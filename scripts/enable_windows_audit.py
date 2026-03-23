import winrm

# Configure connection using correct .env credentials
host = "192.168.56.102"
username = "akila"
password = "12345678"

session = winrm.Session(
    f"http://{host}:5985/wsman",
    auth=(username, password),
    transport="ntlm",
    server_cert_validation="ignore"
)

commands = [
    # Enable Process Creation (Event ID 4688)
    'auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable',
    
    # Enable command line auditing for process creation
    'reg add "HKLM\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System\\Audit" /v ProcessCreationIncludeCmdLine_Enabled /t REG_DWORD /d 1 /f',
    
    # Enable PowerShell Script Block Logging (Event ID 4104)
    'reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\PowerShell\\ScriptBlockLogging" /v EnableScriptBlockLogging /t REG_DWORD /d 1 /f',
    
    # Enable Object Access (for Scheduled Tasks / Files - 4698, 4656, 4663)
    'auditpol /set /subcategory:"Other Object Access Events" /success:enable /failure:enable',
    'auditpol /set /subcategory:"File System" /success:enable /failure:enable',
    'auditpol /set /subcategory:"Handle Manipulation" /success:enable /failure:enable',
    
    # Refresh group policies
    'gpupdate /force'
]

for cmd in commands:
    print(f"Running: {cmd}")
    result = session.run_cmd(cmd)
    if result.status_code == 0:
         print(f"Success: {result.std_out.decode('utf-8', errors='replace').strip()}")
    else:
         print(f"Error: {result.std_err.decode('utf-8', errors='replace').strip()}")

print("Audit configuration complete.")
