# NLP Engine — intent detection, emotion analysis, Groq API integration
import json
import logging
import os
import time
from functools import lru_cache
from pathlib import Path

import requests
from helix_backend.router.router import get_routing_decision
from helix_backend.edge_model.engine import generate_local

try:
    from dotenv import load_dotenv
    # Load from project root .env
    _root = Path(__file__).resolve().parents[3]
    load_dotenv(_root / ".env")
except ImportError:
    pass


class NLPEngine:
    def __init__(self, model_name="llama-3.1-8b-instant", api_key=None):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

        if not self.api_key:
            self.logger.warning("GROQ_API_KEY not found — Groq calls will fail and fall back to local model.")

    def smart_generate(self, messages, max_tokens=200, temperature=0.7, privacy_mode=False, force_offline=False):
        """
        Intelligently routes and generates response using either local or cloud model.
        """
        # Get the user query (last message)
        user_query = messages[-1].get("content", "")
        
        # 1. Ask the Router
        decision = get_routing_decision(user_query, privacy_mode=privacy_mode, force_offline=force_offline)
        
        if decision == "local":
            self.logger.info("Executing LOCAL EDGE AI generation...")
            return generate_local(messages, max_tokens=max_tokens, temperature=temperature)
        else:
            self.logger.info("Executing CLOUD API generation...")
            response = self.call_groq_model(messages, max_tokens=max_tokens, temperature=temperature)
            
            # If cloud fails, fallback to local as absolute safety
            if response.startswith("[Groq Error]"):
                self.logger.warning("Cloud failed, falling back to local model...")
                return generate_local(messages, max_tokens=max_tokens, temperature=temperature)
            
            return response

    def call_groq_model(self, messages, max_tokens=200, temperature=0.7):
        if not self.api_key:
            self.logger.error("No GROQ_API_KEY configured.")
            return "[Groq Error]: No API key configured"

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": 1,
            "stream": False,
        }

        for attempt in range(3):
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                }

                self.logger.info(f"[Groq Attempt {attempt + 1}] model={self.model_name}, messages={len(messages)}")
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)

                if not response.content:
                    self.logger.warning(f"[Attempt {attempt + 1}] Empty response from Groq.")
                    if attempt < 2:
                        time.sleep(3)
                    continue

                if response.status_code == 429:
                    self.logger.warning(f"[Attempt {attempt + 1}] Rate limit hit, waiting...")
                    if attempt < 2:
                        time.sleep(5)
                    continue

                if response.status_code != 200:
                    self.logger.warning(f"[Attempt {attempt + 1}] HTTP {response.status_code}: {response.text}")
                    if attempt < 2:
                        time.sleep(3)
                    continue

                try:
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        content = result["choices"][0]["message"]["content"].strip()
                        self.logger.info(f"[Groq] Response received ({len(content)} chars)")
                        return content
                    self.logger.warning(f"[Attempt {attempt + 1}] Invalid response structure: {result}")
                    if attempt < 2:
                        time.sleep(3)
                except Exception as error:
                    self.logger.error(f"[Attempt {attempt + 1}] JSON parsing error: {error}")
                    if attempt < 2:
                        time.sleep(3)
            except Exception as error:
                self.logger.error(f"[Attempt {attempt + 1}] Request Error: {error}")
                if attempt < 2:
                    time.sleep(3)

        return "[Groq Error]: Failed after 3 attempts"

    def _keyword_intent_fallback(self, user_input):
        lowered = (user_input or "").lower()
        if any(token in lowered for token in ["hi", "hello", "hey"]):
            return "greeting"
        if any(token in lowered for token in ["weather", "temperature", "rain"]):
            return "get_weather"
        if any(token in lowered for token in ["help", "please", "can you", "could you"]):
            return "request"
        if any(token in lowered for token in ["sad", "anxious", "stress", "lonely", "upset"]):
            return "emotional_support"
        if "?" in lowered:
            return "question"
        return "unknown"

    def _keyword_emotion_fallback(self, user_input):
        lowered = (user_input or "").lower()
        emotion = "neutral"
        sentiment = "neutral"

        if any(token in lowered for token in ["happy", "great", "awesome", "excited", "love"]):
            emotion = "happy"
            sentiment = "positive"
        elif any(token in lowered for token in ["sad", "down", "hurt", "lonely"]):
            emotion = "sad"
            sentiment = "negative"
        elif any(token in lowered for token in ["angry", "mad", "annoyed", "frustrated"]):
            emotion = "angry"
            sentiment = "negative"
        elif any(token in lowered for token in ["afraid", "scared", "anxious", "worried", "stress"]):
            emotion = "fear"
            sentiment = "negative"
        elif any(token in lowered for token in ["wow", "surprised", "unexpected"]):
            emotion = "surprise"
        return {"emotion": emotion, "sentiment": sentiment}

    def build_fallback_response(self, user_input, analysis=None, adaptive_context=None, personality_name="Helix"):
        analysis = analysis or {}
        emotional_state = (adaptive_context or {}).get("emotional_state", {})
        alignment = emotional_state.get("alignment", "balanced")
        intent = analysis.get("intent", "unknown")
        emotion = analysis.get("emotion", "neutral")
        policy = ((adaptive_context or {}).get("policy_state") or {}).get("policy", "supportive")

        if policy == "celebratory":
            return f"That sounds genuinely exciting! I'd love to help you build on this momentum."
        if alignment == "grounding" or emotion in {"sad", "angry", "fear"}:
            return f"I hear the weight in what you said. Let's slow it down and take the next step together."
        if intent in {"question", "request"}:
            return f"I understand what you need. I can help with that — let's work through it together."
        return f"I'm here with you. Tell me more about what's on your mind."

    @lru_cache(maxsize=128)
    def detect_intent_cached(self, user_input: str) -> str:
        return self.detect_intent(user_input)

    def detect_intent(self, user_input: str) -> str:
        messages = [
            {
                "role": "system",
                "content": "You are an intent detector. Respond with one word only: 'greeting', 'question', 'request', 'get_weather', 'emotional_support', 'manipulation_check', or 'unknown'.",
            },
            {"role": "user", "content": user_input},
        ]

        result = self.call_groq_model(messages, max_tokens=10).lower().strip()
        if result.startswith("[groq error]"):
            return self._keyword_intent_fallback(user_input)

        valid_intents = ["greeting", "question", "request", "get_weather", "emotional_support", "manipulation_check", "unknown"]
        return result if result in valid_intents else "unknown"

    def detect_emotion(self, user_input: str) -> dict:
        messages = [
            {
                "role": "system",
                "content": 'You are an emotion and sentiment detector. Reply ONLY with JSON like: {"emotion": "sad", "sentiment": "negative"}',
            },
            {"role": "user", "content": user_input},
        ]

        result = self.call_groq_model(messages, max_tokens=50)
        if result.startswith("[Groq Error]"):
            self.logger.warning(f"Groq API error in emotion detection: {result}")
            return self._keyword_emotion_fallback(user_input)

        try:
            start_idx = result.find("{")
            end_idx = result.rfind("}") + 1
            if start_idx != -1 and end_idx != -1:
                json_str = result[start_idx:end_idx]
                parsed_data = json.loads(json_str)
                if "emotion" in parsed_data and "sentiment" in parsed_data:
                    valid_emotions = ["happy", "sad", "angry", "fear", "surprise", "disgust", "neutral"]
                    valid_sentiments = ["positive", "negative", "neutral"]

                    emotion = parsed_data.get("emotion", "neutral")
                    sentiment = parsed_data.get("sentiment", "neutral")
                    if emotion not in valid_emotions:
                        emotion = "neutral"
                    if sentiment not in valid_sentiments:
                        sentiment = "neutral"
                    return {"emotion": emotion, "sentiment": sentiment}

                self.logger.warning(f"Missing required fields in emotion detection response: {parsed_data}")
                return self._keyword_emotion_fallback(user_input)

            self.logger.warning(f"No valid JSON found in emotion detection response: {result}")
            return self._keyword_emotion_fallback(user_input)
        except json.JSONDecodeError as error:
            self.logger.error(f"[JSON Parsing Error]: {error}")
        except Exception as error:
            self.logger.error(f"[Unexpected Error in emotion detection]: {error}")

        return self._keyword_emotion_fallback(user_input)

    def get_analysis(self, user_input: str) -> dict:
        intent = self.detect_intent(user_input)
        emotion_data = self.detect_emotion(user_input)
        return {
            "intent": intent,
            "emotion": emotion_data.get("emotion", "neutral"),
            "sentiment": emotion_data.get("sentiment", "neutral"),
        }

    def analyze(self, user_input: str, memory_manager=None) -> dict:
        context = ""
        if memory_manager:
            context = memory_manager.get_context_text()

        analysis = self.get_analysis(user_input)
        intent = analysis["intent"]
        emotion = analysis["emotion"]
        sentiment = analysis["sentiment"]

        system_prompt = (
            f"You are Helix, a helpful AI assistant.\n"
            f"User's emotion: {emotion}\n"
            f"User's intent: {intent}\n"
            f"Sentiment: {sentiment}\n"
            f"User said: {user_input}\n"
            "Reply as Helix with empathy and understanding (2-3 sentences):"
        )

        if context:
            system_prompt += f"\nHere is the recent conversation:\n{context}\nRespond appropriately."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]

        response = self.call_groq_model(messages, max_tokens=150, temperature=0.8)
        if response.startswith("[Groq Error]"):
            response = self.build_fallback_response(user_input, analysis)

        if memory_manager:
            memory_manager.add_memory(user_input, response, analysis=analysis)

        return {
            "intent": intent,
            "emotion": emotion,
            "sentiment": sentiment,
            "response": response,
        }
