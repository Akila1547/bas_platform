# Quick Attack Verification Script for Windows VM
# Run this on Windows VM in PowerShell (as Administrator)

Write-Host "=== BAS Attack Verification ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check PowerShell execution logs
Write-Host "[1] Checking PowerShell Command Logs..." -ForegroundColor Yellow
$psLogs = Get-WinEvent -LogName "Microsoft-Windows-PowerShell/Operational" -MaxEvents 20 -ErrorAction SilentlyContinue | 
    Where-Object {$_.TimeCreated -gt (Get-Date).AddMinutes(-30)}

if ($psLogs) {
    Write-Host "✓ Found $($psLogs.Count) PowerShell events in last 30 minutes" -ForegroundColor Green
    $psLogs | Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} else {
    Write-Host "✗ No recent PowerShell events found" -ForegroundColor Red
}

Write-Host ""

# 2. Check WinRM connections
Write-Host "[2] Checking WinRM Connections from Kali (192.168.56.101)..." -ForegroundColor Yellow
$winrmLogs = Get-WinEvent -LogName "Microsoft-Windows-WinRM/Operational" -MaxEvents 20 -ErrorAction SilentlyContinue |
    Where-Object {$_.TimeCreated -gt (Get-Date).AddMinutes(-30)}

if ($winrmLogs) {
    Write-Host "✓ Found $($winrmLogs.Count) WinRM events" -ForegroundColor Green
    $winrmLogs | Select-Object TimeCreated, Id, Message | Format-Table -AutoSize
} else {
    Write-Host "✗ No recent WinRM events found" -ForegroundColor Red
}

Write-Host ""

# 3. Check Security logon events
Write-Host "[3] Checking Network Logons..." -ForegroundColor Yellow
$logons = Get-WinEvent -FilterHashtable @{
    LogName='Security'
    ID=4624
    StartTime=(Get-Date).AddMinutes(-30)
} -ErrorAction SilentlyContinue | Select-Object -First 10

if ($logons) {
    Write-Host "✓ Found $($logons.Count) logon events" -ForegroundColor Green
} else {
    Write-Host "✗ No recent logon events found" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== Verification Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To see detailed PowerShell commands executed:" -ForegroundColor Yellow
Write-Host "  1. Open Event Viewer (eventvwr.msc)" -ForegroundColor White
Write-Host "  2. Navigate to: Applications and Services Logs > Microsoft > Windows > PowerShell > Operational" -ForegroundColor White
Write-Host "  3. Look for Event ID 4104 (Script Block Logging)" -ForegroundColor White
