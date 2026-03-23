#!/bin/bash
# Defense Evasion Playbook - ADAPTIVE with full output
# =====================================================
# STANDALONE — no prior playbook needed
# Demonstrates adaptive attack: if primary is blocked, auto-pivots to fallback
# Shows actual output of each technique

set -e

API_URL="${API_URL:-http://localhost:8000}"
TARGET_IP="${TARGET_IP:-192.168.56.102}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'; NC='\033[0m'

log_info()     { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success()  { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning()  { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()    { echo -e "${RED}[ERROR]${NC} $1"; }
log_adaptive() { echo -e "${MAGENTA}[ADAPTIVE]${NC} $1"; }

check_api() {
    if ! curl -s "${API_URL}/health" > /dev/null 2>&1; then
        log_error "API not reachable. Start with: ./run.sh"; exit 1
    fi
    log_success "API reachable"
}

# Submit attack and wait for result, return status
submit_and_wait() {
    local technique_id=$1
    local response=$(curl -s -X POST "${API_URL}/api/v1/attacks/execute" \
        -H "Content-Type: application/json" \
        -d "{\"technique_id\": \"${technique_id}\", \"target_ip\": \"${TARGET_IP}\"}")

    local attack_id=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('attack_id',''))" 2>/dev/null)

    if [ -z "$attack_id" ]; then echo "error"; return; fi

    local max_wait=90; local waited=0
    while [ $waited -lt $max_wait ]; do
        sleep 3; waited=$((waited + 3))
        local result=$(curl -s "${API_URL}/api/v1/attacks/results/${attack_id}")
        local cur_status=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)

        if [ "$cur_status" = "completed" ] || [ "$cur_status" = "failed" ] || [ "$cur_status" = "blocked" ]; then
            # Print output
            local output=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('command_output','') or '')" 2>/dev/null)
            local health=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('health_impact',0):.2f}\")" 2>/dev/null)
            local duration=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('duration_seconds',0):.1f}\")" 2>/dev/null)

            if [ -n "$output" ] && [ "$output" != "None" ]; then
                echo "" >&2
                echo -e "${CYAN}┌─ OUTPUT ────────────────────────────────────────────────────┐${NC}" >&2
                echo "$output" | while IFS= read -r line; do echo -e "${CYAN}│${NC} $line" >&2; done
                echo -e "${CYAN}└──────────────────────────────────────────────────────────────┘${NC}" >&2
            fi
            echo "  Duration: ${duration}s | Health impact: ${health}" >&2
            echo "$cur_status"
            return
        fi
    done
    echo "timeout"
}

# Adaptive execution: try primary, fallback if it fails/blocks
execute_adaptive_pair() {
    local primary_id=$1
    local primary_name=$2
    local fallback_id=$3
    local fallback_name=$4

    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  ADAPTIVE PAIR${NC}"
    echo -e "  Primary  : ${BOLD}${primary_id}${NC} — ${primary_name}"
    echo -e "  Fallback : ${BOLD}${fallback_id}${NC} — ${fallback_name}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    log_info "Trying PRIMARY: ${primary_id} — ${primary_name}"
    local primary_status=$(submit_and_wait "$primary_id")

    if [ "$primary_status" = "completed" ]; then
        log_success "✓ Primary succeeded: ${primary_id}"
        return 0
    else
        log_warning "✗ Primary ${primary_status}: ${primary_id}"
        log_adaptive "→ PIVOTING to fallback technique..."
        echo ""
        log_info "Trying FALLBACK: ${fallback_id} — ${fallback_name}"
        local fallback_status=$(submit_and_wait "$fallback_id")

        if [ "$fallback_status" = "completed" ]; then
            log_success "✓ Fallback succeeded: ${fallback_id}"
            log_adaptive "→ Attack chain adapted successfully!"
        else
            log_error "✗ Fallback also ${fallback_status}: ${fallback_id}"
            log_adaptive "→ Both techniques failed — target may be hardened"
        fi
    fi
    echo ""
}

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║       Defense Evasion Playbook (ADAPTIVE)                    ║"
    echo "║       MITRE ATT&CK: Defense Evasion (TA0005)                 ║"
    echo "║       Target: ${TARGET_IP}                                   ║"
    echo "║       NOTE: STANDALONE — no prior playbook needed            ║"
    echo "║       FEATURE: Auto-pivots to fallback on failure            ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    check_api
    curl -s -X POST "${API_URL}/api/v1/safety/level/controlled" > /dev/null
    log_success "Safety level: controlled"
    curl -s -X POST "${API_URL}/api/v1/telemetry/start/${TARGET_IP}?interval=5" > /dev/null
    log_success "Telemetry started"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              ADAPTIVE ATTACK CHAIN                           ║"
    echo "║  Each pair: tries primary first, auto-pivots if blocked      ║"
    echo "╚══════════════════════════════════════════════════════════════╝"

    # Adaptive pair 1: Disable Defender → Disable Firewall
    execute_adaptive_pair \
        "T1562.001" "Disable Windows Defender" \
        "T1562.004" "Disable Firewall"

    # Adaptive pair 2: Clear Event Logs → Obfuscate PowerShell
    execute_adaptive_pair \
        "T1070.001" "Clear Event Logs" \
        "T1027.002" "Obfuscated PowerShell"

    echo ""
    local health=$(curl -s "${API_URL}/api/v1/telemetry/latest")
    local score=$(echo "$health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('health_score',0):.2f}\")" 2>/dev/null)
    echo "╔══════════════════════════════════════════════════════════════╗"
    printf "║  FINAL HEALTH SCORE: %-6s / 100                           ║\n" "$score"
    echo "╚══════════════════════════════════════════════════════════════╝"

    curl -s -X POST "${API_URL}/api/v1/telemetry/stop" > /dev/null
    log_success "Defense Evasion (Adaptive) playbook completed!"
    log_adaptive "Adaptive fallback logic demonstrated"
    echo ""
}

trap 'echo ""; log_warning "Interrupted"; curl -s -X POST "${API_URL}/api/v1/telemetry/stop" > /dev/null; exit 1' INT
main
