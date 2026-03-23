#!/usr/bin/env python3
"""
Execute the working credential extraction script
"""

import winrm

print("[*] Connecting to Windows VM (192.168.56.102)...")

session = winrm.Session(
    'http://192.168.56.102:5985/wsman',
    auth=('akila', '12345678'),
    transport='ntlm'
)

print("[+] Connected successfully!")

# Read the working script
with open('scripts/extract_creds_working.ps1', 'r', encoding='utf-8') as f:
    script = f.read()

print("[*] Executing credential extraction script...")
print("="*70 + "\n")

# Execute via PowerShell
result = session.run_ps(script)

# Display output
if result.status_code == 0:
    output = result.std_out.decode('utf-8', errors='ignore')
    print(output)
else:
    print("ERROR OUTPUT:")
    error = result.std_err.decode('utf-8', errors='ignore')
    print(error)
    
    if result.std_out:
        print("\nPARTIAL OUTPUT:")
        print(result.std_out.decode('utf-8', errors='ignore'))

print("="*70)
print(f"[*] Exit Code: {result.status_code}\n")
