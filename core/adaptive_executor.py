"""
Adaptive Attack Executor
Provides fallback and evasion logic for attack techniques
"""
import logging
from typing import Dict, List, Optional
from core.attack_executor import AttackExecutor, AttackResult

logger = logging.getLogger(__name__)


class AdaptiveAttackExecutor:
    """
    Executes attacks with adaptive fallback logic.
    If primary technique fails/blocked, automatically pivots to fallback techniques.
    """
    
    def __init__(self, attack_executor: AttackExecutor):
        self.executor = attack_executor
        self.fallback_chains: Dict[str, List[str]] = {}
        self.max_retries = 3
        
    def register_fallback_chain(self, primary_id: str, fallback_ids: List[str]):
        """
        Register fallback techniques for a primary technique.
        
        Args:
            primary_id: Primary technique ID (e.g., "T1562.001")
            fallback_ids: List of fallback technique IDs to try in order
        """
        self.fallback_chains[primary_id] = fallback_ids
        logger.info(f"Registered fallback chain: {primary_id} -> {fallback_ids}")
    
    async def execute_adaptive(
        self, 
        technique_id: str, 
        target_ip: str,
        description: str = ""
    ) -> AttackResult:
        """
        Execute attack with automatic fallback on failure.
        
        Args:
            technique_id: Primary technique to execute
            target_ip: Target IP address
            description: Optional description for logging
            
        Returns:
            AttackResult from successful technique or final failure
        """
        logger.info(f"Starting adaptive execution: {technique_id} on {target_ip}")
        
        # Try primary technique
        result = await self.executor.execute_attack(technique_id, target_ip)
        
        if result.status == "completed":
            logger.info(f"✓ Primary technique {technique_id} succeeded")
            return result
        
        # Primary failed - try fallbacks
        if technique_id in self.fallback_chains:
            logger.warning(f"✗ Primary technique {technique_id} failed ({result.status})")
            logger.info(f"→ Pivoting to fallback chain: {self.fallback_chains[technique_id]}")
            
            for fallback_id in self.fallback_chains[technique_id]:
                logger.info(f"→ Attempting fallback: {fallback_id}")
                
                fallback_result = await self.executor.execute_attack(fallback_id, target_ip)
                
                if fallback_result.status == "completed":
                    logger.info(f"✓ Fallback technique {fallback_id} succeeded!")
                    fallback_result.metadata["fallback_from"] = technique_id
                    fallback_result.metadata["fallback_reason"] = result.status
                    return fallback_result
                else:
                    logger.warning(f"✗ Fallback {fallback_id} also failed ({fallback_result.status})")
            
            logger.error(f"All fallback techniques exhausted for {technique_id}")
        
        # No fallbacks or all failed
        result.metadata["fallback_attempted"] = technique_id in self.fallback_chains
        return result
    
    def get_fallback_chain(self, technique_id: str) -> Optional[List[str]]:
        """Get registered fallback chain for a technique"""
        return self.fallback_chains.get(technique_id)


# Predefined fallback chains for common scenarios
DEFENSE_EVASION_FALLBACKS = {
    "T1562.001": ["T1562.004"],  # Disable Defender -> Disable Firewall
    "T1070.001": ["T1027.002"],  # Clear logs -> Obfuscate commands
}

LATERAL_MOVEMENT_FALLBACKS = {
    "T1021.001": ["T1021.002"],  # RDP -> SMB
}
