<p align="center">
  <img src="https://img.shields.io/badge/Platform-Kali%20Linux-informational?style=for-the-badge&logo=linux&logoColor=white" alt="Platform"/>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Framework-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/C2-Sliver-red?style=for-the-badge" alt="Sliver C2"/>
  <img src="https://img.shields.io/badge/MITRE ATT%26CK-Mapped-orange?style=for-the-badge" alt="MITRE"/>
  <img src="https://img.shields.io/badge/License-Academic%20Research-lightgrey?style=for-the-badge" alt="License"/>
</p>

<h1 align="center">🛡️ Adaptive BAS Platform</h1>
<p align="center"><em>A research-grade Breach and Attack Simulation platform for controlled red-team evaluation of defensive tools</em></p>

---

## 📖 Overview

The **Adaptive BAS Platform** is a full-stack Breach and Attack Simulation (BAS) system designed for cybersecurity research. It executes realistic, MITRE ATT\&CK–mapped attack techniques against a controlled Windows victim VM, collects real-time telemetry, and measures the effectiveness of defensive tools — all from a Kali Linux control node.

> ⚠️ **For authorized research and lab environments only.** Never use on systems you do not own or have explicit written permission to test.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    BAS PLATFORM (Kali Linux)                    │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌───────────┐  ┌────────┐ │
│   │   Safety    │  │   Attack    │  │ Telemetry │  │  C2    │ │
│   │   Engine    │  │  Executor   │  │ Collector │  │ Client │ │
│   │             │  │             │  │           │  │(Sliver)│ │
│   │ Kill Switch │  │ MITRE ATT&CK│  │ Real-time │  │ Agent  │ │
│   │ IP Whitelist│  │  Playbooks  │  │  Metrics  │  │  Mgmt  │ │
│   │ Health Guard│  │ Auto-Cleanup│  │ Anomalies │  │  Exec  │ │
│   └─────────────┘  └─────────────┘  └───────────┘  └────────┘ │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │          FastAPI REST API  +  React Web UI               │  │
│   └─────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                          │
              WinRM / PowerShell + Sliver C2
                          ▼
┌────────────────────────────────────────────────────────────────┐
│                  VICTIM VM  (Windows 10/11)                     │
│   WinRM ─ PowerShell Remoting   │   Sliver Beacon/Session      │
│   Windows Event Log Collection  │   System Metrics             │
└────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔒 **Safety Engine** | Kill switch, IP whitelisting, health-based auto-stop |
| ⚔️ **Attack Executor** | 10+ MITRE ATT\&CK techniques with auto-cleanup |
| 📡 **Real-time Telemetry** | CPU, memory, network, process monitoring |
| 🎭 **C2 Integration** | Full Sliver C2 framework integration |
| 📋 **8 Playbooks** | Scenario-based attack chains |
| 🖥️ **Web UI** | React dashboard for live monitoring |
| 📊 **API-First** | Full REST API with Swagger docs |

---

## 🚀 Quick Start

> See [SETUP_GUIDE.md](SETUP_GUIDE.md) for the complete detailed setup walkthrough.

### Prerequisites
- Kali Linux (host)
- VirtualBox with a Windows 10/11 VM on a Host-Only network
- Python 3.10+

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/bas_platform.git
cd bas_platform
sudo bash setup.sh
```

### 2. Configure

```bash
cp .env.example .env
nano .env   # Set victim IP, credentials, and safety options
```

### 3. Run

```bash
./run.sh
```

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

---

## 📁 Project Structure

```
bas_platform/
├── api/
│   └── main.py                  # FastAPI application & all endpoints
├── core/
│   ├── safety_engine.py         # Kill switch, target validation, health guard
│   ├── attack_executor.py       # Technique registry & execution engine
│   └── adaptive_executor.py     # Adaptive fallback execution logic
├── telemetry/
│   ├── collector.py             # Real-time VM metrics collection
│   └── event_parser.py          # Windows Event Log parser
├── c2_integration/
│   └── sliver_client.py         # Sliver C2 gRPC client
├── config/
│   └── settings.py              # Pydantic settings & env loader
├── playbooks/
│   ├── discovery_phase.sh       # T1087, T1057, T1016, T1083
│   ├── credential_access.sh     # T1003.001 (LSASS safe dump)
│   ├── persistence_phase.sh     # T1053.005 (Scheduled Task)
│   ├── privilege_escalation.sh  # T1548 techniques
│   ├── lateral_movement.sh      # T1021 WinRM lateral movement
│   ├── lateral_movement_sliver.sh # Full Sliver C2 lateral movement
│   ├── defense_evasion_adaptive.sh# Adaptive defense evasion
│   └── ransomware_simulation.sh # Controlled ransomware sim
├── scripts/
│   ├── extract_browser_creds.ps1
│   └── enable_windows_audit.py
├── attacks/
│   └── modules/
├── web-ui/                      # React + Vite dashboard
│   └── src/
├── .env.example                 # Configuration template
├── requirements.txt             # Python dependencies
├── setup.sh                     # Full platform setup script
├── setup_sliver.sh              # Sliver C2 setup script
├── run.sh                       # Platform launch script
└── SETUP_GUIDE.md               # Developer onboarding guide
```

---

## ⚔️ MITRE ATT\&CK Techniques

| ID | Name | Tactic | Severity |
|----|------|--------|----------|
| T1087 | Account Discovery | Discovery | Informational |
| T1057 | Process Discovery | Discovery | Informational |
| T1016 | Network Configuration Discovery | Discovery | Informational |
| T1083 | File & Directory Discovery | Discovery | Low |
| T1003.001 | LSASS Memory (Safe) | Credential Access | Medium |
| T1053.005 | Scheduled Task Creation | Persistence | Medium |
| T1059.001 | PowerShell Execution | Execution | Medium |
| T1021.006 | WinRM Remote Execution | Lateral Movement | High |
| T1071.001 | Web Protocol C2 | Command & Control | Low |
| T1041 | Exfiltration (Simulated) | Exfiltration | Medium |
| T1562 | Defense Evasion (Adaptive) | Defense Evasion | High |

---

## 🔒 Safety Levels

| Level | Description | What Executes |
|-------|-------------|---------------|
| `simulation` | Dry-run mode | Commands logged only, nothing runs |
| `observation` | Telemetry only | Read-only collection from victim |
| `controlled` | Safe non-destructive attacks | MITRE techniques with cleanup |
| `full` | All techniques | Requires explicit flag + IP whitelist |

---

## 🌐 API Reference

### Safety & Control
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/safety/status` | Safety system status |
| POST | `/api/v1/safety/level/{level}` | Set safety level |
| POST | `/api/v1/safety/kill-switch` | Emergency stop |
| DELETE | `/api/v1/safety/kill-switch` | Reset kill switch |

### Attack Execution
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/attacks/techniques` | List all techniques |
| POST | `/api/v1/attacks/execute` | Execute an attack |
| GET | `/api/v1/attacks/results` | List results |
| GET | `/api/v1/attacks/results/{id}` | Get specific result |

### Telemetry
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/telemetry/start/{ip}` | Start collection |
| POST | `/api/v1/telemetry/stop` | Stop collection |
| GET | `/api/v1/telemetry/latest` | Latest snapshot |
| GET | `/api/v1/telemetry/health-timeline` | Health over time |

### C2 Integration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/c2/status` | Sliver server status |
| GET | `/api/v1/c2/agents` | List active implants |
| POST | `/api/v1/c2/agents/{id}/execute` | Execute via C2 |

---

## 🧩 Playbooks

Each playbook is a bash script that calls the platform's REST API to chain multiple MITRE techniques into a realistic attack scenario.

| Playbook | Scenario |
|----------|----------|
| `discovery_phase.sh` | Full network & host discovery |
| `credential_access.sh` | Safe credential harvesting |
| `persistence_phase.sh` | Scheduled task persistence |
| `privilege_escalation.sh` | UAC bypass & privilege escalation |
| `lateral_movement.sh` | WinRM-based lateral movement |
| `lateral_movement_sliver.sh` | Sliver C2 lateral movement (5 phases) |
| `defense_evasion_adaptive.sh` | Adaptive primary/fallback evasion |
| `ransomware_simulation.sh` | Controlled ransomware simulation |

---

## 🛠️ Extending the Platform

### Add a New Attack Technique

Edit `core/attack_executor.py` in `_register_builtin_techniques()`:

```python
self.register_technique(AttackTechnique(
    technique_id="T1XXX",
    name="My Technique",
    description="What it does",
    severity=AttackSeverity.LOW,
    tactic="Discovery",
    command_template="Get-Command",
    requires_admin=False,
    expected_duration=10,
    is_destructive=False,
    cleanup_command="Optional cleanup",
    expected_artifacts=["event_id_1234"],
    detection_rules=["rule_name"]
))
```

### Run Tests

```bash
source venv/bin/activate
pytest test_setup.py -v
```

---

## 🔧 Troubleshooting

| Issue | Fix |
|-------|-----|
| WinRM fails | Run `Enable-PSRemoting -Force` on Windows VM as admin |
| Sliver not connecting | `sudo systemctl restart sliver` then `sudo bash fix_sliver.sh` |
| API port 8000 in use | `sudo lsof -i :8000` then kill, or use `./run.sh --port 8001` |
| venv not found | Run `sudo bash setup.sh` from project root |

---

## 🔐 Security & Ethics

- **Lab environments only** — isolated Host-Only VirtualBox network
- **Never target production systems**
- **Always snapshot** the victim VM before running attack playbooks
- **All attack output may contain sensitive data** — treat results accordingly
- **Legal compliance** — only use on systems you own or have explicit written authorization to test

---

## 📄 License

This project is developed for **academic and research purposes** as part of a graduate-level cybersecurity research program. It is not licensed for commercial use.

---

## 👤 Author

**Akila** — Graduate Researcher, Cybersecurity  
*Built as part of a Breach and Attack Simulation research project(Masters dissertation)*

---

## 📚 References

- [MITRE ATT\&CK Framework](https://attack.mitre.org/)
- [Sliver C2 Framework](https://github.com/BishopFox/sliver)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [NIST SP 800-115 — Technical Guide to Information Security Testing](https://csrc.nist.gov/publications/detail/sp/800-115/final)
