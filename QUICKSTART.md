# BAS Platform - Quick Start Guide

## Step-by-Step Commands

### PHASE 1: Kali Linux Setup (BAS Platform)

```bash
# 1. Navigate to project directory
cd /mnt/okcomputer/output/bas_platform

# 2. Run setup script (installs Python, PowerShell, Sliver)
sudo bash setup.sh

# 3. Configure environment
cp .env.example .env
nano .env  # Edit with your victim IP and credentials

# 4. Start the API
./run.sh
```

### PHASE 2: Windows VM Setup (Victim)

On Windows VM (run PowerShell as Administrator):

```powershell
# 1. Enable PowerShell remoting
Enable-PSRemoting -Force

# 2. Add Kali to trusted hosts
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force

# 3. Start WinRM service
Set-Service WinRM -StartupType Automatic
Start-Service WinRM

# 4. Enable firewall rules
Enable-NetFirewallRule -DisplayGroup "Windows Remote Management"

# 5. Verify
Test-WSMan
```

### PHASE 3: Test Connectivity

From Kali (new terminal):

```bash
# Test PowerShell remoting
crackmapexec winrm 192.168.56.101

# Or test with evil-winrm
evil-winrm -i 192.168.56.101 -u Administrator -p 'YourPassword'
```

### PHASE 4: API Testing

```bash
# 1. Check API is running
curl http://localhost:8000/health

# 2. Check safety status
curl http://localhost:8000/api/v1/safety/status

# 3. List attack techniques
curl http://localhost:8000/api/v1/attacks/techniques

# 4. Start telemetry collection
curl -X POST "http://localhost:8000/api/v1/telemetry/start/192.168.56.101"

# 5. Get latest telemetry
curl http://localhost:8000/api/v1/telemetry/latest
```

### PHASE 5: Execute First Attack

```bash
# Execute Account Discovery (T1087)
curl -X POST "http://localhost:8000/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "technique_id": "T1087",
    "target_ip": "192.168.56.101"
  }'

# Response will contain attack_id
# {
#   "attack_id": "abc123",
#   "status": "completed"
# }

# Get detailed results
curl http://localhost:8000/api/v1/attacks/results/abc123
```

### PHASE 6: Enable Live Execution (When Ready)

```bash
# 1. Edit .env to enable live execution
nano .env
# Change: LIVE_EXECUTION_ENABLED=true

# 2. Restart API
# Press Ctrl+C, then:
./run.sh

# 3. Set safety level to controlled
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled"

# 4. Execute attacks (now with real commands)
curl -X POST "http://localhost:8000/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "technique_id": "T1057",
    "target_ip": "192.168.56.101"
  }'
```

## Common Commands Reference

### Safety Controls
```bash
# Get status
curl http://localhost:8000/api/v1/safety/status

# Set level (simulation/observation/controlled/full)
curl -X POST "http://localhost:8000/api/v1/safety/level/controlled"

# Emergency kill switch
curl -X POST "http://localhost:8000/api/v1/safety/kill-switch?reason=Emergency+stop"

# Reset kill switch
curl -X DELETE "http://localhost:8000/api/v1/safety/kill-switch"
```

### Telemetry
```bash
# Start collection
curl -X POST "http://localhost:8000/api/v1/telemetry/start/192.168.56.101?interval=5"

# Stop collection
curl -X POST "http://localhost:8000/api/v1/telemetry/stop"

# Get latest
curl http://localhost:8000/api/v1/telemetry/latest

# Get history
curl "http://localhost:8000/api/v1/telemetry/history?count=50"

# Get health timeline (for charts)
curl http://localhost:8000/api/v1/telemetry/health-timeline

# Get events/alerts
curl "http://localhost:8000/api/v1/telemetry/events?severity=warning"
```

### Attack Execution
```bash
# List techniques
curl http://localhost:8000/api/v1/attacks/techniques

# Get technique details
curl http://localhost:8000/api/v1/attacks/techniques/T1087

# Execute attack
curl -X POST "http://localhost:8000/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "technique_id": "T1087",
    "target_ip": "192.168.56.101"
  }'

# List all results
curl http://localhost:8000/api/v1/attacks/results

# Get specific result
curl http://localhost:8000/api/v1/attacks/results/abc123
```

### C2 Integration
```bash
# Check C2 status
curl http://localhost:8000/api/v1/c2/status

# List agents
curl http://localhost:8000/api/v1/c2/agents

# Execute via C2
curl -X POST "http://localhost:8000/api/v1/c2/agents/SESSION_ID/execute?command=whoami"
```

### Dashboard & Reports
```bash
# Get dashboard summary
curl http://localhost:8000/api/v1/dashboard/summary

# Get attack timeline with telemetry
curl http://localhost:8000/api/v1/reports/attack-timeline
```

## Attack Playbook Example

```bash
#!/bin/bash
# Example: Discovery Phase Playbook

TARGET="192.168.56.101"
API="http://localhost:8000"

echo "=== Starting Discovery Phase ==="

# Start telemetry
curl -s -X POST "$API/api/v1/telemetry/start/$TARGET?interval=5" > /dev/null

# T1087 - Account Discovery
echo "[1/4] Account Discovery"
curl -s -X POST "$API/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d "{\"technique_id\": \"T1087\", \"target_ip\": \"$TARGET\"}"
sleep 2

# T1057 - Process Discovery
echo "[2/4] Process Discovery"
curl -s -X POST "$API/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d "{\"technique_id\": \"T1057\", \"target_ip\": \"$TARGET\"}"
sleep 2

# T1016 - Network Config Discovery
echo "[3/4] Network Config Discovery"
curl -s -X POST "$API/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d "{\"technique_id\": \"T1016\", \"target_ip\": \"$TARGET\"}"
sleep 2

# T1083 - File Discovery
echo "[4/4] File Discovery"
curl -s -X POST "$API/api/v1/attacks/execute" \
  -H "Content-Type: application/json" \
  -d "{\"technique_id\": \"T1083\", \"target_ip\": \"$TARGET\"}"

echo ""
echo "=== Discovery Phase Complete ==="
echo "Health Impact:"
curl -s "$API/api/v1/telemetry/latest" | grep -o '"health_score":[0-9.]*'
```

## Troubleshooting

### API won't start
```bash
# Check port usage
sudo lsof -i :8000

# Use different port
python -m uvicorn api.main:app --port 8001
```

### PowerShell remoting fails
```bash
# Test WinRM
crackmapexec winrm 192.168.56.101

# On Windows, reset WinRM
Disable-PSRemoting -Force
Enable-PSRemoting -Force -SkipNetworkProfileCheck
```

### No telemetry data
```bash
# Check if collection is running
curl http://localhost:8000/api/v1/telemetry/latest

# Restart collection
curl -X POST "http://localhost:8000/api/v1/telemetry/stop"
curl -X POST "http://localhost:8000/api/v1/telemetry/start/192.168.56.101"
```

## File Locations

| File | Purpose |
|------|---------|
| `.env` | Configuration |
| `logs/bas_platform.log` | Application logs |
| `data/bas_platform.db` | SQLite database |
| `api/main.py` | FastAPI application |

## Next Steps

1. **Review API Documentation**: http://localhost:8000/docs
2. **Test all techniques**: Start with informational ones
3. **Monitor health**: Watch telemetry during attacks
4. **Create playbooks**: Chain techniques together
5. **Build UI**: Integrate with your frontend
