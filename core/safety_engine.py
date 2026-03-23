"""
Safety Engine
=============
Critical safety controls for the BAS platform.
Implements kill switches, target validation, and execution guards.
"""

import ipaddress
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio

from config.settings import SafetyConfig, TelemetryConfig


logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    SIMULATION = "simulation"      # No real execution
    OBSERVATION = "observation"    # Read-only telemetry
    CONTROLLED = "controlled"      # Safe, non-destructive attacks
    FULL = "full"                  # Full attack execution (requires explicit enable)


@dataclass
class SafetyStatus:
    """Current safety system status"""
    level: SafetyLevel
    live_execution_enabled: bool
    health_monitor_active: bool
    kill_switch_triggered: bool
    last_check: datetime
    active_restrictions: List[str]


class SafetyEngine:
    """
    Central safety controller for the BAS platform.
    All attack execution MUST pass through this engine.
    """
    
    def __init__(self):
        self.config = SafetyConfig()
        self.telemetry_config = TelemetryConfig()
        self._kill_switch = False
        self._current_level = SafetyLevel.SIMULATION
        self._execution_lock = asyncio.Lock()
        self._audit_log: List[Dict] = []
        
    @property
    def kill_switch_active(self) -> bool:
        """Check if emergency kill switch is active"""
        return self._kill_switch
    
    def trigger_kill_switch(self, reason: str) -> None:
        """Emergency stop all operations"""
        self._kill_switch = True
        self._current_level = SafetyLevel.SIMULATION
        logger.critical(f"KILL SWITCH TRIGGERED: {reason}")
        self._log_audit("KILL_SWITCH", {"reason": reason})
        
    def reset_kill_switch(self) -> None:
        """Reset kill switch (requires manual confirmation)"""
        self._kill_switch = False
        logger.info("Kill switch reset")
        self._log_audit("KILL_SWITCH_RESET", {})
    
    def set_safety_level(self, level: SafetyLevel) -> bool:
        """Set operational safety level"""
        if level == SafetyLevel.FULL and not self.config.LIVE_EXECUTION_ENABLED:
            logger.error("Cannot set FULL mode: LIVE_EXECUTION_ENABLED is False in config")
            return False
            
        old_level = self._current_level
        self._current_level = level
        logger.info(f"Safety level changed: {old_level.value} -> {level.value}")
        self._log_audit("SAFETY_LEVEL_CHANGE", {
            "old": old_level.value,
            "new": level.value
        })
        return True
    
    def validate_target(self, target_ip: str) -> tuple[bool, str]:
        """
        Validate target IP against safety rules.
        Returns (is_valid, reason)
        """
        try:
            ip = ipaddress.ip_address(target_ip)
            
            # Check if private IP (lab environment only)
            if not ip.is_private:
                return False, f"Target {target_ip} is not a private IP - blocked for safety"
            
            # Check blocked targets
            if target_ip in self.config.BLOCKED_TARGETS:
                return False, f"Target {target_ip} is in blocked list"
            
            # Check allowed targets whitelist (if configured)
            if self.config.ALLOWED_TARGETS and target_ip not in self.config.ALLOWED_TARGETS:
                return False, f"Target {target_ip} not in allowed targets whitelist"
                
            return True, "Target validated"
            
        except ValueError:
            return False, f"Invalid IP address: {target_ip}"
    
    def check_health_threshold(self, health_score: float) -> bool:
        """Check if victim health is above acceptable threshold"""
        if health_score < self.config.HEALTH_THRESHOLD:
            self.trigger_kill_switch(
                f"Victim health {health_score}% below threshold {self.config.HEALTH_THRESHOLD}%"
            )
            return False
        return True
    
    async def request_execution_permission(
        self, 
        attack_name: str, 
        target: str,
        is_destructive: bool = False
    ) -> tuple[bool, str]:
        """
        Request permission to execute an attack.
        All attacks must call this before execution.
        """
        async with self._execution_lock:
            # Check kill switch
            if self._kill_switch:
                return False, "Kill switch is active - all execution blocked"
            
            # Check safety level
            if self._current_level == SafetyLevel.SIMULATION:
                return False, "System in SIMULATION mode - no live execution"
            
            if self._current_level == SafetyLevel.OBSERVATION:
                return False, "System in OBSERVATION mode - telemetry only"
            
            # Validate target
            valid, reason = self.validate_target(target)
            if not valid:
                return False, reason
            
            # Check destructive operations
            if is_destructive and self.config.REQUIRE_CONFIRMATION:
                # In real implementation, this would trigger UI confirmation
                logger.warning(f"Destructive attack '{attack_name}' requires manual confirmation")
                # For now, block destructive ops in controlled mode
                if self._current_level == SafetyLevel.CONTROLLED:
                    return False, "Destructive attacks blocked in CONTROLLED mode"
            
            # Log approval
            self._log_audit("EXECUTION_APPROVED", {
                "attack": attack_name,
                "target": target,
                "destructive": is_destructive
            })
            
            return True, "Execution approved"
    
    def _log_audit(self, action: str, details: Dict) -> None:
        """Log audit event"""
        if self.config.AUDIT_LOG_ENABLED:
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "details": details
            }
            self._audit_log.append(entry)
            logger.info(f"AUDIT: {action} - {details}")
    
    def get_status(self) -> SafetyStatus:
        """Get current safety system status"""
        restrictions = []
        if self._kill_switch:
            restrictions.append("KILL_SWITCH_ACTIVE")
        if not self.config.LIVE_EXECUTION_ENABLED:
            restrictions.append("LIVE_EXEC_DISABLED")
        if self._current_level != SafetyLevel.FULL:
            restrictions.append(f"LEVEL_{self._current_level.value}")
            
        return SafetyStatus(
            level=self._current_level,
            live_execution_enabled=self.config.LIVE_EXECUTION_ENABLED,
            health_monitor_active=True,
            kill_switch_triggered=self._kill_switch,
            last_check=datetime.utcnow(),
            active_restrictions=restrictions
        )
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get recent audit log entries"""
        return self._audit_log[-limit:]


# Global safety engine instance
safety_engine = SafetyEngine()
