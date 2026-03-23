# Ransomware Defense Guide

This guide explains how to demonstrate the defensive capabilities of the BAS Platform by protecting the system against the simulated ransomware attack (`T1486`).

## The Threat: Ransomware Simulation

Our platform includes a safe, non-destructive ransomware playbook:
`./playbooks/ransomware_simulation.sh`

When executed without protection, this playbook will:
1. Create a `C:\BAS_Ransomware_Test` directory.
2. Drop dummy financial and business files into it.
3. Encrypt those files and change their extension to `.bas_locked`.
4. Drop a simulated `RANSOM_NOTE.txt`.

## The Defense: Controlled Folder Access

We will demonstrate how **Windows Defender's Controlled Folder Access** (a built-in anti-ransomware feature) natively blocks this attack. Controlled Folder Access monitors applications and scripts, preventing unauthorized processes from modifying files in protected directories.

### Step 1: Enable Controlled Folder Access on the Target VM

1. Log in to the Windows VM (`192.168.56.102`).
2. Open **Windows Security** (search in the Start menu).
3. Go to **Virus & threat protection**.
4. Scroll down to **Ransomware protection** and click **Manage ransomware protection**.
5. Toggle **Controlled folder access** to **On** (Click Yes on the UAC prompt).

### Step 2: Add the Sandbox to Protected Folders

1. Still in the Ransomware protection screen, click **Protected folders** (Click Yes on the UAC prompt).
2. Click **+ Add a protected folder**.
3. Navigate to and select `C:\BAS_Ransomware_Test`. 
   *(Note: If the folder doesn't exist yet, run the playbook once to create it, or create it manually, then add it).*

### Step 3: Run the Attack

Now that the OS is defending the folder, run the simulation playbook from the BAS Platform (Kali Linux):

```bash
cd /home/akila/Desktop/bas_platform
./playbooks/ransomware_simulation.sh
```

### Step 4: Observe the Defense in Action

Watch the output of the playbook. 
- You will see that the PowerShell script successfully connects and creates the sandbox (if it didn't exist).
- However, when it attempts to encrypt and rename the files to `.bas_locked`, PowerShell will throw `UnauthorizedAccess` exceptions.
- The `RANSOM_NOTE.txt` might still be dropped depending on directory permissions, but **the valuable data files remain completely untouched and unencrypted**.

**On the Windows VM:**
You will receive a native Windows Security notification: 
`"Unauthorized changes blocked. Controlled Folder Access blocked powershell.exe from making changes..."`

This proves that the operating system's native anti-ransomware defenses successfully mitigated the MITRE ATT&CK T1486 technique used by the BAS Platform.
