"""
BAS Platform API
================
FastAPI application providing REST endpoints for:
- Attack execution and management
- Telemetry collection and queries
- C2 integration and agent management
- Safety controls and monitoring
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our modules
import sys
sys.path.insert(0, '/home/akila/Desktop/bas_platform')

from core.safety_engine import safety_engine, SafetyLevel, SafetyStatus
from core.attack_executor import attack_executor, AttackResult, AttackStatus, AttackSeverity
from telemetry.collector import telemetry_collector, SystemMetrics, TelemetryEvent
from c2_integration.sliver_client import sliver_client, SliverAgent


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic models for API
class AttackExecuteRequest(BaseModel):
    technique_id: str = Field(..., description="MITRE ATT&CK technique ID")
    target_ip: str = Field(..., description="Target IP address")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional parameters")


class AttackExecuteResponse(BaseModel):
    attack_id: str
    technique_id: str
    technique_name: str
    status: str
    message: str


class AttackResultResponse(BaseModel):
    attack_id: str
    technique_id: str
    technique_name: str
    status: str
    target_ip: str
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: float
    command_executed: Optional[str]
    command_output: Optional[str]
    exit_code: Optional[int]
    health_impact: float
    detection_indicators: List[str]
    error_message: Optional[str]


class TechniqueInfo(BaseModel):
    technique_id: str
    name: str
    description: str
    tactic: str
    severity: str
    requires_admin: bool
    expected_duration: int
    is_destructive: bool


class TelemetrySnapshot(BaseModel):
    timestamp: str
    target_ip: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_connections: int
    process_count: int
    health_score: float
    critical_services_status: Dict[str, str]


class HealthTimelinePoint(BaseModel):
    timestamp: str
    health_score: float
    cpu: float
    memory: float


class SafetyStatusResponse(BaseModel):
    level: str
    live_execution_enabled: bool
    health_monitor_active: bool
    kill_switch_triggered: bool
    last_check: str
    active_restrictions: List[str]


class C2AgentResponse(BaseModel):
    id: str
    name: str
    hostname: str
    username: str
    os: str
    status: str
    last_checkin: Optional[str]


# Startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("BAS Platform starting up...")
    
    # Connect to Sliver C2
    await sliver_client.connect()
    
    yield
    
    # Cleanup
    logger.info("BAS Platform shutting down...")
    await telemetry_collector.stop_collection()


# Create FastAPI app
app = FastAPI(
    title="Adaptive BAS Platform API",
    description="Backend API for Breach and Attack Simulation platform",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Safety & Control Endpoints
# ============================================================================

@app.get("/api/v1/safety/status", response_model=SafetyStatusResponse)
async def get_safety_status():
    """Get current safety system status"""
    status = safety_engine.get_status()
    return SafetyStatusResponse(
        level=status.level.value,
        live_execution_enabled=status.live_execution_enabled,
        health_monitor_active=status.health_monitor_active,
        kill_switch_triggered=status.kill_switch_triggered,
        last_check=status.last_check.isoformat(),
        active_restrictions=status.active_restrictions
    )


@app.post("/api/v1/safety/level/{level}")
async def set_safety_level(level: str):
    """Set safety level: simulation, observation, controlled, full"""
    try:
        safety_level = SafetyLevel(level.lower())
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid level. Choose from: {[l.value for l in SafetyLevel]}"
        )
    
    success = safety_engine.set_safety_level(safety_level)
    if not success:
        raise HTTPException(
            status_code=403,
            detail="Failed to set safety level. Check LIVE_EXECUTION_ENABLED config."
        )
    
    return {"message": f"Safety level set to {level}", "success": True}


@app.post("/api/v1/safety/kill-switch")
async def trigger_kill_switch(reason: str = "Manual trigger"):
    """Emergency stop all operations"""
    safety_engine.trigger_kill_switch(reason)
    await telemetry_collector.stop_collection()
    return {"message": "Kill switch activated", "reason": reason}


@app.delete("/api/v1/safety/kill-switch")
async def reset_kill_switch():
    """Reset kill switch (requires manual confirmation)"""
    safety_engine.reset_kill_switch()
    return {"message": "Kill switch reset"}


@app.get("/api/v1/safety/audit-log")
async def get_audit_log(limit: int = Query(100, ge=1, le=1000)):
    """Get safety audit log"""
    return safety_engine.get_audit_log(limit)


# ============================================================================
# Attack Execution Endpoints
# ============================================================================

@app.get("/api/v1/attacks/techniques", response_model=List[TechniqueInfo])
async def list_techniques(tactic: Optional[str] = None):
    """List all available attack techniques"""
    techniques = attack_executor.list_techniques(tactic)
    return [
        TechniqueInfo(
            technique_id=t.technique_id,
            name=t.name,
            description=t.description,
            tactic=t.tactic,
            severity=t.severity.value,
            requires_admin=t.requires_admin,
            expected_duration=t.expected_duration,
            is_destructive=t.is_destructive
        )
        for t in techniques
    ]


@app.get("/api/v1/attacks/techniques/{technique_id}")
async def get_technique(technique_id: str):
    """Get details of a specific technique"""
    technique = attack_executor.get_technique(technique_id)
    if not technique:
        raise HTTPException(status_code=404, detail="Technique not found")
    
    return {
        "technique_id": technique.technique_id,
        "name": technique.name,
        "description": technique.description,
        "tactic": technique.tactic,
        "severity": technique.severity.value,
        "command_template": technique.command_template,
        "requires_admin": technique.requires_admin,
        "expected_duration": technique.expected_duration,
        "is_destructive": technique.is_destructive,
        "cleanup_command": technique.cleanup_command,
        "expected_artifacts": technique.expected_artifacts,
        "detection_rules": technique.detection_rules
    }


@app.post("/api/v1/attacks/execute", response_model=AttackExecuteResponse)
async def execute_attack(request: AttackExecuteRequest, background_tasks: BackgroundTasks):
    """Execute an attack technique against a target"""
    
    # Validate technique exists
    technique = attack_executor.get_technique(request.technique_id)
    if not technique:
        raise HTTPException(status_code=404, detail=f"Technique {request.technique_id} not found")
    
    # Start telemetry collection if not running
    if not telemetry_collector._is_collecting:
        await telemetry_collector.start_continuous_collection(request.target_ip)
    
    # Execute attack (async)
    result = await attack_executor.execute_attack(
        request.technique_id,
        request.target_ip,
        request.parameters
    )
    
    return AttackExecuteResponse(
        attack_id=result.attack_id,
        technique_id=result.technique_id,
        technique_name=result.technique_name,
        status=result.status.value,
        message="Attack execution completed" if result.status == AttackStatus.COMPLETED else result.error_message or "Execution failed"
    )


@app.get("/api/v1/attacks/results/{attack_id}", response_model=AttackResultResponse)
async def get_attack_result(attack_id: str):
    """Get detailed results of an attack execution"""
    result = attack_executor.get_attack_result(attack_id)
    if not result:
        raise HTTPException(status_code=404, detail="Attack result not found")
    
    return AttackResultResponse(
        attack_id=result.attack_id,
        technique_id=result.technique_id,
        technique_name=result.technique_name,
        status=result.status.value,
        target_ip=result.target_ip,
        start_time=result.start_time,
        end_time=result.end_time,
        duration_seconds=result.duration_seconds,
        command_executed=result.command_executed,
        command_output=result.command_output,
        exit_code=result.exit_code,
        health_impact=result.health_impact,
        detection_indicators=result.detection_indicators,
        error_message=result.error_message
    )


@app.get("/api/v1/attacks/results")
async def list_attack_results():
    """List all attack execution results"""
    results = attack_executor.get_all_results()
    return [
        {
            "attack_id": r.attack_id,
            "technique_id": r.technique_id,
            "technique_name": r.technique_name,
            "status": r.status.value,
            "target_ip": r.target_ip,
            "duration_seconds": r.duration_seconds,
            "health_impact": r.health_impact
        }
        for r in results
    ]


# ============================================================================
# Telemetry Endpoints
# ============================================================================

@app.post("/api/v1/telemetry/start/{target_ip}")
async def start_telemetry(target_ip: str, interval: int = Query(5, ge=1, le=60)):
    """Start continuous telemetry collection from target"""
    await telemetry_collector.start_continuous_collection(target_ip, interval)
    return {
        "message": f"Telemetry collection started for {target_ip}",
        "interval_seconds": interval
    }


@app.post("/api/v1/telemetry/stop")
async def stop_telemetry():
    """Stop telemetry collection"""
    await telemetry_collector.stop_collection()
    return {"message": "Telemetry collection stopped"}


@app.get("/api/v1/telemetry/latest", response_model=TelemetrySnapshot)
async def get_latest_telemetry():
    """Get latest telemetry snapshot"""
    metrics = telemetry_collector.get_latest_metrics()
    if not metrics:
        raise HTTPException(status_code=404, detail="No telemetry data available")
    
    return TelemetrySnapshot(
        timestamp=metrics.timestamp,
        target_ip=metrics.target_ip,
        cpu_percent=metrics.cpu_percent,
        memory_percent=metrics.memory_percent,
        disk_percent=metrics.disk_percent,
        network_connections=metrics.network_connections,
        process_count=metrics.process_count,
        health_score=metrics.health_score,
        critical_services_status=metrics.critical_services_status
    )


@app.get("/api/v1/telemetry/history")
async def get_telemetry_history(count: int = Query(100, ge=1, le=1000)):
    """Get historical telemetry data"""
    history = telemetry_collector.get_metrics_history(count)
    return [
        {
            "timestamp": m.timestamp,
            "target_ip": m.target_ip,
            "cpu_percent": m.cpu_percent,
            "memory_percent": m.memory_percent,
            "disk_percent": m.disk_percent,
            "network_connections": m.network_connections,
            "process_count": m.process_count,
            "health_score": m.health_score
        }
        for m in history
    ]


@app.get("/api/v1/telemetry/health-timeline", response_model=List[HealthTimelinePoint])
async def get_health_timeline():
    """Get health score timeline for visualization"""
    timeline = telemetry_collector.get_health_timeline()
    return [HealthTimelinePoint(**point) for point in timeline]


@app.get("/api/v1/telemetry/events")
async def get_telemetry_events(
    severity: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000)
):
    """Get telemetry events and alerts"""
    events = telemetry_collector.get_events(severity, limit)
    return [
        {
            "timestamp": e.timestamp,
            "event_type": e.event_type,
            "source": e.source,
            "data": e.data,
            "severity": e.severity
        }
        for e in events
    ]


@app.get("/api/v1/telemetry/snapshot/{target_ip}")
async def collect_snapshot(target_ip: str):
    """Collect a single telemetry snapshot from target"""
    metrics = await telemetry_collector.collect_snapshot(target_ip)
    if not metrics:
        raise HTTPException(status_code=500, detail="Failed to collect telemetry")
    
    return {
        "timestamp": metrics.timestamp,
        "cpu_percent": metrics.cpu_percent,
        "memory_percent": metrics.memory_percent,
        "disk_percent": metrics.disk_percent,
        "network_connections": metrics.network_connections,
        "process_count": metrics.process_count,
        "health_score": metrics.health_score,
        "critical_services": metrics.critical_services_status,
        "top_processes": metrics.top_processes
    }


# ============================================================================
# C2 Integration Endpoints
# ============================================================================

@app.get("/api/v1/c2/status")
async def get_c2_status():
    """Get Sliver C2 server status"""
    connected = sliver_client.is_connected
    agents = await sliver_client.get_agents() if connected else []
    
    return {
        "connected": connected,
        "server_host": sliver_client.config.SLIVER_SERVER_HOST,
        "server_port": sliver_client.config.SLIVER_SERVER_PORT,
        "agent_count": len(agents),
        "active_sessions": len([a for a in agents if a.status.value == "active"]),
        "beacon_sessions": len([a for a in agents if a.status.value == "beacon"])
    }


@app.get("/api/v1/c2/agents", response_model=List[C2AgentResponse])
async def list_c2_agents():
    """List all C2 agents/sessions"""
    if not sliver_client.is_connected:
        raise HTTPException(status_code=503, detail="C2 server not connected")
    
    agents = await sliver_client.get_agents()
    return [
        C2AgentResponse(
            id=a.id,
            name=a.name,
            hostname=a.hostname,
            username=a.username,
            os=a.os or "Unknown",
            status=a.status.value,
            last_checkin=a.last_checkin
        )
        for a in agents
    ]


@app.get("/api/v1/c2/agents/{hostname}")
async def get_agent_by_hostname(hostname: str):
    """Get agent details by hostname"""
    if not sliver_client.is_connected:
        raise HTTPException(status_code=503, detail="C2 server not connected")
    
    agent = await sliver_client.get_agent_by_hostname(hostname)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {
        "id": agent.id,
        "name": agent.name,
        "hostname": agent.hostname,
        "username": agent.username,
        "status": agent.status.value,
        "last_checkin": agent.last_checkin
    }


@app.post("/api/v1/c2/agents/{session_id}/execute")
async def execute_via_c2(session_id: str, command: str):
    """Execute command via C2 agent"""
    if not sliver_client.is_connected:
        raise HTTPException(status_code=503, detail="C2 server not connected")
    
    result = await sliver_client.execute_command(session_id, command)
    
    return {
        "success": result.success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "execution_time_ms": result.execution_time_ms
    }


# ============================================================================
# Dashboard & Reporting Endpoints
# ============================================================================

@app.get("/api/v1/dashboard/summary")
async def get_dashboard_summary():
    """Get dashboard summary data"""
    latest = telemetry_collector.get_latest_metrics()
    safety = safety_engine.get_status()
    attacks = attack_executor.get_all_results()
    
    completed_attacks = [a for a in attacks if a.status == AttackStatus.COMPLETED]
    failed_attacks = [a for a in attacks if a.status == AttackStatus.FAILED]
    
    return {
        "safety_status": {
            "level": safety.level.value,
            "kill_switch": safety.kill_switch_triggered,
            "restrictions": safety.active_restrictions
        },
        "victim_health": {
            "score": latest.health_score if latest else 0,
            "cpu": latest.cpu_percent if latest else 0,
            "memory": latest.memory_percent if latest else 0,
            "status": "healthy" if (latest and latest.health_score > 70) else "degraded" if (latest and latest.health_score > 40) else "critical"
        },
        "attacks": {
            "total": len(attacks),
            "completed": len(completed_attacks),
            "failed": len(failed_attacks),
            "avg_health_impact": sum(a.health_impact for a in completed_attacks) / len(completed_attacks) if completed_attacks else 0
        },
        "c2_status": {
            "connected": sliver_client.is_connected,
            "agents": len(await sliver_client.get_agents()) if sliver_client.is_connected else 0
        }
    }


@app.get("/api/v1/reports/attack-timeline")
async def get_attack_timeline():
    """Get complete attack execution timeline with telemetry correlation"""
    attacks = attack_executor.get_all_results()
    telemetry = telemetry_collector.get_health_timeline()
    
    return {
        "attacks": [
            {
                "attack_id": a.attack_id,
                "technique_id": a.technique_id,
                "technique_name": a.technique_name,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "duration": a.duration_seconds,
                "health_impact": a.health_impact,
                "status": a.status.value
            }
            for a in sorted(attacks, key=lambda x: x.start_time or "")
        ],
        "health_timeline": telemetry
    }


@app.get("/api/v1/reports/attack-table")
async def get_attack_table():
    """Full attack results table with status, technique name, duration, and output"""
    attacks = attack_executor.get_all_results()
    return [
        {
            "attack_id": a.attack_id[:8],
            "technique_id": a.technique_id,
            "technique_name": a.technique_name,
            "tactic": getattr(attack_executor.get_technique(a.technique_id), 'tactic', 'Unknown'),
            "status": a.status.value,
            "target_ip": a.target_ip,
            "start_time": a.start_time,
            "duration_seconds": round(a.duration_seconds, 2),
            "health_impact": round(a.health_impact, 2),
            "command_output": (a.command_output or "")[:300],  # Truncate to 300 chars
            "error_message": a.error_message
        }
        for a in sorted(attacks, key=lambda x: x.start_time or "")
    ]


@app.get("/api/v1/reports/download/{playbook_name}")
async def download_report(playbook_name: str):
    """Generate and download a JSON report for a specific playbook run"""
    from fastapi.responses import JSONResponse
    
    attacks = attack_executor.get_all_results()
    safety = safety_engine.get_status()
    
    # Filter by relevant technique categories for each playbook
    playbook_tactic_map = {
        "discovery": ["Discovery"],
        "credential_access": ["Credential Access"],
        "privilege_escalation": ["Privilege Escalation"],
        "defense_evasion": ["Defense Evasion"],
        "lateral_movement": ["Lateral Movement"],
        "ransomware": ["Impact"]
    }
    
    tactic_filter = playbook_tactic_map.get(playbook_name, [])
    
    filtered = []
    for a in attacks:
        tech = attack_executor.get_technique(a.technique_id)
        tactic = getattr(tech, 'tactic', '') if tech else ''
        if not tactic_filter or tactic in tactic_filter:
            filtered.append({
                "attack_id": a.attack_id,
                "technique_id": a.technique_id,
                "technique_name": a.technique_name,
                "tactic": tactic,
                "status": a.status.value,
                "target_ip": a.target_ip,
                "start_time": a.start_time,
                "end_time": a.end_time,
                "duration_seconds": a.duration_seconds,
                "health_impact": a.health_impact,
                "command_output": a.command_output,
                "detection_indicators": a.detection_indicators,
                "error_message": a.error_message
            })
    
    report = {
        "report_type": playbook_name,
        "generated_at": datetime.utcnow().isoformat(),
        "platform_version": "2.0.0",
        "safety_level": safety.level.value,
        "total_techniques": len(filtered),
        "successful": len([a for a in filtered if a["status"] == "completed"]),
        "failed": len([a for a in filtered if a["status"] not in ["completed"]]),
        "techniques": filtered
    }
    
    response = JSONResponse(content=report)
    response.headers["Content-Disposition"] = f'attachment; filename="{playbook_name}_report.json"'
    return response


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }


# Removed API root endpoint to allow React SPA to be served at root


# ============================================================================
# Purple Team Evaluation Endpoints
# ============================================================================

from telemetry.event_parser import event_parser
import subprocess
import os

@app.get("/api/v1/evaluation/metrics")
async def get_evaluation_metrics():
    """
    Purple Team evaluation metrics — only what we can genuinely prove.
    Queries native Windows Event Logs on the victim VM via WinRM.
    Returns: TPR (True Positive Rate) and MTTD (Mean Time to Detect).
    FPR and FC are intentionally absent — they require a SIEM.
    """
    attacks = attack_executor.get_all_results()
    executed_technique_ids = [a.technique_id for a in attacks if a.status.value in ["completed", "blocked"]]
    metrics = event_parser.generate_evaluation_metrics(executed_technique_ids)
    return metrics


@app.get("/api/v1/evaluation/live-events")
async def get_live_events():
    """
    Fetches raw Windows Event Log records for all executed techniques.
    Returns the actual log entries (Event ID, timestamp, message snippet)
    directly from the victim VM via WinRM — this is the split-screen proof.
    """
    attacks = attack_executor.get_all_results()
    executed_technique_ids = list({
        a.technique_id for a in attacks
        if a.status.value in ["completed", "blocked"]
    })
    raw_events = event_parser.get_all_raw_events(executed_technique_ids)
    return {
        "total_records": len(raw_events),
        "queried_techniques": executed_technique_ids,
        "records": raw_events,
    }

# Playbook → technique IDs mapping (used to record trigger times for MTTD)
_PLAYBOOK_TECHNIQUES = {
    "discovery_phase":          ["T1087", "T1057", "T1016", "T1083"],
    "credential_access":        ["T1003.001", "T1555.003"],
    "privilege_escalation":     ["T1053.005"],
    "defense_evasion_adaptive": ["T1562.001", "T1070.001", "T1562.004"],
    "lateral_movement_sliver":  ["T1021.002", "T1570", "T1021.001"],
    "ransomware_simulation":    ["T1486", "T1496"],
}


@app.post("/api/v1/playbooks/execute/{playbook_name}")
async def execute_bash_playbook(playbook_name: str, background_tasks: BackgroundTasks):
    """
    Execute a bash playbook script on the platform server.
    Records the exact trigger time to /tmp/bas_attack_log.json so that
    event_parser.py can compute real MTTD = (log_timestamp - trigger_time).
    """
    valid_playbooks = list(_PLAYBOOK_TECHNIQUES.keys())
    if playbook_name not in valid_playbooks:
        raise HTTPException(status_code=404, detail="Playbook not found")

    script_path = f"/home/akila/Desktop/bas_platform/playbooks/{playbook_name}.sh"
    if not os.path.exists(script_path):
        raise HTTPException(status_code=404, detail="Script file not found")

    # ── Record attack trigger time for real MTTD calculation ──────────────
    trigger_time = datetime.utcnow().isoformat()
    attack_log_path = "/tmp/bas_attack_log.json"
    try:
        existing = []
        if os.path.exists(attack_log_path):
            with open(attack_log_path, "r") as f:
                data = json.load(f)
                existing = data if isinstance(data, list) else [data]
        existing.append({
            "playbook_name":  playbook_name,
            "technique_ids": _PLAYBOOK_TECHNIQUES.get(playbook_name, []),
            "trigger_time":  trigger_time,
        })
        with open(attack_log_path, "w") as f:
            json.dump(existing, f, indent=2)
        logger.info(f"Recorded attack trigger: {playbook_name} at {trigger_time}")
    except Exception as e:
        logger.warning(f"Could not write attack log: {e}")

    def run_script():
        try:
            logger.info(f"UI Triggered Playbook: {playbook_name}")
            with open("/tmp/bas_playbook_output.log", "w") as f:
                f.write(f"--- STARTING PLAYBOOK: {playbook_name} ---\n")
                f.write(f"--- TRIGGER TIME: {trigger_time} UTC ---\n\n")
            with open("/tmp/bas_playbook_output.log", "a") as f:
                subprocess.run(["bash", script_path], stdout=f, stderr=subprocess.STDOUT, text=True)
            with open("/tmp/bas_playbook_output.log", "a") as f:
                f.write(f"\n--- PLAYBOOK FINISHED ---\n")
        except Exception as e:
            logger.error(f"Playbook execution error: {e}")
            with open("/tmp/bas_playbook_output.log", "a") as f:
                f.write(f"\n[ERROR] Playbook execution failed: {e}\n")

    background_tasks.add_task(run_script)
    return {"message": f"Playbook {playbook_name} started successfully", "success": True}

@app.get("/api/v1/playbooks/logs")
async def get_playbook_logs():
    """Returns the latest buffered lines from the playbook execution log"""
    try:
        with open("/tmp/bas_playbook_output.log", "r") as f:
            lines = f.readlines()
        return {"logs": [line.rstrip() for line in lines[-200:]]}  # Return last 200 lines
    except FileNotFoundError:
        return {"logs": ["Waiting for playbook execution..."]}

# ============================================================================
# Serve React Frontend
# ============================================================================
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

DIST_DIR = "/home/akila/Desktop/bas_platform/web-ui/dist"

if os.path.isdir(DIST_DIR):
    # Mount the assets
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="assets")
    
    # Catch-all route to serve the SPA index.html
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Allow API requests to pass through
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("health"):
            raise HTTPException(status_code=404, detail="API route not found")
            
        file_path = os.path.join(DIST_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(DIST_DIR, "index.html"))

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
