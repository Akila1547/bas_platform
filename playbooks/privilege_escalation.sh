#!/bin/bash
# Privilege Escalation Playbook - ENHANCED with full output
# ==========================================================
# STANDALONE — does NOT require any prior playbook to run
# Shows UAC settings, token privileges, service enumeration output

set -e

API_URL="${API_URL:-http://localhost:8000}"
TARGET_IP="${TARGET_IP:-192.168.56.102}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

check_api() {
    if ! curl -s "${API_URL}/health" > /dev/null 2>&1; then
        log_error "API not reachable. Start with: ./run.sh"; exit 1
    fi
    log_success "API reachable"
}

execute_and_show() {
    local technique_id=$1
    local name=$2

    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  ATTACK: ${technique_id} — ${name}${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    local response=$(curl -s -X POST "${API_URL}/api/v1/attacks/execute" \
        -H "Content-Type: application/json" \
        -d "{\"technique_id\": \"${technique_id}\", \"target_ip\": \"${TARGET_IP}\"}")

    local attack_id=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('attack_id',''))" 2>/dev/null)

    if [ -z "$attack_id" ]; then
        log_error "Failed to submit attack: $response"; return 1
    fi

    log_info "Submitted (ID: ${attack_id}), waiting..."

    local max_wait=90; local waited=0
    while [ $waited -lt $max_wait ]; do
        sleep 3; waited=$((waited + 3))
        local result=$(curl -s "${API_URL}/api/v1/attacks/results/${attack_id}")
        local cur_status=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)

        if [ "$cur_status" = "completed" ] || [ "$cur_status" = "failed" ] || [ "$cur_status" = "blocked" ]; then
            local health=$(echo "$result"   | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('health_impact',0):.2f}\")" 2>/dev/null)
            local duration=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('duration_seconds',0):.1f}\")" 2>/dev/null)
            local output=$(echo "$result"   | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('command_output','') or '')" 2>/dev/null)

            [ "$cur_status" = "completed" ] && log_success "${technique_id} done in ${duration}s | Health impact: ${health}"
            [ "$cur_status" = "blocked"   ] && log_warning "${technique_id} blocked by safety controls"
            [ "$cur_status" = "failed"    ] && log_error   "${technique_id} failed"

            if [ -n "$output" ] && [ "$output" != "None" ]; then
                echo ""
                echo -e "${CYAN}┌─ OUTPUT ────────────────────────────────────────────────────┐${NC}"
                echo "$output" | while IFS= read -r line; do echo -e "${CYAN}│${NC} $line"; done
                echo -e "${CYAN}└──────────────────────────────────────────────────────────────┘${NC}"
            fi
            echo ""; return 0
        fi
        log_info "  Waiting... (${waited}s)"
    done
    log_warning "Timed out after ${max_wait}s"
}

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║         Privilege Escalation Attack Playbook                 ║"
    echo "║         MITRE ATT&CK: Privilege Escalation (TA0004)          ║"
    echo "║         Target: ${TARGET_IP}                                 ║"
    echo "║         NOTE: STANDALONE — no prior playbook needed          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    check_api
    curl -s -X POST "${API_URL}/api/v1/safety/level/controlled" > /dev/null
    log_success "Safety level: controlled"
    curl -s -X POST "${API_URL}/api/v1/telemetry/start/${TARGET_IP}?interval=5" > /dev/null
    log_success "Telemetry started"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║         EXECUTING PRIVILEGE ESCALATION ATTACKS               ║"
    echo "╚══════════════════════════════════════════════════════════════╝"

    execute_and_show "T1548.002" "UAC Bypass — Check UAC registry settings"
    execute_and_show "T1134.001" "Token Impersonation — Enumerate user privileges"
    execute_and_show "T1543.003" "Windows Service — Enumerate auto-start services"

    echo ""
    local health=$(curl -s "${API_URL}/api/v1/telemetry/latest")
    local score=$(echo "$health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('health_score',0):.2f}\")" 2>/dev/null)
    echo "╔══════════════════════════════════════════════════════════════╗"
    printf "║  FINAL HEALTH SCORE: %-6s / 100                           ║\n" "$score"
    echo "╚══════════════════════════════════════════════════════════════╝"

    curl -s -X POST "${API_URL}/api/v1/telemetry/stop" > /dev/null
    log_success "Privilege Escalation playbook completed!"
    echo ""
}

trap 'echo ""; log_warning "Interrupted"; curl -s -X POST "${API_URL}/api/v1/telemetry/stop" > /dev/null; exit 1' INT
main
