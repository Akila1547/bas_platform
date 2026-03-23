#!/usr/bin/env python3
"""
BAS Platform Setup Test Script
==============================
Tests all components to verify proper setup.
"""

import asyncio
import sys
import os
import subprocess
import json
from typing import Dict, List, Tuple

# Add project to path
sys.path.insert(0, '/mnt/okcomputer/output/bas_platform')


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_header(text: str):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def check_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """Check if a command exists and works"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)


def test_python_environment():
    """Test Python and dependencies"""
    print_header("Testing Python Environment")
    
    # Check Python version
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    else:
        print_warning(f"Python {version.major}.{version.minor} (3.11+ recommended)")
    
    # Check virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print_success("Running in virtual environment")
    else:
        print_warning("Not in virtual environment (recommended)")
    
    # Check key dependencies
    deps = [
        ('fastapi', 'FastAPI'),
        ('uvicorn', 'Uvicorn'),
        ('pydantic', 'Pydantic'),
    ]
    
    for module, name in deps:
        try:
            __import__(module)
            print_success(f"{name} installed")
        except ImportError:
            print_error(f"{name} not installed (run: pip install -r requirements.txt)")


def test_system_commands():
    """Test system-level dependencies"""
    print_header("Testing System Commands")
    
    commands = [
        (['python3', '--version'], 'Python 3'),
        (['pwsh', '--version'], 'PowerShell'),
        (['sliver-client', 'version'], 'Sliver Client'),
    ]
    
    for cmd, name in commands:
        success, output = check_command(cmd, name)
        if success:
            print_success(f"{name}: {output[:50]}")
        else:
            print_error(f"{name}: Not found or error")
            if 'sliver' in name.lower():
                print_warning("  Install Sliver: curl https://sliver.sh/install | sudo bash")
            elif 'powershell' in name.lower():
                print_warning("  Install PowerShell: See WINDOWS_SETUP.md")


def test_configuration():
    """Test configuration files"""
    print_header("Testing Configuration")
    
    # Check .env file
    if os.path.exists('.env'):
        print_success(".env file exists")
        
        # Read and check key values
        with open('.env', 'r') as f:
            content = f.read()
            
        if 'VICTIM_PASSWORD=YourSecurePassword' in content:
            print_warning("VICTIM_PASSWORD is still default - please change it")
        elif 'VICTIM_PASSWORD=' in content:
            print_success("VICTIM_PASSWORD is configured")
            
        if 'LIVE_EXECUTION_ENABLED=true' in content:
            print_warning("LIVE_EXECUTION_ENABLED is TRUE - attacks will execute!")
        else:
            print_success("LIVE_EXECUTION_ENABLED is false (safe mode)")
    else:
        print_error(".env file not found (copy from .env.example)")
    
    # Check directory structure
    dirs = ['logs', 'data', 'attacks/modules']
    for d in dirs:
        if os.path.exists(d):
            print_success(f"Directory exists: {d}")
        else:
            print_error(f"Directory missing: {d} (mkdir -p {d})")


def test_api_imports():
    """Test that API modules can be imported"""
    print_header("Testing API Module Imports")
    
    modules = [
        ('config.settings', 'Settings'),
        ('core.safety_engine', 'SafetyEngine'),
        ('core.attack_executor', 'AttackExecutor'),
        ('telemetry.collector', 'TelemetryCollector'),
        ('c2_integration.sliver_client', 'SliverClient'),
    ]
    
    for module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            print_success(f"Imported {module_path}.{class_name}")
        except Exception as e:
            print_error(f"Failed to import {module_path}: {str(e)[:50]}")


def test_attack_techniques():
    """Test attack technique registry"""
    print_header("Testing Attack Techniques")
    
    try:
        from core.attack_executor import attack_executor
        
        techniques = attack_executor.list_techniques()
        print_success(f"Loaded {len(techniques)} attack techniques")
        
        # Show technique summary
        tactics = {}
        for t in techniques:
            tactics[t.tactic] = tactics.get(t.tactic, 0) + 1
        
        print("\n  Techniques by tactic:")
        for tactic, count in sorted(tactics.items()):
            print(f"    - {tactic}: {count}")
        
        # Check specific techniques
        key_techniques = ['T1087', 'T1057', 'T1016', 'T1053.005']
        for tid in key_techniques:
            t = attack_executor.get_technique(tid)
            if t:
                print_success(f"Technique {tid}: {t.name}")
            else:
                print_error(f"Technique {tid} not found")
                
    except Exception as e:
        print_error(f"Failed to load techniques: {e}")


def test_safety_engine():
    """Test safety engine"""
    print_header("Testing Safety Engine")
    
    try:
        from core.safety_engine import safety_engine, SafetyLevel
        
        # Check status
        status = safety_engine.get_status()
        print_success(f"Safety level: {status.level.value}")
        print_success(f"Kill switch: {'ACTIVE' if status.kill_switch_triggered else 'inactive'}")
        print_success(f"Live execution: {'enabled' if status.live_execution_enabled else 'disabled'}")
        
        # Test target validation
        test_cases = [
            ('192.168.56.101', True, 'Private IP'),
            ('10.0.0.5', True, 'Private IP'),
            ('8.8.8.8', False, 'Public IP (should be blocked)'),
            ('192.168.1.1', False, 'Gateway (should be blocked)'),
        ]
        
        print("\n  Target validation tests:")
        for ip, should_pass, description in test_cases:
            valid, reason = safety_engine.validate_target(ip)
            if valid == should_pass:
                print_success(f"    {ip}: {description}")
            else:
                print_error(f"    {ip}: Unexpected result - {reason}")
                
    except Exception as e:
        print_error(f"Safety engine test failed: {e}")


async def test_telemetry_collector():
    """Test telemetry collector"""
    print_header("Testing Telemetry Collector")
    
    try:
        from telemetry.collector import telemetry_collector
        from config.settings import TelemetryConfig
        
        print_success("TelemetryCollector initialized")
        print_success(f"Collection interval: {TelemetryConfig.COLLECTION_INTERVAL}s")
        print_success(f"Metrics tracked: {len(TelemetryConfig.METRICS)}")
        
        # Show metrics
        print("\n  Tracked metrics:")
        for metric in TelemetryConfig.METRICS:
            print(f"    - {metric}")
            
    except Exception as e:
        print_error(f"Telemetry collector test failed: {e}")


def test_file_structure():
    """Test project file structure"""
    print_header("Testing File Structure")
    
    required_files = [
        'api/main.py',
        'core/safety_engine.py',
        'core/attack_executor.py',
        'telemetry/collector.py',
        'c2_integration/sliver_client.py',
        'config/settings.py',
        'requirements.txt',
        'setup.sh',
        'run.sh',
        'README.md',
        'WINDOWS_SETUP.md',
    ]
    
    for filepath in required_files:
        if os.path.exists(filepath):
            print_success(f"File exists: {filepath}")
        else:
            print_error(f"File missing: {filepath}")


def print_summary():
    """Print test summary"""
    print_header("Test Summary")
    print("\nIf all checks show ✓, your setup is ready!")
    print("\nNext steps:")
    print("  1. Review any warnings above")
    print("  2. Configure .env with your victim IP")
    print("  3. Setup Windows VM (see WINDOWS_SETUP.md)")
    print("  4. Start API: ./run.sh")
    print("  5. Test: curl http://localhost:8000/health")
    print("\nFor help, see README.md and QUICKSTART.md")


async def main():
    """Run all tests"""
    print(f"{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║         BAS Platform - Setup Verification                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    
    test_python_environment()
    test_system_commands()
    test_configuration()
    test_file_structure()
    test_api_imports()
    test_attack_techniques()
    test_safety_engine()
    await test_telemetry_collector()
    
    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
