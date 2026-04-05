import logging
from ..utils.network_checker.checker import helper as network_checker

class ModelRouter:
    def __init__(self, privacy_mode=False):
        self.privacy_mode = privacy_mode
        self.logger = logging.getLogger(__name__)

    def decide(self, query: str, force_offline: bool = False) -> str:
        """
        Dynamically route the query to either 'local' or 'cloud' based on
        complexity, network status, and privacy settings.
        """
        # --- Mandatory Local Routing (Force Offline / Privacy) ---
        if force_offline:
            self.logger.info("ROUTING: Forced offline mode. Switching to LOCAL.")
            return "local"
            
        if self.privacy_mode:
            self.logger.info("ROUTING: Privacy mode enabled. Switching to LOCAL.")
            return "local"

        is_online = network_checker.is_online()
        if not is_online:
            self.logger.info("ROUTING: Device is OFFLINE. Falling back to LOCAL model.")
            return "local"

        # --- Dynamic Heuristic Routing (Intelligence) ---
        query_lowered = query.lower()
        query_len = len(query.split())

        # Simple keywords for Cloud (Complexity)
        complex_keywords = ["analyze", "evaluate", "explain deeply", "write code", "elaborate", "structure a plan"]
        is_complex = any(kw in query_lowered for kw in complex_keywords) or query_len > 25

        # Simple keywords for Local (Heuristics)
        simple_keywords = ["hi", "hello", "who are you", "what's the time", "good morning", "hey"]
        is_simple = any(kw in query_lowered for kw in simple_keywords) and query_len < 10

        if is_complex:
            self.logger.info(f"ROUTING: Query is COMPLEX (words={query_len}). Switching to CLOUD.")
            return "cloud"
            
        if is_simple:
            self.logger.info(f"ROUTING: Query is SIMPLE (words={query_len}). Defaulting to LOCAL for speed.")
            return "local"

        # Default for balanced queries
        self.logger.info("ROUTING: Standard query. Using CLOUD for high-quality response.")
        return "cloud"

# Singleton instance
router = ModelRouter()
def get_routing_decision(query, privacy_mode=False, force_offline=False):
    router.privacy_mode = privacy_mode
    return router.decide(query, force_offline)
