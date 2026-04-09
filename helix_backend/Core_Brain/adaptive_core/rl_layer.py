class ReinforcementLearningLayer:
    def __init__(self):
        self.q_values = {
            "supportive": 0.55,
            "direct": 0.5,
            "curious": 0.45,
            "celebratory": 0.45,
            "provocative": 0.40,
            "playful": 0.40,
        }
        self.learning_rate = 0.2
        self.last_policy = "supportive"

    def select_policy(self, emotional_state, analysis):
        stress = emotional_state["vector"]["stress"]
        excitement = emotional_state["vector"]["excitement"]
        curiosity = emotional_state["vector"]["curiosity"]
        intent = (analysis or {}).get("intent", "unknown")

        if stress > 0.65:
            policy = "supportive"
        elif excitement > 0.7:
            policy = "celebratory"
        elif curiosity > 0.6 or intent == "question":
            policy = "curious"
        elif intent == "flirty": # New intent for Suzi
            policy = "provocative"
        elif intent == "playful": # New intent for Helix
            policy = "playful"
        else:
            policy = max(self.q_values, key=self.q_values.get)

        self.last_policy = policy
        return {
            "policy": policy,
            "q_values": {key: round(value, 3) for key, value in self.q_values.items()},
        }

    def compute_reward(self, user_input, analysis, response_text, previous_sentiment=None):
        reward = 0.0
        words = len((user_input or "").split())
        reward += min(words / 30, 0.25)
        reward += 0.4 if response_text and not str(response_text).startswith("[Groq Error]") else -0.3

        current_sentiment = (analysis or {}).get("sentiment", "neutral")
        sentiment_score = {"negative": -1, "neutral": 0, "positive": 1}
        if previous_sentiment is not None:
            reward += (sentiment_score.get(current_sentiment, 0) - sentiment_score.get(previous_sentiment, 0)) * 0.15

        if (analysis or {}).get("intent") not in {"unknown", None, ""}:
            reward += 0.1
            
        # Specific rewards for new personality behaviors
        if (analysis or {}).get("intent") in {"flirty", "playful"}:
            reward += 0.15 # Higher reward for engaging with these new traits

        return max(-1.0, min(1.0, round(reward, 3)))

    def update(self, reward, policy=None):
        active_policy = policy or self.last_policy
        current_q = self.q_values.get(active_policy, 0.5)
        updated_q = current_q + self.learning_rate * (reward - current_q)
        self.q_values[active_policy] = round(updated_q, 3)
        return {"policy": active_policy, "updated_q": self.q_values[active_policy], "reward": reward}
