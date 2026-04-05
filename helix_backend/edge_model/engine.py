import os
import logging
from typing import List, Dict, Optional

# --- Model Selection Config ---
# We'll use optimum + onnxruntime for Windows/CPU high-compatibility
try:
    from optimum.onnxruntime import ORTModelForCausalLM
    from transformers import AutoTokenizer, pipeline
    HAS_OPTIMUM = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"Optimum ONNX not available: {e}")
    HAS_OPTIMUM = False
except Exception as e:
    logging.getLogger(__name__).warning(f"Unexpected error importing Optimum: {e}")
    HAS_OPTIMUM = False

try:
    from llama_cpp import Llama
    HAS_LLAMA_CPP = True
except ImportError:
    HAS_LLAMA_CPP = False

class EdgeEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Using a very small, high-performance model for CPU (Qwen2 0.5B)
        # Xenova's version is pre-optimized for ONNX/CPU
        self.model_id = os.getenv("LOCAL_MODEL_ID", "Xenova/Qwen2-0.5B-Instruct")
        self.llm = None
        self.tokenizer = None
        self.is_loaded = False
        self.engine_type = None # 'onnx' or 'gguf'

    def load_model(self):
        if self.is_loaded:
            return True

        # --- OPTION 1: ONNX Runtime (Optimum) ---
        if HAS_OPTIMUM:
            try:
                self.logger.info(f"Loading Edge AI via ONNX Runtime: {self.model_id}...")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
                self.llm = ORTModelForCausalLM.from_pretrained(
                    self.model_id,
                    provider="CPUExecutionProvider",
                    use_cache=True,
                    use_io_binding=True
                )
                self.engine_type = 'onnx'
                self.is_loaded = True
                return True
            except Exception as e:
                self.logger.warning(f"ONNX loading failed: {e}. Trying GGUF...")

        # --- OPTION 2: Llama.cpp (GGUF) ---
        if HAS_LLAMA_CPP:
            model_path = os.getenv("LOCAL_MODEL_PATH", "models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")
            if os.path.exists(model_path):
                try:
                    self.logger.info(f"Loading Edge AI via GGUF: {model_path}...")
                    self.llm = Llama(model_path=model_path, n_ctx=2048, n_threads=4, verbose=False)
                    self.engine_type = 'gguf'
                    self.is_loaded = True
                    return True
                except Exception as e:
                    self.logger.error(f"GGUF loading failed: {e}")
            else:
                self.logger.warning(f"GGUF model not found at {model_path}")

        self.logger.error("No compatible local AI engine (ONNX/GGUF) found or installed.")
        return False

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 150, temperature: float = 0.7) -> str:
        if not self.load_model():
            return "[Edge AI Error]: No local inference engine available (Installation required)."

        try:
            if self.engine_type == 'onnx':
                # ONNX Generation
                prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = self.tokenizer(prompt, return_tensors="pt")
                
                output = self.llm.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    top_k=50,
                    top_p=0.95
                )
                
                # Strip the prompt from the response
                response = self.tokenizer.decode(output[0], skip_special_tokens=True)
                if prompt in response:
                    response = response.replace(prompt, "").strip()
                return response

            elif self.engine_type == 'gguf':
                # GGUF Generation (Legacy path)
                prompt = ""
                for msg in messages:
                    prompt += f"<|{msg['role']}|>\n{msg['content']}</s>\n"
                prompt += "<|assistant|>\n"
                
                output = self.llm(prompt, max_tokens=max_tokens, temperature=temperature, stop=["</s>"], echo=False)
                return output['choices'][0]['text'].strip()

        except Exception as e:
            self.logger.error(f"Inference error: {e}")
            return f"[Edge AI Error]: Generation failed. {e}"

# Singleton instance
edge_engine = EdgeEngine()
def generate_local(messages, max_tokens=150, temperature=0.7):
    return edge_engine.generate(messages, max_tokens, temperature)
