from .base_personality import BasePersonality
from Core_Brain.nlp_engine import NLPEngine


class EchoPersonality(BasePersonality):
    def __init__(self):
        super().__init__(name="Echo", style="caring, empathetic", goals="help user emotionally and give supportive replies")
        self.nlp = NLPEngine() 

    def respond(self, user_input, memory, analysis=None):
        if not analysis:
            analysis = self.nlp.get_analysis(user_input)
            
        intent = analysis.get("intent", "unknown")
        emotion = analysis.get("emotion", "neutral")
        sentiment = analysis.get("sentiment", "neutral")

        # Personality-specific system prompt
        system_prompt = (
            f"You are {self.name}, an AI companion for emotional support. "
            f"Style: {self.style}. Goal: {self.goals}. "
            "NEVER use poetic metaphors or overly flowery language like 'whisper of a smile' or 'casting a glow'. "
            "Avoid canned phrases like 'lovely to see you' or 'wonderfully'. "
            "Instead, be direct, human-like, and empathetic. "
            f"User is feeling {emotion} ({sentiment}). Intent: {intent}. "
            f"User input: '{user_input}'\n\n"
            "GUIDELINES:\n"
            "1. Acknowledge what the user said with genuine interest.\n"
            "2. Speak like a real person, not a poet. Be warm but grounded.\n"
            "3. Keep it to 2-3 short, meaningful sentences.\n"
            "4. If they share something good, be happy with them simply. If bad, be supportive simply."
        )

        # Call LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]

        response = self.nlp.call_groq_model(messages, max_tokens=150, temperature=0.8)

        if not response:
            response = "I hear you. I'm here for you, always."

        # Save memory
        if memory:
            memory.add_memory(user_input, response)

        return response