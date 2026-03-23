#!/bin/bash
# Ransomware Simulation Playbook (SAFE)
# =====================================================
# Executes a safe ransomware simulation in a sandboxed directory
# to demonstrate impact and defense capabilities.

set -e

API_URL="${API_URL:-http://localhost:8000}"
TARGET_IP="${TARGET_IP:-192.168.56.102}"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'; NC='\033[0m'

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

submit_and_wait() {
    local technique_id=$1
    local name=$2
    
    echo ""
    echo -e "${BOLD}▶ Executing: ${technique_id} - ${name}${NC}"
    
    local response=$(curl -s -X POST "${API_URL}/api/v1/attacks/execute" \
        -H "Content-Type: application/json" \
        -d "{\"technique_id\": \"${technique_id}\", \"target_ip\": \"${TARGET_IP}\"}")

    local attack_id=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('attack_id',''))" 2>/dev/null)
    
    if [ -z "$attack_id" ]; then
        log_error "Failed to start attack. Ensure Safety Level is set to 'full'"
        echo "$response"
        return
    fi
    
    log_info "Attack started (ID: ${attack_id}). Waiting for completion..."
    
    local max_wait=90; local waited=0
    while [ $waited -lt $max_wait ]; do
        sleep 3; waited=$((waited + 3))
        local result=$(curl -s "${API_URL}/api/v1/attacks/results/${attack_id}")
        local cur_status=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
        
        if [ "$cur_status" = "completed" ] || [ "$cur_status" = "failed" ] || [ "$cur_status" = "blocked" ]; then
            # Print output
            local output=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('command_output','') or '')" 2>/dev/null)
            local health=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d.get('health_impact',0):.2f}\")" 2>/dev/null)
            
            if [ -n "$output" ] && [ "$output" != "None" ]; then
                echo ""
                echo -e "${CYAN}┌─ TARGET VM OUTPUT ──────────────────────────────────────────┐${NC}"
                echo "$output" | while IFS= read -r line; do echo -e "${CYAN}│${NC} $line"; done
                echo -e "${CYAN}└──────────────────────────────────────────────────────────────┘${NC}"
            fi
            
            if [ "$cur_status" = "completed" ]; then
                log_success "${technique_id} completed successfully (Health impact: ${health})"
            elif [ "$cur_status" = "blocked" ]; then
                local err=$(echo "$result" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error_message','') or '')" 2>/dev/null)
                log_warning "${technique_id} was BLOCKED by safety engine or OS restrictions."
                echo "  Reason: $err"
            else
                log_error "${technique_id} failed"
            fi
            return
        fi
    done
    log_error "Timeout waiting for attack completion"
}

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║       Ransomware Simulation Playbook (SAFE)                  ║"
    echo "║       MITRE ATT&CK: Impact (TA0040)                          ║"
    echo "║       Target: ${TARGET_IP}                                   ║"
    echo "║       WARNING: This playbook requires 'full' safety level    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    check_api

    # Set safety level to FULL because ransomware payload is marked marked as destructive (meaning it writes/alters files)
    log_info "Setting safety level to FULL for ransomware simulation..."
    local safety_resp=$(curl -s -X POST "${API_URL}/api/v1/safety/level/full")
    local safety_success=$(echo "$safety_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('success', False))" 2>/dev/null)
    
    if [ "$safety_success" != "True" ]; then
        log_error "Failed to set FULL safety level. Simulation cannot proceed."
        echo "Response: $safety_resp"
        echo "Ensure LIVE_EXECUTION_ENABLED is True in config."
        exit 1
    fi
    log_success "Safety level: full"

    # Execute Ransomware Payload
    submit_and_wait "T1486" "Data Encrypted for Impact"

    # Reset safety level back to controlled
    curl -s -X POST "${API_URL}/api/v1/safety/level/controlled" > /dev/null
    log_success "Safety level restored to controlled"
    
    echo ""
    log_success "Ransomware Simulation Playbook completed!"
    echo "To demonstrate defense, test this playbook against Windows Defender Controlled Folder Access."
    echo ""
}

trap 'echo ""; log_warning "Interrupted"; curl -s -X POST "${API_URL}/api/v1/safety/level/controlled" > /dev/null; exit 1' INT
main
