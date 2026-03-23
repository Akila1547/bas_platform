# BAS Platform - Quick Start Guide

## 🚀 System Status

**Platform**: Fully Operational ✅  
**Total Playbooks**: 6  
**Total Techniques**: 22  
**Adaptive Capabilities**: Enabled  

---

## Available Playbooks

### 1. Discovery Phase
```bash
./playbooks/discovery_phase.sh
```
**Techniques**: T1087, T1057, T1016, T1083

### 2. Persistence Phase
```bash
./playbooks/persistence_phase.sh
```
**Techniques**: T1053.005, T1059.001

### 3. Credential Access
```bash
./playbooks/credential_access.sh
```
**Techniques**: T1555.003, T1552.001, T1003.001

### 4. Privilege Escalation
```bash
./playbooks/privilege_escalation.sh
```
**Techniques**: T1548.002, T1134.001, T1543.003

### 5. Defense Evasion (Adaptive) ⚡
```bash
./playbooks/defense_evasion_adaptive.sh
```
**Techniques**: T1562.001 → T1562.004, T1070.001 → T1027.002  
**Features**: Automatic fallback on technique failure

### 6. Lateral Movement
```bash
./playbooks/lateral_movement.sh
```
**Techniques**: T1021.001, T1021.002, T1570

---

## Quick Commands

### Start API Server
```bash
./run.sh
```

### Set Safety Level
```bash
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled"
```

### Execute Single Attack
```bash
curl -X POST "http://localhost:8000/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d '{"technique_id": "T1087", "target_ip": "192.168.56.102"}'
```

### Check System Health
```bash
curl http://localhost:8000/health
```

---

## Next Steps

### Sliver C2 Integration (Optional)
1. Start Sliver server
2. Generate implant for Windows VM
3. Deploy and establish session
4. Use C2-based lateral movement playbook

### UI Development (Optional)
- Web dashboard for attack execution
- Real-time telemetry visualization
- Attack chain builder
- Report generation interface

---

## Troubleshooting

### Credential Issues
Ensure `.env` file has correct credentials:
```
VICTIM_USERNAME=akila
VICTIM_PASSWORD=1123
```

### API Not Starting
Check logs:
```bash
tail -f api.log
```

### Attacks Failing
1. Verify WinRM connectivity:
```bash
python3 test_winrm.py
```

2. Check safety level:
```bash
curl http://localhost:8000/api/v1/safety/status
```

---

## Documentation

- **Full Walkthrough**: `walkthrough.md`
- **Implementation Plan**: `implementation_plan.md`
- **Windows Verification**: `WINDOWS_VERIFICATION.md`
- **Project Summary**: `PROJECT_SUMMARY.md`
