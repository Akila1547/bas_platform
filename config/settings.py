"""
BAS Platform Configuration
==========================
Centralized configuration for the Adaptive Breach and Attack Simulation platform.
All safety limits and operational parameters are defined here.
"""

from pydantic_settings import BaseSettings
from typing import List, Dict
import os


class SafetyConfig:
    """Safety controls and operational limits"""
    # Maximum execution time for any single attack (seconds)
    MAX_ATTACK_DURATION = 300
    
    # Allowed target IPs (whitelist for safety)
    ALLOWED_TARGETS = []  # Populate with your lab VM IPs
    
    # Blocked targets (never attack these)
    BLOCKED_TARGETS = ["192.168.1.1", "10.0.0.1"]  # Gateway, DNS, etc.
    
    # Enable/disable actual execution (False = simulation mode only)
    LIVE_EXECUTION_ENABLED = True
    
    # Require explicit confirmation for destructive operations
    REQUIRE_CONFIRMATION = True
    
    # Auto-kill switch: stop all operations if victim health drops below threshold
    HEALTH_THRESHOLD = 30  # Percentage
    
    # Log all operations for audit
    AUDIT_LOG_ENABLED = True


class C2Config:
    """Sliver C2 Configuration"""
    SLIVER_SERVER_HOST = os.getenv("SLIVER_SERVER_HOST", "127.0.0.1")
    SLIVER_SERVER_PORT = int(os.getenv("SLIVER_SERVER_PORT", "31337"))
    SLIVER_CONFIG_PATH = os.getenv("SLIVER_CONFIG_PATH", "~/.sliver-client/configs")
    
    # Session timeout
    SESSION_TIMEOUT = 60
    
    # Command execution timeout
    COMMAND_TIMEOUT = 30


class TelemetryConfig:
    """Telemetry collection settings"""
    # Collection interval (seconds)
    COLLECTION_INTERVAL = 5
    
    # Metrics to collect
    METRICS = [
        "cpu_percent",
        "memory_percent",
        "disk_usage",
        "network_connections",
        "process_count",
        "running_processes",
        "system_uptime",
        "critical_services"
    ]
    
    # Health score calculation weights
    HEALTH_WEIGHTS = {
        "cpu": 0.25,
        "memory": 0.25,
        "disk": 0.15,
        "services": 0.20,
        "responsiveness": 0.15
    }


class AttackConfig:
    """Attack execution configuration"""
    # Attack modules directory
    MODULES_PATH = "attacks/modules"
    
    # Pre-attack checks
    VERIFY_TARGET_REACHABLE = True
    VERIFY_SNAPSHOT_EXISTS = True
    
    # Post-attack cleanup
    AUTO_CLEANUP = True
    CLEANUP_TIMEOUT = 60


class Settings(BaseSettings):
    """Main application settings"""
    APP_NAME: str = "Adaptive BAS Platform"
    DEBUG: bool = False
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "sqlite:///./bas_platform.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bas_platform.log"
    
    # === ADD THESE MISSING FIELDS ===
    
    # Victim/Windows VM Settings (from .env)
    VICTIM_IP: str = ""
    VICTIM_USERNAME: str = "Administrator"
    VICTIM_PASSWORD: str = ""
    
    # Sliver C2 Settings (from .env)
    SLIVER_SERVER_HOST: str = "127.0.0.1"
    SLIVER_SERVER_PORT: int = 31337
    SLIVER_CONFIG_PATH: str = "/root/.sliver-client/configs"
    
    # Safety Settings (from .env)
    LIVE_EXECUTION_ENABLED: bool = False
    ALLOWED_TARGETS: str = ""  # Comma-separated IPs
    BLOCKED_TARGETS: str = "192.168.1.1,10.0.0.1"
    
    # Telemetry Settings (from .env)
    HEALTH_THRESHOLD: int = 30
    TELEMETRY_INTERVAL: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra fields from .env


# Global settings instance
settings = Settings()
