"""
Sliver C2 Integration
=====================
Integration with Sliver C2 framework for agent management and command execution.
Provides safe wrapper around Sliver operations for BAS platform.
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import os
from sliver import SliverClientConfig, SliverClient as PySliverClient

from config.settings import C2Config


logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BEACON = "beacon"
    UNKNOWN = "unknown"


@dataclass
class SliverAgent:
    """Represents a Sliver C2 agent"""
    id: str
    name: str
    hostname: str
    username: str
    uid: str
    gid: str
    os: str
    arch: str
    transport: str
    remote_address: str
    status: AgentStatus
    last_checkin: Optional[str] = None
    version: str = ""
    
    @property
    def is_active(self) -> bool:
        return self.status == AgentStatus.ACTIVE


@dataclass
class CommandResult:
    """Result of command execution via Sliver"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: int


class SliverClient:
    """
    Client for interacting with Sliver C2 server.
    Uses sliver-client CLI for operations.
    """
    
    def __init__(self):
        self.config = C2Config()
        self._connected = False
        self._current_session: Optional[str] = None
        self._sliver_client: Optional[PySliverClient] = None
        
    async def connect(self) -> bool:
        """Connect to Sliver server and verify connectivity"""
        try:
            cfg_path = os.path.expanduser("~/.sliver-client/configs/bas_operator_localhost.cfg")
            config = SliverClientConfig.parse_config_file(cfg_path)
            self._sliver_client = PySliverClient(config)
            await self._sliver_client.connect()
            self._connected = True
            logger.info("Connected to Sliver C2 server via gRPC")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Sliver: {e}")
            return False
    
    async def get_agents(self) -> List[SliverAgent]:
        """Get list of all active agents/sessions"""
        agents = []
        if not self._connected or not self._sliver_client:
            return agents
        
        try:
            # Get sessions (interactive)
            sessions = await self._sliver_client.sessions()
            for s in sessions:
                agents.append(SliverAgent(
                    id=s.ID, name=s.Name, hostname=s.Hostname,
                    username=s.Username, uid=str(s.UID), gid=str(s.GID),
                    os=s.OS, arch=s.Arch, transport=s.Transport,
                    remote_address=s.RemoteAddress, status=AgentStatus.ACTIVE,
                    last_checkin=str(s.LastCheckin) if hasattr(s, 'LastCheckin') else None,
                    version=s.Version
                ))
            
            # Get beacons
            beacons = await self._sliver_client.beacons()
            for b in beacons:
                agents.append(SliverAgent(
                    id=b.ID, name=b.Name, hostname=b.Hostname,
                    username=b.Username, uid=str(b.UID), gid=str(b.GID),
                    os=b.OS, arch=b.Arch, transport=b.Transport,
                    remote_address=b.RemoteAddress, status=AgentStatus.BEACON,
                    last_checkin=str(b.LastCheckin) if hasattr(b, 'LastCheckin') else None,
                    version=b.Version
                ))
                
        except Exception as e:
            logger.error(f"Failed to get agents via gRPC: {e}")
        
        return agents
    
    async def get_agent_by_hostname(self, hostname: str) -> Optional[SliverAgent]:
        """Find agent by hostname"""
        agents = await self.get_agents()
        for agent in agents:
            if agent.hostname.lower() == hostname.lower():
                return agent
        return None
    
    async def execute_command(
        self, 
        session_id: str, 
        command: str,
        timeout: int = 30
    ) -> CommandResult:
        """
        Execute command via Sliver session.
        Uses 'execute' command for non-interactive execution.
        """
        try:
            # Use sliver execute command
            # Format: execute -s <session> -c "<command>"
            sliver_cmd = f'execute -s {session_id} -c "{command}"'
            
            result = await self._run_sliver_command(sliver_cmd, timeout)
            
            return CommandResult(
                success=result["success"],
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                exit_code=result.get("exit_code", -1),
                execution_time_ms=result.get("time_ms", 0)
            )
            
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=0
            )
    
    async def execute_shellcode(
        self,
        session_id: str,
        shellcode_path: str
    ) -> CommandResult:
        """Execute shellcode (for advanced scenarios)"""
        # NOTE: This is for advanced research only
        # Requires explicit safety approval
        logger.warning(f"Shellcode execution requested: {shellcode_path}")
        
        try:
            sliver_cmd = f'sideload -s {session_id} {shellcode_path}'
            result = await self._run_sliver_command(sliver_cmd, timeout=60)
            
            return CommandResult(
                success=result["success"],
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                exit_code=0 if result["success"] else -1,
                execution_time_ms=result.get("time_ms", 0)
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time_ms=0
            )
    
    async def get_system_info(self, session_id: str) -> Dict[str, Any]:
        """Get system information from agent"""
        info = {}
        
        try:
            # Get basic info
            info_cmd = f'info -s {session_id}'
            result = await self._run_sliver_command(info_cmd)
            if result["success"]:
                info = self._parse_info(result["output"])
            
            # Get network info
            net_cmd = f'netstat -s {session_id}'
            net_result = await self._run_sliver_command(net_cmd)
            if net_result["success"]:
                info["network"] = net_result["output"]
                
        except Exception as e:
            logger.error(f"Failed to get system info: {e}")
        
        return info
    
    async def upload_file(
        self,
        session_id: str,
        local_path: str,
        remote_path: str
    ) -> bool:
        """Upload file to agent"""
        try:
            cmd = f'upload -s {session_id} -l "{local_path}" -r "{remote_path}"'
            result = await self._run_sliver_command(cmd)
            return result["success"]
        except Exception as e:
            logger.error(f"File upload failed: {e}")
            return False
    
    async def download_file(
        self,
        session_id: str,
        remote_path: str,
        local_path: str
    ) -> bool:
        """Download file from agent"""
        try:
            cmd = f'download -s {session_id} -r "{remote_path}" -l "{local_path}"'
            result = await self._run_sliver_command(cmd)
            return result["success"]
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return False
    
    async def kill_agent(self, session_id: str) -> bool:
        """Kill/terminate an agent session"""
        try:
            cmd = f'kill -s {session_id} -f'
            result = await self._run_sliver_command(cmd)
            return result["success"]
        except Exception as e:
            logger.error(f"Failed to kill agent: {e}")
            return False
    
    async def _run_sliver_command(
        self, 
        command: str, 
        timeout: int = 30
    ) -> Dict:
        """Execute a sliver-client command"""
        try:
            # Build full command
            full_cmd = f"sliver-client {command}"
            
            process = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "success": process.returncode == 0,
                "output": stdout.decode().strip(),
                "error": stderr.decode().strip(),
                "exit_code": process.returncode
            }
            
        except asyncio.TimeoutError:
            return {"success": False, "error": "Command timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_sessions(self, output: str) -> List[SliverAgent]:
        """Parse sessions command output"""
        agents = []
        # Sliver sessions output parsing
        # Format varies by version, this is a simplified parser
        lines = output.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('ID') and not line.startswith('='):
                parts = line.split()
                if len(parts) >= 5:
                    agents.append(SliverAgent(
                        id=parts[0],
                        name=parts[1] if len(parts) > 1 else "",
                        hostname=parts[2] if len(parts) > 2 else "",
                        username=parts[3] if len(parts) > 3 else "",
                        uid="",
                        gid="",
                        os="",
                        arch="",
                        transport="",
                        remote_address="",
                        status=AgentStatus.ACTIVE
                    ))
        return agents
    
    def _parse_beacons(self, output: str) -> List[SliverAgent]:
        """Parse beacons command output"""
        agents = []
        lines = output.split('\n')
        for line in lines:
            if line.strip() and not line.startswith('ID'):
                parts = line.split()
                if len(parts) >= 5:
                    agents.append(SliverAgent(
                        id=parts[0],
                        name=parts[1] if len(parts) > 1 else "",
                        hostname=parts[2] if len(parts) > 2 else "",
                        username="",
                        uid="",
                        gid="",
                        os="",
                        arch="",
                        transport="beacon",
                        remote_address="",
                        status=AgentStatus.BEACON,
                        last_checkin=parts[-1] if len(parts) > 4 else None
                    ))
        return agents
    
    def _parse_info(self, output: str) -> Dict:
        """Parse info command output"""
        info = {}
        lines = output.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip().lower()] = value.strip()
        return info
    
    @property
    def is_connected(self) -> bool:
        return self._connected


# Global Sliver client instance
sliver_client = SliverClient()
