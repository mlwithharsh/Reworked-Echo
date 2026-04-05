import logging
from typing import List, Dict

class ContextManager:
    """Production Context Management (Sliding Window & Summarization)."""
    def __init__(self, max_context: int = 10):
        self.max_context = max_context
        self.logger = logging.getLogger("HELIX.Context")

    def trim_history(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Sliding window for conversation context to prevent token overflows 
        and maintain low-memory local inference.
        """
        if len(history) <= self.max_context:
            return history

        # --- Rule 1: Always keep system prompt ---
        system_msgs = [msg for msg in history if msg.get("role") == "system"]
        
        # --- Rule 2: Keep recent N interactions ---
        recent_msgs = history[-(self.max_context - len(system_msgs)):]
        
        # In the future: Summarize the middle 'trimmed' messages
        # For now, just slide the window
        self.logger.info(f"Context: Trimmed {len(history)} -> {len(system_msgs) + len(recent_msgs)} messages.")
        return system_msgs + recent_msgs

# Singleton
context_manager = ContextManager()
