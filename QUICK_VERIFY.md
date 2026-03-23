# Quick Verification Commands

## From Kali Linux (Remote Verification)

You can verify the attacks remotely from Kali using WinRM:

```bash
# 1. Check recent PowerShell events
~/.local/share/gem/ruby/3.3.0/bin/evil-winrm -i 192.168.56.102 -u akila -p 1123 -x "Get-WinEvent -LogName 'Microsoft-Windows-PowerShell/Operational' -MaxEvents 10 | Select-Object TimeCreated, Id | Format-Table"

# 2. Check WinRM connection logs
~/.local/share/gem/ruby/3.3.0/bin/evil-winrm -i 192.168.56.102 -u akila -p 1123 -x "Get-WinEvent -LogName 'Microsoft-Windows-WinRM/Operational' -MaxEvents 10 | Select-Object TimeCreated, Id | Format-Table"

# 3. Check if our commands left traces in PowerShell history
~/.local/share/gem/ruby/3.3.0/bin/evil-winrm -i 192.168.56.102 -u akila -p 1123 -x "Get-Content (Get-PSReadlineOption).HistorySavePath -Tail 20"
```

## On Windows VM (Direct Verification)

### Quick GUI Method:
1. Press `Win + R`
2. Type: `eventvwr.msc`
3. Navigate to: **Applications and Services Logs → Microsoft → Windows → PowerShell → Operational**
4. Look for recent events (Event ID 4104)

### PowerShell Script Method:
Copy `verify_on_windows.ps1` to Windows VM and run:
```powershell
.\verify_on_windows.ps1
```

## What You Should See

### Evidence of T1087 (Account Discovery):
- Event with `Get-LocalUser` command
- Timestamp: Around 11:45 AM

### Evidence of T1057 (Process Discovery):
- Event with `Get-Process` command  
- Timestamp: Around 11:45-11:46 AM

### Evidence of T1083 (File Discovery):
- Event with `Get-ChildItem -Path 'C:\Users'` command
- Timestamp: Around 11:46 AM

All events should show:
- **Source**: Microsoft-Windows-PowerShell
- **User**: akila
- **Connection from**: 192.168.56.101 (Kali IP)
