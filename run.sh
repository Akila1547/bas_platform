#!/bin/bash
# BAS Platform Run Script
# =======================

set -e

cd /home/akila/Desktop/bas_platform

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Running setup first...${NC}"
    bash setup.sh
fi

# Activate virtual environment
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# ── Auto-start Sliver HTTP C2 listener ────────────────────────────────────────
echo -e "${YELLOW}[Sliver C2] Checking HTTP listener on port 8443...${NC}"
if systemctl is-active sliver &>/dev/null; then
    timeout 12 python3 - << 'PYEOF' 2>/dev/null || echo -e "${YELLOW}[Sliver C2] Could not reach gRPC — run fix_sliver.sh if needed${NC}"
import asyncio
from sliver import SliverClientConfig, SliverClient
import os

async def ensure_listener():
    cfg_path = "/home/akila/.sliver-client/configs/bas_operator_localhost.cfg"
    if not os.path.exists(cfg_path):
        print("[Sliver C2] No operator config — run: sudo bash fix_sliver.sh")
        return
    try:
        cfg = SliverClientConfig.parse_config_file(cfg_path)
        client = SliverClient(cfg)
        await asyncio.wait_for(client.connect(), timeout=8)
        jobs = await asyncio.wait_for(client.jobs(), timeout=5)
        http_running = any(j.Port == 8443 for j in jobs)
        if not http_running:
            job = await asyncio.wait_for(
                client.start_http_listener(host="0.0.0.0", port=8443, domain="", website=""),
                timeout=8
            )
            print(f"[Sliver C2] ✅ HTTP listener started on :8443 (Job {job.JobID})")
        else:
            print("[Sliver C2] ✅ HTTP listener already running on :8443")
        beacons = await asyncio.wait_for(client.beacons(), timeout=5)
        sessions = await asyncio.wait_for(client.sessions(), timeout=5)
        print(f"[Sliver C2]    Beacons={len(beacons)}  Sessions={len(sessions)}")
    except Exception as e:
        print(f"[Sliver C2] gRPC error: {e}")

asyncio.run(ensure_listener())
PYEOF
else
    echo -e "${YELLOW}[Sliver C2] Service not running — start with: sudo systemctl start sliver${NC}"
fi
# ──────────────────────────────────────────────────────────────────────────────

echo -e "${GREEN}Starting BAS Platform API...${NC}"
echo ""
echo "Configuration:"
echo "  Host: ${API_HOST:-0.0.0.0}"
echo "  Port: ${API_PORT:-8000}"
echo "  Debug: ${DEBUG:-false}"
echo ""
echo "Endpoints:"
echo "  API: http://localhost:${API_PORT:-8000}"
echo "  Docs: http://localhost:${API_PORT:-8000}/docs"
echo "  Health: http://localhost:${API_PORT:-8000}/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run the API
python -m uvicorn api.main:app --host ${API_HOST:-0.0.0.0} --port ${API_PORT:-8000} --reload
