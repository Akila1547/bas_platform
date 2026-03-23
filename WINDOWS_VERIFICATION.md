# Windows VM Attack Verification Guide

## How to Verify Attacks Were Executed on Windows VM

### Method 1: Check PowerShell Event Logs (Recommended)

**On Windows VM, open PowerShell as Administrator and run:**

```powershell
# View PowerShell command execution logs
Get-WinEvent -LogName "Microsoft-Windows-PowerShell/Operational" -MaxEvents 50 | 
    Where-Object {$_.TimeCreated -gt (Get-Date).AddMinutes(-30)} | 
    Format-Table TimeCreated, Message -AutoSize

# Or use Event Viewer GUI:
# 1. Press Win+R, type: eventvwr.msc
# 2. Navigate to: Applications and Services Logs > Microsoft > Windows > PowerShell > Operational
# 3. Look for Event ID 4103 (Module Logging) and 4104 (Script Block Logging)
# 4. Check timestamps around 11:45 AM - 11:47 AM (when attacks ran)
```

**What to look for:**
- Commands like `Get-LocalUser`, `Get-Process`, `Get-ChildItem`
- Source: `Microsoft-Windows-PowerShell`
- Recent timestamps matching attack execution time

---

### Method 2: Check WinRM Activity Logs

```powershell
# View WinRM connection logs
Get-WinEvent -LogName "Microsoft-Windows-WinRM/Operational" -MaxEvents 20 | 
    Format-Table TimeCreated, Id, Message -AutoSize

# Look for Event ID 91 (Session created) from IP 192.168.56.101
```

---

### Method 3: Check Security Event Logs

```powershell
# View logon events (WinRM creates logon sessions)
Get-WinEvent -FilterHashtable @{
    LogName='Security'
    ID=4624  # Successful logon
    StartTime=(Get-Date).AddMinutes(-30)
} | Where-Object {$_.Message -like "*192.168.56.101*"} | 
    Format-Table TimeCreated, Message -AutoSize

# Event ID 4624 = Successful Logon (Type 3 = Network logon via WinRM)
```

---

### Method 4: Check Process Creation Events

```powershell
# View process creation events (if auditing enabled)
Get-WinEvent -FilterHashtable @{
    LogName='Security'
    ID=4688  # Process creation
    StartTime=(Get-Date).AddMinutes(-30)
} | Select-Object TimeCreated, Message | Format-List
```

---

### Method 5: Direct Evidence - Check for Attack Artifacts

```powershell
# 1. Check if PowerShell transcription is enabled (may have captured commands)
Test-Path "$env:USERPROFILE\Documents\PowerShell_transcript*.txt"

# 2. Check PowerShell history
Get-Content (Get-PSReadlineOption).HistorySavePath | Select-Object -Last 50

# 3. Check recent file access in C:\Users (from T1083 attack)
Get-ChildItem C:\Users -Recurse -Depth 1 -ErrorAction SilentlyContinue | 
    Where-Object {$_.LastAccessTime -gt (Get-Date).AddMinutes(-30)} | 
    Format-Table FullName, LastAccessTime
```

---

### Method 6: Network Connection Verification

```powershell
# Check for recent connections from Kali IP
Get-NetTCPConnection | Where-Object {$_.RemoteAddress -eq "192.168.56.101"}

# Or check connection history (if available)
netstat -ano | findstr "192.168.56.101"
```

---

## Quick Verification Steps (GUI Method)

### Step 1: Open Event Viewer
1. Press `Win + R`
2. Type: `eventvwr.msc`
3. Click OK

### Step 2: Navigate to PowerShell Logs
1. Expand: **Applications and Services Logs**
2. Expand: **Microsoft** → **Windows** → **PowerShell**
3. Click: **Operational**

### Step 3: Look for Recent Events
- **Event ID 4103**: Module Logging (shows cmdlets executed)
- **Event ID 4104**: Script Block Logging (shows full commands)
- **Timestamp**: Around 11:45-11:47 AM IST (when attacks ran)

### Step 4: Check Event Details
Right-click any event → **Event Properties** to see:
- **Command executed** (e.g., `Get-LocalUser`, `Get-Process`)
- **User**: Your username (akila)
- **Source IP**: 192.168.56.101 (Kali)

---

## Expected Evidence for Each Attack

### T1087 - Account Discovery
**Command**: `Get-LocalUser | Select-Object Name,Enabled,LastLogon`
**Evidence**:
- PowerShell Event ID 4103/4104 with `Get-LocalUser` cmdlet
- Timestamp: ~11:45:23 AM

### T1057 - Process Discovery
**Command**: `Get-Process | Select-Object ProcessName,Id,CPU,WorkingSet | Sort-Object CPU -Descending`
**Evidence**:
- PowerShell Event ID 4103/4104 with `Get-Process` cmdlet
- Timestamp: ~11:45:48 AM

### T1083 - File Discovery
**Command**: `Get-ChildItem -Path 'C:\Users' -Depth 1`
**Evidence**:
- PowerShell Event ID 4103/4104 with `Get-ChildItem` cmdlet
- Access time updates on C:\Users directory
- Timestamp: ~11:46:32 AM

---

## Screenshot Evidence

To capture proof for your report:

1. **Event Viewer Screenshot**:
   - Open Event Viewer → PowerShell → Operational
   - Filter by time range (last 30 minutes)
   - Take screenshot showing attack commands

2. **PowerShell History**:
   ```powershell
   Get-Content (Get-PSReadlineOption).HistorySavePath | Select-Object -Last 20
   ```
   - Take screenshot of output

3. **WinRM Connections**:
   ```powershell
   Get-WinEvent -LogName "Microsoft-Windows-WinRM/Operational" -MaxEvents 10
   ```
   - Take screenshot showing connections from 192.168.56.101

---

## Troubleshooting

**If you don't see events:**

1. **Enable PowerShell Logging** (for future attacks):
   ```powershell
   # Run as Administrator
   New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging" -Force
   New-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ModuleLogging" -Name "EnableModuleLogging" -Value 1 -PropertyType DWord
   
   New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" -Force
   New-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging" -Name "EnableScriptBlockLogging" -Value 1 -PropertyType DWord
   ```

2. **Check if logs are being cleared**:
   ```powershell
   Get-EventLog -List
   ```

3. **Verify WinRM is logging**:
   ```powershell
   wevtutil gl Microsoft-Windows-WinRM/Operational
   ```

---

## Summary

The **easiest and most reliable** way to verify:

1. Open **Event Viewer** (`eventvwr.msc`)
2. Go to **PowerShell → Operational** logs
3. Look for **Event ID 4104** (Script Block Logging)
4. Check timestamps around **11:45-11:47 AM**
5. You should see commands like `Get-LocalUser`, `Get-Process`, `Get-ChildItem`

This proves the attacks were **actually executed** on the Windows VM, not just simulated!
