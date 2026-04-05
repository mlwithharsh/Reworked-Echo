import logging
from ..utils.network_checker.checker import helper as network_checker

class ModelRouter:
    """Production Model Router with Adaptive Scoring and Capability Tagging."""
    def __init__(self, privacy_mode=False):
        self.privacy_mode = privacy_mode
        self.logger = logging.getLogger("HELIX.ModelRouter")
        self.base_threshold = 28
        self.adaptive_offset = 0 # Dynamic adjustment based on cloud latency
        self.history_ratios = []

    def classify_query(self, query: str) -> str:
        """Capability Tagging: Classifies query for specialized routing/processing."""
        query_lowered = query.lower()
        if any(kw in query_lowered for kw in ["code", "function", "script", "import", "class"]):
            return "code"
        if any(kw in query_lowered for kw in ["analyze", "summarize", "evaluate", "compare"]):
            return "analysis"
        if any(kw in query_lowered for kw in ["settings", "version", "status", "who are you"]):
            return "system"
        return "chat"

    def evaluate_complexity(self, query: str) -> int:
        score = 0
        words = query.lower().split()
        length = len(words)
        tag = self.classify_query(query)

        # Baseline: Length
        score += length * 2

        # Tag-based scoring
        if tag == "code": score += 30
        if tag == "analysis": score += 20
        if tag == "system": score -= 15 # System queries are very simple

        # Structural markers
        if "?" in query: score += 5
        if "\n" in query: score += 10

        self.logger.info(f"Analysis: Tag={tag} Score={score}")
        return max(0, score)

    def adjust_threshold(self, cloud_latency: float):
        """Adaptive Scoring: Adjust threshold based on cloud performance."""
        if cloud_latency > 15.0: # Cloud is very slow
            self.adaptive_offset -= 5 # Lower threshold (use LOCAL more)
            self.logger.info(f"Adaptive: Cloud slow ({cloud_latency:.1f}s). Lowering threshold.")
        elif cloud_latency < 2.0: # Cloud is fast
            self.adaptive_offset = min(0, self.adaptive_offset + 2) # Restore base
            
        self.adaptive_offset = max(-15, min(10, self.adaptive_offset))

    def decide(self, query: str, force_offline: bool = False) -> dict:
        # Precedence 1: Offline
        if not network_checker.is_online() or force_offline:
            return {"route": "edge", "tag": self.classify_query(query)}

        # Precedence 2: Privacy Mode
        if self.privacy_mode:
            return {"route": "edge", "tag": self.classify_query(query)}

        # Precedence 3: Adaptive Score-based decision
        score = self.evaluate_complexity(query)
        threshold = self.base_threshold + self.adaptive_offset
        
        route = "cloud" if score >= threshold else "edge"
        self.logger.info(f"ROUTING: {route} (Score={score} Threshold={threshold})")
        
        return {
            "route": route,
            "tag": self.classify_query(query),
            "score": score
        }

# Singleton instance
router = ModelRouter()
def get_routing_decision(query, privacy_mode=False, force_offline=False):
    router.privacy_mode = privacy_mode
    return router.decide(query, force_offline)
