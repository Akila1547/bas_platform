#!/bin/bash
# Discovery Phase Playbook - ENHANCED with full output
# =====================================================
# Each attack shows its FULL command output from the Windows VM
# Playbooks are INDEPENDENT - no sequential dependency required

set -e

API_URL="${API_URL:-http://localhost:8000}"
TARGET_IP="${TARGET_IP:-192.168.56.102}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_output()  { echo -e "${CYAN}$1${NC}"; }

check_api() {
    if ! curl -s "${API_URL}/health" > /dev/null 2>&1; then
        log_error "API not reachable at ${API_URL}. Start with: ./run.sh"
        exit 1
    fi
    log_success "API reachable at ${API_URL}"
}

# Execute attack AND wait for completion, then print full output
execute_and_show() {
    local technique_id=$1
    local name=$2

    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}  ATTACK: ${technique_id} — ${name}${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Submit attack
    local response=$(curl -s -X POST "${API_URL}/api/v1/attacks/execute" \
        -H "Content-Type: application/json" \
        -d "{\"technique_id\": \"${technique_id}\", \"target_ip\": \"${TARGET_IP}\"}")

    local attack_id=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('attack_id',''))" 2>/dev/null)
    local status=$(echo "$response"   | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)

    if [ -z "$attack_id" ]; then
        log_error "Failed to submit attack. Response: $response"
        return 1
    fi

    log_info "Attack submitted (ID: ${attack_id}), waiting for completion..."

    # Poll until done
    local max_wait=60
    local waited=0
    while [ $waited -lt $max_wait ]; do
        sleep 3
        waited=$((waited + 3))
        local result=$(curl -s "${API_URL}/api/v1/attacks/results/${attack_id}")
        local cur_status=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)

        if [ "$cur_status" = "completed" ] || [ "$cur_status" = "failed" ] || [ "$cur_status" = "blocked" ]; then
            # Extract fields
            local health=$(echo "$result"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('health_impact',0):.2f}\")" 2>/dev/null)
            local duration=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('duration_seconds',0):.1f}\")" 2>/dev/null)
            local output=$(echo "$result"  | python3 -c "
import sys, json
d = json.load(sys.stdin)
out = d.get('command_output', '') or ''
print(out)
" 2>/dev/null)

            if [ "$cur_status" = "completed" ]; then
                log_success "${technique_id} completed in ${duration}s | Health impact: ${health}"
            elif [ "$cur_status" = "blocked" ]; then
                log_warning "${technique_id} blocked by safety controls"
            else
                log_error "${technique_id} failed"
            fi

            # Print the actual command output
            if [ -n "$output" ] && [ "$output" != "None" ]; then
                echo ""
                echo -e "${CYAN}┌─ COMMAND OUTPUT ────────────────────────────────────────────┐${NC}"
                echo "$output" | while IFS= read -r line; do
                    echo -e "${CYAN}│${NC} $line"
                done
                echo -e "${CYAN}└──────────────────────────────────────────────────────────────┘${NC}"
            fi

            echo ""
            return 0
        fi
        log_info "  Waiting... (${waited}s)"
    done

    log_warning "${technique_id} timed out after ${max_wait}s"
}

get_final_health() {
    local health=$(curl -s "${API_URL}/api/v1/telemetry/latest")
    local score=$(echo "$health"  | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('health_score',0):.2f}\")" 2>/dev/null)
    local cpu=$(echo "$health"    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('cpu_percent',0):.1f}\")" 2>/dev/null)
    local memory=$(echo "$health" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('memory_percent',0):.1f}\")" 2>/dev/null)

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    FINAL HEALTH STATUS                       ║"
    echo "╠══════════════════════════════════════════════════════════════╣"
    printf "║  Health Score:  %-6s / 100                                 ║\n" "$score"
    printf "║  CPU Usage:     %-6s%%                                      ║\n" "$cpu"
    printf "║  Memory Usage:  %-6s%%                                      ║\n" "$memory"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
}

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║         Discovery Phase Attack Playbook                      ║"
    echo "║         MITRE ATT&CK: Discovery Tactic (TA0007)              ║"
    echo "║         Target: ${TARGET_IP}                                 ║"
    echo "║         NOTE: This playbook is STANDALONE (no dependencies)  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    check_api

    # Set safety level
    curl -s -X POST "${API_URL}/api/v1/safety/level/controlled" > /dev/null
    log_success "Safety level: controlled"

    # Start telemetry
    curl -s -X POST "${API_URL}/api/v1/telemetry/start/${TARGET_IP}?interval=5" > /dev/null
    log_success "Telemetry started"

    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              EXECUTING DISCOVERY ATTACKS                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"

    execute_and_show "T1087" "Account Discovery — List all local users"
    execute_and_show "T1057" "Process Discovery — List running processes"
    execute_and_show "T1016" "Network Config Discovery — Full network info"
    execute_and_show "T1083" "File & Directory Discovery — Enumerate files"

    get_final_health

    # Save report
    curl -s "${API_URL}/api/v1/reports/attack-timeline" | python3 -m json.tool \
        > "discovery_report_$(date +%Y%m%d_%H%M%S).json" 2>/dev/null
    log_info "Report saved to discovery_report_*.json"

    curl -s -X POST "${API_URL}/api/v1/telemetry/stop" > /dev/null
    log_success "Discovery phase playbook completed!"
    echo ""
}

trap 'echo ""; log_warning "Interrupted"; curl -s -X POST "${API_URL}/api/v1/telemetry/stop" > /dev/null; exit 1' INT
main
