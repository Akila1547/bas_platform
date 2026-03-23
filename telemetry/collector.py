"""
Telemetry Collector
===================
Collects system health and behavioral telemetry from victim Windows VM.
Uses WMI, PowerShell remoting, or C2 channel for data collection.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import subprocess
import re

from config.settings import TelemetryConfig, C2Config
from core.safety_engine import safety_engine


logger = logging.getLogger(__name__)


class MetricType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"
    SERVICE = "service"
    SYSTEM = "system"


@dataclass
class SystemMetrics:
    """Complete system metrics snapshot"""
    timestamp: str
    target_ip: str
    
    # CPU
    cpu_percent: float
    cpu_count: int
    cpu_per_core: List[float]
    
    # Memory
    memory_percent: float
    memory_available_mb: float
    memory_total_mb: float
    
    # Disk
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float
    
    # Network
    network_connections: int
    network_bytes_sent: int
    network_bytes_recv: int
    
    # Processes
    process_count: int
    top_processes: List[Dict[str, Any]]
    new_processes: List[str]
    
    # Services
    critical_services_status: Dict[str, str]
    services_running: int
    services_stopped: int
    
    # System
    system_uptime_seconds: float
    boot_time: str
    
    # Derived
    health_score: float
    responsiveness_ms: Optional[float] = None


@dataclass
class TelemetryEvent:
    """Individual telemetry event"""
    timestamp: str
    event_type: str
    source: str
    data: Dict[str, Any]
    severity: str = "info"


class TelemetryCollector:
    """
    Collects telemetry from Windows victim via multiple channels.
    Supports: Sliver C2, PowerShell remoting, WMI.
    """
    
    def __init__(self):
        self.config = TelemetryConfig()
        self.c2_config = C2Config()
        self._collection_task: Optional[asyncio.Task] = None
        self._metrics_history: List[SystemMetrics] = []
        self._events: List[TelemetryEvent] = []
        self._baseline: Optional[SystemMetrics] = None
        self._is_collecting = False
        
    async def start_continuous_collection(self, target_ip: str, interval: Optional[int] = None):
        """Start background telemetry collection"""
        if self._is_collecting:
            logger.warning("Telemetry collection already running")
            return
            
        self._is_collecting = True
        interval = interval or self.config.COLLECTION_INTERVAL
        
        logger.info(f"Starting telemetry collection for {target_ip} (interval: {interval}s)")
        
        self._collection_task = asyncio.create_task(
            self._collection_loop(target_ip, interval)
        )
    
    async def stop_collection(self):
        """Stop background collection"""
        self._is_collecting = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("Telemetry collection stopped")
    
    async def _collection_loop(self, target_ip: str, interval: int):
        """Main collection loop"""
        while self._is_collecting:
            try:
                metrics = await self.collect_snapshot(target_ip)
                if metrics:
                    self._metrics_history.append(metrics)
                    
                    # Keep only last 1000 snapshots
                    if len(self._metrics_history) > 1000:
                        self._metrics_history = self._metrics_history[-1000:]
                    
                    # Check health and trigger kill switch if needed
                    if not safety_engine.check_health_threshold(metrics.health_score):
                        logger.error(f"Health check failed for {target_ip}")
                    
                    # Detect anomalies
                    await self._detect_anomalies(metrics)
                    
            except Exception as e:
                logger.error(f"Telemetry collection error: {e}")
                self._add_event("collection_error", {"error": str(e)}, "error")
            
            await asyncio.sleep(interval)
    
    async def collect_snapshot(self, target_ip: str) -> Optional[SystemMetrics]:
        """
        Collect a single metrics snapshot from target.
        Uses PowerShell remoting as primary method.
        """
        try:
            # Build PowerShell command for comprehensive metrics
            ps_command = self._build_metrics_command()
            
            # Execute via PowerShell remoting
            result = await self._execute_remoting(target_ip, ps_command)
            
            if result["success"]:
                data = json.loads(result["output"])
                metrics = self._parse_metrics(data, target_ip)
                
                # Calculate health score
                metrics.health_score = self._calculate_health_score(metrics)
                
                return metrics
            else:
                logger.error(f"Failed to collect metrics: {result.get('error')}")
                return None
                
        except Exception as e:
            logger.error(f"Snapshot collection failed: {e}")
            return None
    
    def _build_metrics_command(self) -> str:
        """Build PowerShell command to collect all metrics"""
        return '''
        $metrics = @{}
        
        # CPU
        $cpu = Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 1
        $metrics['cpu_percent'] = [math]::Round($cpu.CounterSamples.CookedValue, 2)
        $metrics['cpu_count'] = (Get-WmiObject -Class Win32_Processor).NumberOfLogicalProcessors
        
        # Memory
        $mem = Get-WmiObject -Class Win32_OperatingSystem
        $metrics['memory_total_mb'] = [math]::Round($mem.TotalVisibleMemorySize / 1024, 2)
        $metrics['memory_available_mb'] = [math]::Round($mem.FreePhysicalMemory / 1024, 2)
        $metrics['memory_percent'] = [math]::Round((($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory) / $mem.TotalVisibleMemorySize) * 100, 2)
        
        # Disk
        $disk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='C:'"
        $metrics['disk_total_gb'] = [math]::Round($disk.Size / 1GB, 2)
        $metrics['disk_free_gb'] = [math]::Round($disk.FreeSpace / 1GB, 2)
        $metrics['disk_percent'] = [math]::Round((($disk.Size - $disk.FreeSpace) / $disk.Size) * 100, 2)
        
        # Network
        $netStats = Get-NetTCPConnection | Measure-Object
        $metrics['network_connections'] = $netStats.Count
        $netAdapter = Get-NetAdapterStatistics | Select-Object -First 1
        $metrics['network_bytes_sent'] = $netAdapter.SentBytes
        $metrics['network_bytes_recv'] = $netAdapter.ReceivedBytes
        
        # Processes
        $processes = Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 | ForEach-Object {
            @{
                name = $_.ProcessName
                pid = $_.Id
                cpu = [math]::Round($_.CPU, 2)
                memory_mb = [math]::Round($_.WorkingSet64 / 1MB, 2)
            }
        }
        $metrics['process_count'] = (Get-Process).Count
        $metrics['top_processes'] = $processes
        
        # Services
        $services = Get-Service
        $metrics['services_running'] = ($services | Where-Object {$_.Status -eq 'Running'}).Count
        $metrics['services_stopped'] = ($services | Where-Object {$_.Status -eq 'Stopped'}).Count
        
        # Critical services
        $criticalServices = @('RpcSs', 'Dhcp', 'Dnscache', 'LanmanServer', 'NTDS', 'Netlogon', 'TermService')
        $criticalStatus = @{}
        foreach ($svc in $criticalServices) {
            $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
            if ($s) {
                $criticalStatus[$svc] = $s.Status.ToString()
            }
        }
        $metrics['critical_services_status'] = $criticalStatus
        
        # System
        $os = Get-WmiObject -Class Win32_OperatingSystem
        $metrics['system_uptime_seconds'] = [math]::Round(((Get-Date) - $os.ConvertToDateTime($os.LastBootUpTime)).TotalSeconds, 2)
        $metrics['boot_time'] = $os.ConvertToDateTime($os.LastBootUpTime).ToString("o")
        
        $metrics | ConvertTo-Json -Depth 10
        '''
    
    async def _execute_remoting(self, target_ip: str, command: str) -> Dict:
        """Execute PowerShell command on remote Windows host"""
        try:
            import winrm
            
            # Create WinRM session
            session = winrm.Session(
                f'http://{target_ip}:5985/wsman',
                auth=(self._get_victim_username(), self._get_victim_password()),
                transport='ntlm'
            )
            
            # Execute command in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: session.run_ps(command)
            )
            
            if result.status_code == 0:
                return {"success": True, "output": result.std_out.decode().strip()}
            else:
                return {"success": False, "error": result.std_err.decode().strip()}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_metrics(self, data: Dict, target_ip: str) -> SystemMetrics:
        """Parse raw metrics data into SystemMetrics"""
        return SystemMetrics(
            timestamp=datetime.utcnow().isoformat(),
            target_ip=target_ip,
            cpu_percent=data.get("cpu_percent", 0),
            cpu_count=data.get("cpu_count", 0),
            cpu_per_core=data.get("cpu_per_core", []),
            memory_percent=data.get("memory_percent", 0),
            memory_available_mb=data.get("memory_available_mb", 0),
            memory_total_mb=data.get("memory_total_mb", 0),
            disk_percent=data.get("disk_percent", 0),
            disk_free_gb=data.get("disk_free_gb", 0),
            disk_total_gb=data.get("disk_total_gb", 0),
            network_connections=data.get("network_connections", 0),
            network_bytes_sent=data.get("network_bytes_sent", 0),
            network_bytes_recv=data.get("network_bytes_recv", 0),
            process_count=data.get("process_count", 0),
            top_processes=data.get("top_processes", []),
            new_processes=[],
            critical_services_status=data.get("critical_services_status", {}),
            services_running=data.get("services_running", 0),
            services_stopped=data.get("services_stopped", 0),
            system_uptime_seconds=data.get("system_uptime_seconds", 0),
            boot_time=data.get("boot_time", ""),
            health_score=0.0,
            responsiveness_ms=None
        )
    
    def _calculate_health_score(self, metrics: SystemMetrics) -> float:
        """Calculate overall health score (0-100)"""
        weights = self.config.HEALTH_WEIGHTS
        
        # CPU health (lower is better)
        cpu_health = max(0, 100 - metrics.cpu_percent)
        
        # Memory health (lower is better)
        mem_health = max(0, 100 - metrics.memory_percent)
        
        # Disk health (lower is better)
        disk_health = max(0, 100 - metrics.disk_percent)
        
        # Services health (all critical services should be running)
        critical = metrics.critical_services_status
        running_critical = sum(1 for s in critical.values() if s == "Running")
        total_critical = len(critical) if critical else 1
        service_health = (running_critical / total_critical) * 100
        
        # Responsiveness (placeholder - would measure ping/response time)
        responsiveness = 100  # Assume responsive
        
        # Weighted average
        health = (
            cpu_health * weights["cpu"] +
            mem_health * weights["memory"] +
            disk_health * weights["disk"] +
            service_health * weights["services"] +
            responsiveness * weights["responsiveness"]
        )
        
        return round(health, 2)
    
    async def _detect_anomalies(self, current: SystemMetrics):
        """Detect anomalies by comparing with baseline"""
        if not self._baseline:
            self._baseline = current
            return
        
        # Check for significant changes
        if current.process_count > self._baseline.process_count * 1.5:
            self._add_event(
                "process_spike",
                {
                    "current": current.process_count,
                    "baseline": self._baseline.process_count
                },
                "warning"
            )
        
        if current.cpu_percent > 90:
            self._add_event(
                "high_cpu",
                {"cpu_percent": current.cpu_percent},
                "warning"
            )
        
        if current.memory_percent > 90:
            self._add_event(
                "high_memory",
                {"memory_percent": current.memory_percent},
                "warning"
            )
        
        # Check for stopped critical services
        for svc, status in current.critical_services_status.items():
            if status != "Running":
                self._add_event(
                    "service_down",
                    {"service": svc, "status": status},
                    "critical"
                )
    
    def _add_event(self, event_type: str, data: Dict, severity: str = "info"):
        """Add telemetry event"""
        event = TelemetryEvent(
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            source="telemetry_collector",
            data=data,
            severity=severity
        )
        self._events.append(event)
        logger.info(f"Telemetry event: {event_type} - {severity}")
    
    def get_latest_metrics(self) -> Optional[SystemMetrics]:
        """Get most recent metrics snapshot"""
        return self._metrics_history[-1] if self._metrics_history else None
    
    def get_metrics_history(self, count: int = 100) -> List[SystemMetrics]:
        """Get historical metrics"""
        return self._metrics_history[-count:]
    
    def get_events(self, severity: Optional[str] = None, limit: int = 100) -> List[TelemetryEvent]:
        """Get telemetry events"""
        events = self._events[-limit:]
        if severity:
            events = [e for e in events if e.severity == severity]
        return events
    
    def get_health_timeline(self) -> List[Dict]:
        """Get health score over time"""
        return [
            {
                "timestamp": m.timestamp,
                "health_score": m.health_score,
                "cpu": m.cpu_percent,
                "memory": m.memory_percent
            }
            for m in self._metrics_history
        ]
    
    def _get_victim_username(self) -> str:
        """Get victim VM username (from config/env)"""
        import os
        return os.getenv("VICTIM_USERNAME", "Administrator")
    
    def _get_victim_password(self) -> str:
        """Get victim VM password (from config/env)"""
        import os
        return os.getenv("VICTIM_PASSWORD", "Password123!")


# Global collector instance
telemetry_collector = TelemetryCollector()
