# BAS Platform - Playbook Testing & Verification Guide

## Overview

This document provides detailed execution steps, commands, and verification methods for all 6 attack playbooks.

---

## Playbook 1: Discovery Phase ✅ TESTED

### Execution Steps

#### 1. Start API Server (Kali Linux)
```bash
cd /home/akila/Desktop/bas_platform
./run.sh > api.log 2>&1 &
```
**What it does**: Starts the BAS Platform API server on port 8000

**Verify**:
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```
**Expected output**: `{"status": "healthy", "timestamp": "...", "version": "2.0.0"}`

---

#### 2. Set Safety Level (Kali Linux)
```bash
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled" -s | python3 -m json.tool
```
**What it does**: Sets safety level to "controlled" - allows safe, non-destructive attacks only

**Expected output**: `{"message": "Safety level set to controlled", "success": true}`

---

#### 3. Execute Discovery Playbook (Kali Linux)
```bash
./playbooks/discovery_phase.sh
```
**What it does**: Executes 4 discovery attacks in sequence:
1. T1087 - Account Discovery
2. T1057 - Process Discovery
3. T1016 - Network Configuration Discovery
4. T1083 - File and Directory Discovery

**Expected output**:
```
╔══════════════════════════════════════════════════════════════╗
║         Discovery Phase Attack Playbook                      ║
║         MITRE ATT&CK: Discovery Tactic                       ║
╚══════════════════════════════════════════════════════════════╝

[SUCCESS] API is reachable at http://localhost:8000
[SUCCESS] Telemetry collection started

╔══════════════════════════════════════════════════════════════╗
║                    EXECUTING ATTACKS                         ║
╚══════════════════════════════════════════════════════════════╝

[SUCCESS] T1087 completed (ID: xxxxxxxx)
[SUCCESS] T1057 completed (ID: xxxxxxxx)
[SUCCESS] T1016 completed (ID: xxxxxxxx)
[SUCCESS] T1083 completed (ID: xxxxxxxx)

╔══════════════════════════════════════════════════════════════╗
║                    FINAL HEALTH STATUS                       ║
║  Health Score:  75.07                                       ║
║  CPU Usage:     9.80  %                                     ║
║  Memory Usage:  34.59 %                                     ║
╚══════════════════════════════════════════════════════════════╝

[SUCCESS] Discovery phase playbook completed!
```

---

### Commands Executed on Windows VM

During the playbook execution, the following PowerShell commands are executed on the Windows VM (192.168.56.102) via WinRM:

#### Attack 1: T1087 - Account Discovery
**Command executed**:
```powershell
Get-LocalUser | Select-Object Name,Enabled,LastLogon,PasswordLastSet | Format-Table -AutoSize
```
**What it does**: Lists all local user accounts on the Windows system
**Location**: Windows VM (192.168.56.102)
**Protocol**: WinRM (port 5985)

---

#### Attack 2: T1057 - Process Discovery
**Command executed**:
```powershell
Get-Process | Select-Object ProcessName,Id,CPU,WorkingSet | Sort-Object CPU -Descending | Select-Object -First 20 | Format-Table -AutoSize
```
**What it does**: Lists top 20 processes by CPU usage
**Location**: Windows VM (192.168.56.102)
**Protocol**: WinRM (port 5985)

---

#### Attack 3: T1016 - Network Configuration Discovery
**Command executed**:
```cmd
ipconfig /all
```
**What it does**: Displays detailed network configuration (IP addresses, DNS, MAC addresses)
**Location**: Windows VM (192.168.56.102)
**Protocol**: WinRM (port 5985)

---

#### Attack 4: T1083 - File and Directory Discovery
**Command executed**:
```powershell
Get-ChildItem -Path 'C:\Users' -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime -First 50 | Format-Table -AutoSize
```
**What it does**: Lists files and directories in C:\Users (up to 2 levels deep, first 50 items)
**Location**: Windows VM (192.168.56.102)
**Protocol**: WinRM (port 5985)

---

### Verification Methods

#### Method 1: Check Generated Report (Kali Linux)
```bash
# Find the latest discovery report
ls -lht discovery_report_*.json | head -1

# View report contents
cat discovery_report_20260213_185918.json | python3 -m json.tool
```

**What to verify**:
- All 4 attacks have `"status": "completed"`
- Each attack has a `duration` > 0
- `health_timeline` shows telemetry data
- Final health score is reasonable (> 50)

**Example report structure**:
```json
{
    "attacks": [
        {
            "attack_id": "db80c466",
            "technique_id": "T1087",
            "technique_name": "Account Discovery",
            "status": "completed",
            "duration": 14.5,
            "health_impact": -2.3
        },
        ...
    ],
    "health_timeline": [
        {
            "timestamp": "2026-02-13T18:59:18",
            "health_score": 75.07,
            "cpu": 9.80,
            "memory": 34.59
        }
    ]
}
```

---

#### Method 2: Check Windows Event Logs (Windows VM)

**On Windows VM, open PowerShell as Administrator**:

```powershell
# Check PowerShell command execution logs
Get-WinEvent -LogName "Microsoft-Windows-PowerShell/Operational" -MaxEvents 20 | 
    Where-Object {$_.TimeCreated -gt (Get-Date).AddMinutes(-10)} | 
    Select-Object TimeCreated, Id, Message | 
    Format-Table -AutoSize
```

**What to verify**:
- Event ID 4104 (Script Block Logging) shows executed commands
- Timestamps match attack execution time
- Commands like `Get-LocalUser`, `Get-Process`, `ipconfig`, `Get-ChildItem` appear

---

#### Method 3: Check WinRM Connection Logs (Windows VM)

```powershell
# Check WinRM activity
Get-WinEvent -LogName "Microsoft-Windows-WinRM/Operational" -MaxEvents 10 | 
    Select-Object TimeCreated, Id, Message | 
    Format-Table -AutoSize
```

**What to verify**:
- Connection events from Kali IP (192.168.56.101)
- Successful authentication events
- Command execution events

---

#### Method 4: Verify via API (Kali Linux)

```bash
# Get attack results
curl -s "http://localhost:8000/api/v1/attacks/results" | python3 -m json.tool

# Get specific attack result (replace ATTACK_ID)
curl -s "http://localhost:8000/api/v1/attacks/results/db80c466" | python3 -m json.tool

# Get telemetry history
curl -s "http://localhost:8000/api/v1/telemetry/history?count=10" | python3 -m json.tool
```

**What to verify**:
- All attacks show `"status": "completed"`
- `command_output` contains actual results
- `exit_code`: 0 (success)
- `health_impact` is calculated

---

#### Method 5: Manual Verification on Windows VM

**Check if commands left traces**:

```powershell
# 1. Verify account discovery was run
# (Check if Get-LocalUser was executed recently)
Get-PSReadlineOption | Select-Object HistorySavePath
Get-Content (Get-PSReadlineOption).HistorySavePath -Tail 20

# 2. Check process access
# (Verify Get-Process was called)
Get-EventLog -LogName Security -Newest 10 | Where-Object {$_.EventID -eq 4688}

# 3. Verify network config access
# (ipconfig leaves minimal traces, but check command history)

# 4. Check file access logs
# (Verify C:\Users was accessed)
Get-EventLog -LogName Security -Newest 20 | 
    Where-Object {$_.EventID -eq 4663 -and $_.Message -like "*C:\Users*"}
```

---

### Success Criteria

✅ **Discovery Phase is successful if**:
1. All 4 attacks complete with status "completed"
2. Report JSON is generated with valid data
3. Windows Event Logs show PowerShell command execution
4. Final health score > 50
5. No errors in API logs
6. Telemetry data is collected throughout execution

---

### Troubleshooting

**Issue**: Attacks fail with "credentials rejected"
**Solution**: 
```bash
# Verify credentials in .env
cat .env | grep VICTIM

# Test WinRM connectivity
python3 test_winrm.py

# Restart API to reload .env
pkill -9 -f uvicorn
./run.sh > api.log 2>&1 &
```

**Issue**: No telemetry data
**Solution**:
```bash
# Manually start telemetry
curl -X POST "http://localhost:8000/api/v1/telemetry/start/192.168.56.102?interval=5"

# Check telemetry status
curl -s "http://localhost:8000/api/v1/telemetry/latest" | python3 -m json.tool
```

**Issue**: Windows Event Logs empty
**Solution**:
```powershell
# Enable PowerShell logging (on Windows VM as Administrator)
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" -Name "EnableScriptBlockLogging" -Value 1
```

---

## Playbook 2: Persistence Phase

### Execution Steps

#### 1. Execute Persistence Playbook (Kali Linux)
```bash
./playbooks/persistence_phase.sh
```

**What it does**: Executes 2 persistence attacks:
1. T1053.005 - Scheduled Task Creation
2. T1059.001 - PowerShell Execution

---

### Commands Executed on Windows VM

#### Attack 1: T1053.005 - Scheduled Task Creation
**Command executed**:
```cmd
schtasks /create /tn 'BAS_Test_Task' /tr 'notepad.exe' /sc once /st 23:59 /f
```
**What it does**: Creates a scheduled task named "BAS_Test_Task" that runs notepad.exe once at 23:59
**Location**: Windows VM
**Protocol**: WinRM

**Cleanup command** (automatically executed):
```cmd
schtasks /delete /tn 'BAS_Test_Task' /f 2>$null
```

---

#### Attack 2: T1059.001 - PowerShell Execution
**Command executed**:
```powershell
powershell -ExecutionPolicy Bypass -Command 'Write-Host "BAS Test Execution"; Get-Date'
```
**What it does**: Executes a benign PowerShell command with bypass execution policy
**Location**: Windows VM
**Protocol**: WinRM

---

### Verification Methods

#### Verify Scheduled Task Creation (Windows VM)
```powershell
# Check if task was created and then deleted
Get-EventLog -LogName Security -Newest 50 | 
    Where-Object {$_.EventID -eq 4698 -or $_.EventID -eq 4699} |
    Select-Object TimeGenerated, EventID, Message

# Event ID 4698 = Scheduled task created
# Event ID 4699 = Scheduled task deleted
```

#### Verify PowerShell Execution (Windows VM)
```powershell
# Check PowerShell execution logs
Get-WinEvent -LogName "Microsoft-Windows-PowerShell/Operational" -MaxEvents 20 |
    Where-Object {$_.Message -like "*BAS Test Execution*"}
```

---

## Playbook 3: Credential Access

### Execution Steps

#### 1. Execute Credential Access Playbook (Kali Linux)
```bash
./playbooks/credential_access.sh
```

**What it does**: Executes 3 credential access attacks:
1. T1555.003 - Browser Credentials Check
2. T1552.001 - Credentials in Files Search
3. T1003.001 - LSASS Memory Enumeration

---

### Commands Executed on Windows VM

#### Attack 1: T1555.003 - Browser Credentials
**Command executed**:
```powershell
Test-Path '$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Login Data'; Test-Path '$env:APPDATA\Mozilla\Firefox\Profiles'
```
**What it does**: Checks if browser credential storage locations exist (read-only)
**Location**: Windows VM
**Protocol**: WinRM

---

#### Attack 2: T1552.001 - Credentials in Files
**Command executed**:
```powershell
Get-ChildItem -Path C:\Users -Include *password*,*cred*,*.txt,*.xml -Recurse -ErrorAction SilentlyContinue -Depth 2 | Select-Object FullName,Length,LastWriteTime -First 10
```
**What it does**: Searches for files with credential-related names
**Location**: Windows VM
**Protocol**: WinRM

---

#### Attack 3: T1003.001 - LSASS Memory
**Command executed**:
```powershell
Get-Process lsass | Select-Object ProcessName,Id,WorkingSet64,PagedMemorySize64 | Format-List
```
**What it does**: Enumerates LSASS process information (safe, read-only)
**Location**: Windows VM
**Protocol**: WinRM

---

### Verification Methods

#### Verify on Windows VM
```powershell
# Check file access attempts
Get-EventLog -LogName Security -Newest 50 | 
    Where-Object {$_.EventID -eq 4663} |
    Select-Object TimeGenerated, Message

# Check LSASS process access
Get-EventLog -LogName Security -Newest 20 | 
    Where-Object {$_.Message -like "*lsass*"}
```

---

## Playbook 4: Privilege Escalation

### Execution Steps

#### 1. Execute Privilege Escalation Playbook (Kali Linux)
```bash
./playbooks/privilege_escalation.sh
```

**What it does**: Executes 3 privilege escalation attacks:
1. T1548.002 - UAC Settings Check
2. T1134.001 - Token/Privilege Enumeration
3. T1543.003 - Service Enumeration

---

### Commands Executed on Windows VM

#### Attack 1: T1548.002 - UAC Bypass Check
**Command executed**:
```powershell
Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' | Select-Object EnableLUA,ConsentPromptBehaviorAdmin,PromptOnSecureDesktop
```
**What it does**: Reads UAC configuration from registry
**Location**: Windows VM
**Protocol**: WinRM

---

#### Attack 2: T1134.001 - Token Impersonation
**Command executed**:
```cmd
whoami /priv; whoami /groups
```
**What it does**: Lists current user privileges and group memberships
**Location**: Windows VM
**Protocol**: WinRM

---

#### Attack 3: T1543.003 - Windows Service
**Command executed**:
```powershell
Get-Service | Where-Object {$_.StartType -eq 'Automatic' -and $_.Status -eq 'Running'} | Select-Object Name,DisplayName,StartType -First 20
```
**What it does**: Lists running automatic services
**Location**: Windows VM
**Protocol**: WinRM

---

### Verification Methods

#### Verify on Windows VM
```powershell
# Check registry access
Get-EventLog -LogName Security -Newest 30 | 
    Where-Object {$_.EventID -eq 4663 -and $_.Message -like "*Registry*"}

# Check privilege enumeration
Get-WinEvent -LogName "Microsoft-Windows-PowerShell/Operational" -MaxEvents 20 |
    Where-Object {$_.Message -like "*whoami*"}
```

---

## Playbook 5: Defense Evasion (Adaptive) ⚡

### Execution Steps

#### 1. Execute Defense Evasion Playbook (Kali Linux)
```bash
./playbooks/defense_evasion_adaptive.sh
```

**What it does**: Executes adaptive attacks with fallback logic:
1. T1562.001 → T1562.004 (Defender check → Firewall check)
2. T1070.001 → T1027.002 (Event logs → Obfuscation)

---

### Commands Executed on Windows VM

#### Attack 1a: T1562.001 - Disable Defender (Primary)
**Command executed**:
```powershell
Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,IoavProtectionEnabled,OnAccessProtectionEnabled
```
**What it does**: Checks Windows Defender status
**Location**: Windows VM 
**Protocol**: WinRM

**If primary fails, automatically pivots to**:

#### Attack 1b: T1562.004 - Disable Firewall (Fallback)
**Command executed**:
```powershell
Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction
```
**What it does**: Checks Windows Firewall status
**Location**: Windows VM
**Protocol**: WinRM

---

#### Attack 2a: T1070.001 - Clear Event Logs (Primary)
**Command executed**:
```powershell
Get-EventLog -List | Select-Object Log,MaximumKilobytes,@{Name='Entries';Expression={$_.Entries.Count}}
```
**What it does**: Enumerates event logs (does NOT clear them)
**Location**: Windows VM
**Protocol**: WinRM

**If primary fails, automatically pivots to**:

#### Attack 2b: T1027.002 - Obfuscated PowerShell (Fallback)
**Command executed**:
```powershell
$cmd = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes('Write-Host BAS_Test')); powershell -EncodedCommand $cmd
```
**What it does**: Executes base64-encoded PowerShell command
**Location**: Windows VM
**Protocol**: WinRM

---

### Verification Methods

#### Verify Adaptive Behavior (Kali Linux)
**Check playbook output for adaptive pivoting**:
```
[INFO] Primary: T1562.001 - Disable Windows Defender
[WARNING] ✗ Primary technique failed/blocked
[ADAPTIVE] → PIVOTING to fallback technique...
[INFO] Fallback: T1562.004 - Disable Firewall
[SUCCESS] ✓ Fallback technique succeeded
```

#### Verify on Windows VM
```powershell
# Check for base64-encoded command execution
Get-WinEvent -LogName "Microsoft-Windows-PowerShell/Operational" -MaxEvents 20 |
    Where-Object {$_.Message -like "*EncodedCommand*" -or $_.Message -like "*BAS_Test*"}
```

---

## Playbook 6: Lateral Movement

### Execution Steps

#### 1. Execute Lateral Movement Playbook (Kali Linux)
```bash
./playbooks/lateral_movement.sh
```

**What it does**: Executes 3 lateral movement attacks:
1. T1021.001 - RDP Enumeration
2. T1021.002 - SMB/Admin Shares
3. T1570 - Lateral Tool Transfer

---

### Commands Executed on Windows VM

#### Attack 1: T1021.001 - RDP
**Command executed**:
```powershell
Get-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' | Select-Object fDenyTSConnections; qwinsta
```
**What it does**: Checks RDP status and active sessions
**Location**: Windows VM
**Protocol**: WinRM

---

#### Attack 2: T1021.002 - SMB/Admin Shares
**Command executed**:
```powershell
Get-SmbShare | Select-Object Name,Path,Description; net share
```
**What it does**: Lists network shares
**Location**: Windows VM
**Protocol**: WinRM

---

#### Attack 3: T1570 - Lateral Tool Transfer
**Command executed**:
```powershell
$testFile = '$env:TEMP\bas_transfer_test.txt'; 'BAS_Test_Transfer' | Out-File -FilePath $testFile; Test-Path $testFile; Remove-Item $testFile -Force
```
**What it does**: Creates, verifies, and deletes a test file (simulates file transfer)
**Location**: Windows VM
**Protocol**: WinRM

---

### Verification Methods

#### Verify on Windows VM
```powershell
# Check SMB share enumeration
Get-WinEvent -LogName "Microsoft-Windows-SmbClient/Security" -MaxEvents 20 -ErrorAction SilentlyContinue

# Check file creation in TEMP
Get-EventLog -LogName Security -Newest 20 | 
    Where-Object {$_.Message -like "*bas_transfer_test.txt*"}
```

---

## Summary: Complete Testing Workflow

### Execute All Playbooks in Order

```bash
# 1. Start API
./run.sh > api.log 2>&1 &
sleep 5

# 2. Set safety level
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled" -s

# 3. Test Discovery
./playbooks/discovery_phase.sh

# 4. Test Persistence
./playbooks/persistence_phase.sh

# 5. Test Credential Access
./playbooks/credential_access.sh

# 6. Test Privilege Escalation
./playbooks/privilege_escalation.sh

# 7. Test Defense Evasion (Adaptive)
./playbooks/defense_evasion_adaptive.sh

# 8. Test Lateral Movement
./playbooks/lateral_movement.sh

# 9. Generate final report
curl -s "http://localhost:8000/api/v1/reports/attack-timeline" | python3 -m json.tool > full_test_report.json
```

---

## Universal Verification Checklist

After each playbook execution:

- [ ] Check exit code is 0
- [ ] Verify all attacks show "completed" status
- [ ] Check report JSON is generated
- [ ] Verify Windows Event Logs show command execution
- [ ] Confirm final health score is reasonable
- [ ] Review API logs for errors: `tail -50 api.log`
- [ ] Check telemetry data was collected

---

## Next Steps

1. ✅ Test all 6 playbooks sequentially
2. ✅ Document results for each
3. ⏭️ Sliver C2 integration (optional)
4. ⏭️ Web UI development (optional)
