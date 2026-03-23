#!/bin/bash
# Persistence Phase Playbook
# ==========================
# Executes persistence techniques to simulate attacker establishing foothold

set -e

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
TARGET_IP="${TARGET_IP:-192.168.56.101}"
TELEMETRY_INTERVAL="${TELEMETRY_INTERVAL:-5}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_api() {
    log_info "Checking API connectivity..."
    if curl -s "${API_URL}/health" > /dev/null; then
        log_success "API is reachable"
    else
        log_error "API not reachable"
        exit 1
    fi
}

check_safety() {
    log_info "Checking safety status..."
    local status=$(curl -s "${API_URL}/api/v1/safety/status" | grep -o '"level":"[^"]*"' | cut -d'"' -f4)
    log_info "Safety level: ${status}"
}

start_telemetry() {
    log_info "Starting telemetry collection..."
    curl -s -X POST "${API_URL}/api/v1/telemetry/start/${TARGET_IP}?interval=${TELEMETRY_INTERVAL}" > /dev/null
    log_success "Telemetry started"
}

stop_telemetry() {
    log_info "Stopping telemetry..."
    curl -s -X POST "${API_URL}/api/v1/telemetry/stop" > /dev/null
}

execute_attack() {
    local technique_id=$1
    local name=$2
    
    log_info "Executing ${technique_id} - ${name}..."
    
    local response=$(curl -s -X POST "${API_URL}/api/v1/attacks/execute" \
        -H "Content-Type: application/json" \
        -d "{\"technique_id\": \"${technique_id}\", \"target_ip\": \"${TARGET_IP}\"}")
    
    local attack_id=$(echo "$response" | grep -o '"attack_id":"[^"]*"' | cut -d'"' -f4)
    local status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$status" = "completed" ]; then
        log_success "${technique_id} completed"
    elif [ "$status" = "blocked" ]; then
        log_warning "${technique_id} blocked by safety controls"
    else
        log_error "${technique_id} failed"
    fi
    
    sleep 2
}

main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║         Persistence Phase Attack Playbook                    ║"
    echo "║         MITRE ATT&CK: Persistence Tactic                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    check_api
    check_safety
    start_telemetry
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    EXECUTING ATTACKS                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # T1053.005 - Scheduled Task Creation
    execute_attack "T1053.005" "Scheduled Task Creation"
    
    # T1059.001 - PowerShell Execution
    execute_attack "T1059.001" "PowerShell Execution"
    
    echo ""
    
    # Get final health
    local health=$(curl -s "${API_URL}/api/v1/telemetry/latest")
    local score=$(echo "$health" | grep -o '"health_score":[^,}]*' | cut -d':' -f2)
    
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                    FINAL HEALTH: $(printf '%6.2f' "$score")                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""
    
    stop_telemetry
    log_success "Persistence phase completed!"
    echo ""
}

trap 'echo ""; log_warning "Interrupted"; stop_telemetry; exit 1' INT

main
