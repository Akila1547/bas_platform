#!/usr/bin/env python3
"""Test T1016 network discovery commands"""
import winrm

target_ip = "192.168.56.102"
username = "akila"
password = "12345678"

print(f"Testing T1016 network discovery commands on {target_ip}...")

session = winrm.Session(
    f'http://{target_ip}:5985/wsman',
    auth=(username, password),
    transport='ntlm'
)

# Test different network discovery commands
commands = [
    ("ipconfig /all", "Classic ipconfig"),
    ("Get-NetIPConfiguration", "Get-NetIPConfiguration"),
    ("Get-WmiObject -Class Win32_NetworkAdapterConfiguration | Where-Object {$_.IPEnabled}", "WMI Network Config"),
    ("Get-NetAdapter | Select-Object Name,Status,MacAddress", "Get-NetAdapter"),
]

for cmd, desc in commands:
    print(f"\n{'='*60}")
    print(f"Testing: {desc}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    try:
        result = session.run_ps(cmd)
        if result.status_code == 0:
            print(f"✓ SUCCESS")
            print(f"Output: {result.std_out.decode()[:500]}")
        else:
            print(f"✗ FAILED")
            print(f"Error: {result.std_err.decode()}")
    except Exception as e:
        print(f"✗ EXCEPTION: {e}")
