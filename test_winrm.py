#!/usr/bin/env python3
"""
Quick WinRM connectivity test
"""
import winrm

target_ip = "192.168.56.102"
username = "akila"
password = "12345678"

print(f"Testing WinRM connection to {target_ip}...")

try:
    session = winrm.Session(
        f'http://{target_ip}:5985/wsman',
        auth=(username, password),
        transport='ntlm'
    )
    
    result = session.run_ps("hostname")
    print(f"✓ Connection successful!")
    print(f"Hostname: {result.std_out.decode().strip()}")
    print(f"Exit code: {result.status_code}")
    
except Exception as e:
    print(f"✗ Connection failed: {e}")
