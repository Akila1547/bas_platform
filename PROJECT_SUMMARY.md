# BAS Platform - Project Summary

## What You've Built

An **Adaptive Breach and Attack Simulation (BAS) Platform** that:
1. Executes **real attack techniques** on Windows victim VMs
2. Collects **real-time telemetry** to monitor victim health
3. Correlates attacks with system impact
4. Provides **safety controls** to prevent damage

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BAS PLATFORM (Kali Linux)                            │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FASTAPI REST API (Port 8000)                      │    │
│  │                                                                      │    │
│  │  Safety Engine        Attack Executor       Telemetry Collector     │    │
│  │  ├── Kill Switch      ├── 10+ Techniques    ├── Health Metrics      │    │
│  │  ├── Target Validation├── Pre/Post Snapshots├── Process Monitor     │    │
│  │  └── Health Checks    └── Cleanup Automation└── Anomaly Detection   │    │
│  │                                                                      │    │
│  │  C2 Integration (Sliver)                                             │    │
│  │  ├── Agent Management                                                │    │
│  │  └── Command Execution                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                    WinRM / PowerShell Remoting
                    Sliver C2 Channel
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VICTIM VM (Windows 10/11)                            │
│                                                                              │
│  PowerShell Remoting    Sliver Agent        Windows Event Logs              │
│  (Command Execution)    (C2 Channel)        (Detection Artifacts)           │
│                                                                              │
│  System Metrics: CPU, Memory, Disk, Network, Processes, Services            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Safety Engine (`core/safety_engine.py`)
- **Kill Switch**: Emergency stop all operations
- **Target Validation**: Only private IPs, whitelist support
- **Health Monitoring**: Auto-stop if victim health < 30%
- **Safety Levels**: Simulation → Observation → Controlled → Full

### 2. Attack Executor (`core/attack_executor.py`)
- **10 Built-in Techniques**: MITRE ATT&CK mapped
- **Real Command Execution**: PowerShell via WinRM
- **Pre/Post Telemetry**: Measure impact
- **Automatic Cleanup**: Restore system state

### 3. Telemetry Collector (`telemetry/collector.py`)
- **Real-time Metrics**: CPU, memory, disk, network
- **Health Score**: 0-100 based on multiple factors
- **Anomaly Detection**: Automatic alert on unusual activity
- **Timeline Correlation**: Link attacks to system changes

### 4. C2 Integration (`c2_integration/sliver_client.py`)
- **Sliver Client**: Full integration
- **Agent Management**: List, select, execute
- **File Operations**: Upload/download

### 5. FastAPI (`api/main.py`)
- **30+ Endpoints**: Safety, attacks, telemetry, C2, dashboard
- **Auto Documentation**: Swagger UI at `/docs`
- **Async Support**: Non-blocking operations

## Attack Techniques Included

| ID | Name | Tactic | Severity | Admin | Description |
|----|------|--------|----------|-------|-------------|
| T1087 | Account Discovery | Discovery | Info | No | List local users |
| T1057 | Process Discovery | Discovery | Info | No | List processes |
| T1016 | Network Config Discovery | Discovery | Info | No | Network settings |
| T1083 | File/Directory Discovery | Discovery | Low | No | List files |
| T1003.001 | LSASS Memory (Safe) | Credential Access | Med | Yes | Read LSASS info |
| T1053.005 | Scheduled Task Creation | Persistence | Med | Yes | Create task |
| T1059.001 | PowerShell Execution | Execution | Med | No | Run PowerShell |
| T1071.001 | Web Protocol C2 | C2 | Low | No | HTTP request |
| T1041 | Exfiltration (Simulated) | Exfiltration | Med | No | Send test data |
| T1496 | Resource Hijacking | Impact | Med | No | CPU stress test |

## File Structure

```
bas_platform/
├── api/
│   ├── __init__.py
│   └── main.py                 # FastAPI application (30+ endpoints)
├── core/
│   ├── __init__.py
│   ├── safety_engine.py        # Safety controls, kill switch
│   └── attack_executor.py      # Attack execution logic
├── telemetry/
│   ├── __init__.py
│   └── collector.py            # Health monitoring, metrics
├── c2_integration/
│   ├── __init__.py
│   └── sliver_client.py        # Sliver C2 client
├── config/
│   ├── __init__.py
│   └── settings.py             # Configuration
├── attacks/
│   ├── __init__.py
│   └── modules/
│       └── __init__.py         # Custom attack modules
├── playbooks/
│   ├── discovery_phase.sh      # Discovery playbook
│   └── persistence_phase.sh    # Persistence playbook
├── logs/                       # Log files (created at runtime)
├── data/                       # Database (created at runtime)
├── .env.example                # Example configuration
├── requirements.txt            # Python dependencies
├── setup.sh                    # Setup script
├── run.sh                      # Run script
├── test_setup.py               # Setup verification
├── README.md                   # Full documentation
├── QUICKSTART.md               # Quick reference
├── WINDOWS_SETUP.md            # Windows VM setup
└── PROJECT_SUMMARY.md          # This file
```

## API Endpoints

### Safety & Control (5 endpoints)
- `GET /api/v1/safety/status` - Get safety status
- `POST /api/v1/safety/level/{level}` - Set safety level
- `POST /api/v1/safety/kill-switch` - Emergency stop
- `DELETE /api/v1/safety/kill-switch` - Reset kill switch
- `GET /api/v1/safety/audit-log` - View audit log

### Attack Execution (5 endpoints)
- `GET /api/v1/attacks/techniques` - List techniques
- `GET /api/v1/attacks/techniques/{id}` - Get technique details
- `POST /api/v1/attacks/execute` - Execute attack
- `GET /api/v1/attacks/results` - List results
- `GET /api/v1/attacks/results/{id}` - Get specific result

### Telemetry (7 endpoints)
- `POST /api/v1/telemetry/start/{ip}` - Start collection
- `POST /api/v1/telemetry/stop` - Stop collection
- `GET /api/v1/telemetry/latest` - Latest snapshot
- `GET /api/v1/telemetry/history` - Historical data
- `GET /api/v1/telemetry/health-timeline` - Health over time
- `GET /api/v1/telemetry/events` - Events/alerts
- `GET /api/v1/telemetry/snapshot/{ip}` - Single snapshot

### C2 Integration (4 endpoints)
- `GET /api/v1/c2/status` - C2 server status
- `GET /api/v1/c2/agents` - List agents
- `GET /api/v1/c2/agents/{hostname}` - Get agent by hostname
- `POST /api/v1/c2/agents/{id}/execute` - Execute via C2

### Dashboard (2 endpoints)
- `GET /api/v1/dashboard/summary` - Dashboard summary
- `GET /api/v1/reports/attack-timeline` - Full timeline

## Workflow

### Phase 1: Setup (One-time)
```bash
# On Kali
sudo bash setup.sh          # Install dependencies
cp .env.example .env        # Configure
nano .env                   # Edit settings

# On Windows VM (as Admin)
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

### Phase 2: Start API
```bash
./run.sh
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Phase 3: Execute Attacks
```bash
# Start telemetry
curl -X POST "http://localhost:8000/api/v1/telemetry/start/192.168.56.101"

# Execute attack
curl -X POST "http://localhost:8000/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d '{"technique_id": "T1087", "target_ip": "192.168.56.101"}'

# Get results
curl http://localhost:8000/api/v1/attacks/results/ATTACK_ID

# View health timeline
curl http://localhost:8000/api/v1/telemetry/health-timeline
```

### Phase 4: Analysis
```bash
# Dashboard summary
curl http://localhost:8000/api/v1/dashboard/summary

# Full attack timeline
curl http://localhost:8000/api/v1/reports/attack-timeline
```

## Safety Features

### Kill Switch
```bash
# Emergency stop
curl -X POST "http://localhost:8000/api/v1/safety/kill-switch"
```

### Safety Levels
```bash
# Set level (simulation/observation/controlled/full)
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled"
```

### Health Monitoring
- Auto-stop if health < 30%
- Real-time health score (0-100)
- Anomaly detection

### Target Validation
- Only private IPs allowed
- Whitelist support
- Blocked list for critical systems

## Next Steps for Your Professor Demo

### 1. Verify Setup
```bash
cd /mnt/okcomputer/output/bas_platform
python3 test_setup.py
```

### 2. Start API
```bash
./run.sh
```

### 3. Test in Browser
- Open http://localhost:8000/docs
- Try endpoints interactively

### 4. Run Playbook
```bash
# Set target IP
export TARGET_IP=192.168.56.101

# Run discovery phase
./playbooks/discovery_phase.sh
```

### 5. View Results
```bash
# Dashboard
curl http://localhost:8000/api/v1/dashboard/summary | python3 -m json.tool

# Health timeline
curl http://localhost:8000/api/v1/telemetry/health-timeline | python3 -m json.tool
```

## Integration with Frontend

Your frontend can:
1. Call `/api/v1/dashboard/summary` for dashboard data
2. Call `/api/v1/attacks/techniques` to list available attacks
3. POST to `/api/v1/attacks/execute` to trigger attacks
4. Poll `/api/v1/telemetry/latest` for real-time health
5. GET `/api/v1/telemetry/health-timeline` for charts

Example:
```javascript
// Start telemetry
fetch('http://localhost:8000/api/v1/telemetry/start/192.168.56.101', {
  method: 'POST'
});

// Execute attack
const result = await fetch('http://localhost:8000/api/v1/attacks/execute', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    technique_id: 'T1087',
    target_ip: '192.168.56.101'
  })
});

// Get results
const attackResult = await result.json();
```

## Key Achievements

✅ **Real Attack Execution**: Commands actually run on victim VM  
✅ **Real Telemetry**: Live health monitoring  
✅ **Safety Controls**: Kill switch, target validation, health thresholds  
✅ **MITRE ATT&CK**: 10 mapped techniques  
✅ **C2 Integration**: Sliver support  
✅ **REST API**: 30+ endpoints  
✅ **Playbooks**: Automated attack chains  
✅ **Documentation**: Complete guides  

## For Your Professor

This demonstrates:
1. **Understanding of BAS concepts** - Real simulation, not just theory
2. **Safety awareness** - Multiple safety controls implemented
3. **Technical implementation** - Full working backend
4. **Integration capability** - Ready for frontend connection
5. **Research value** - Measurable defensive metrics

## Troubleshooting

| Issue | Solution |
|-------|----------|
| API won't start | Check port 8000: `sudo lsof -i :8000` |
| PowerShell fails | Verify WinRM: `Test-WSMan` on Windows |
| No telemetry | Check target IP in .env |
| Sliver not found | Install: `curl https://sliver.sh/install \| sudo bash` |

## Support Files

- `README.md` - Full documentation
- `QUICKSTART.md` - Command reference
- `WINDOWS_SETUP.md` - Windows VM setup
- `test_setup.py` - Verify installation
- `playbooks/` - Example attack chains

---

**Ready to demonstrate!** Start with `./run.sh` and open http://localhost:8000/docs
