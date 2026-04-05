import os
import logging
from typing import List, Dict, Optional

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

class EdgeEngine:
    def __init__(self, model_path: str = None):
        self.logger = logging.getLogger(__name__)
        self.model_path = model_path or os.getenv("LOCAL_MODEL_PATH", "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
        self.llm: Optional[Llama] = None
        self.is_loaded = False

    def load_model(self):
        """Lazy load the model to save resources when not in use."""
        if self.is_loaded or self.llm:
            return True

        if not Llama:
            self.logger.error("llama-cpp-python not installed. Please pip install llama-cpp-python.")
            return False

        if not os.path.exists(self.model_path):
            self.logger.error(f"Local model GGUF not found at {self.model_path}")
            return False

        try:
            self.logger.info(f"Loading Edge AI Model: {self.model_path}...")
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=2048,  # context window
                n_threads=4, # adjust based on CPU cores
                verbose=False
            )
            self.is_loaded = True
            self.logger.info("Edge AI Model successfully loaded into memory.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load local model: {e}")
            return False

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 256, temperature: float = 0.7) -> str:
        """
        Generate a response using the local edge model.
        """
        if not self.load_model():
            return "[Edge AI Error]: Model loading failed or not available."

        try:
            # Simple prompt construction for TinyLlama Chat format
            prompt = ""
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    prompt += f"<|system|>\n{content}</s>\n"
                elif role == "user":
                    prompt += f"<|user|>\n{content}</s>\n"
                elif role == "assistant":
                    prompt += f"<|assistant|>\n{content}</s>\n"
            
            prompt += "<|assistant|>\n"
            
            output = self.llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=["</s>"],
                echo=False
            )
            
            response_text = output['choices'][0]['text'].strip()
            return response_text
        except Exception as e:
            self.logger.error(f"Error during edge inference: {e}")
            return f"[Edge AI Error]: Inference failed. {e}"

# Singleton instance
edge_engine = EdgeEngine()
def generate_local(messages, max_tokens=256, temperature=0.7):
    return edge_engine.generate(messages, max_tokens, temperature)
