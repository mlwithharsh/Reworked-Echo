import os
import logging
import time
import psutil
import subprocess
import requests
import json
import threading
from typing import List, Dict, Optional, Generator

class EdgeEngine:
    """Production Edge Engine using llama-server.exe sidecar for robustness."""
    def __init__(self, model_path: str = None):
        self.logger = logging.getLogger("HELIX.EdgeEngine")
        
        # Paths
        self.edge_dir = os.path.dirname(os.path.abspath(__file__))
        self.server_bin = os.path.join(self.edge_dir, "llama-server.exe")
        
        # Project base (one level up from edge_model/)
        _base = os.path.dirname(self.edge_dir)
        default_model = os.path.join(_base, "models", "qwen2-0_5b-instruct-q4_k_m.gguf")
        self.model_path = model_path or os.getenv("LOCAL_MODEL_PATH", default_model)
        
        # State
        self.process: Optional[subprocess.Popen] = None
        self.port = 8081 # Use 8081 for internal sidecar
        self.is_loaded = False
        self.last_used = 0
        self.idle_timeout = 300 
        self._lock = threading.Lock()
        
        # Lifecycle monitor
        threading.Thread(target=self._idle_monitor, daemon=True).start()

    def _idle_monitor(self):
        while True:
            time.sleep(30)
            if self.is_loaded and (time.time() - self.last_used > self.idle_timeout):
                with self._lock:
                    self.logger.info("Lifecycle: Idle timeout. Unloading sidecar...")
                    self.unload_model()

    def unload_model(self):
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            self.process = None
        self.is_loaded = False
        self.logger.info("Lifecycle: llama-server sidecar terminated.")

    def warmup(self) -> bool:
        with self._lock:
            return self.load_model()

    def load_model(self) -> bool:
        if self.is_loaded and self.process and self.process.poll() is None:
            self.last_used = time.time()
            return True

        if not os.path.exists(self.server_bin) or not os.path.exists(self.model_path):
            self.logger.error(f"Bin/Model missing: {self.server_bin} OR {self.model_path}")
            return False

        try:
            self.logger.info(f"Lifecycle: Starting llama-server sidecar on port {self.port}...")
            # Optimized for CPU usage on 8GB machines
            cmd = [
                self.server_bin,
                "--model", self.model_path,
                "--port", str(self.port),
                "--ctx-size", "2048",
                "--threads", str(min(4, os.cpu_count() or 4)),
                "--parallel", "1",
                "--n-gpu-layers", "0" # CPU Only
            ]
            
            # Start process quietly
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=self.edge_dir
            )
            
            # Wait for server to be ready
            max_wait = 30
            for i in range(max_wait):
                try:
                    res = requests.get(f"http://localhost:{self.port}/health", timeout=1)
                    if res.status_code == 200:
                        self.is_loaded = True
                        self.last_used = time.time()
                        self.logger.info("Lifecycle: Sidecar READY.")
                        return True
                except:
                    pass
                time.sleep(1)
            
            self.logger.error("Lifecycle: Sidecar failed to start within timeout.")
            return False
        except Exception as e:
            self.logger.error(f"Lifecycle: Startup failure. {e}")
            return False

    def generate_stream(self, messages: List[Dict[str, str]], max_tokens: int = 512, timeout: int = 15) -> Generator[str, None, None]:
        if not self.load_model():
            yield "[Edge Error]: Engine sidecar failed to start."
            return

        try:
            self.last_used = time.time()
            prompt = self._format_prompt(messages)
            
            # Call llama-server OAI compatible endpoint
            payload = {
                "prompt": prompt,
                "n_predict": max_tokens,
                "stream": True,
                "stop": ["<|im_start|>", "<|im_end|>", "</s>"]
            }
            
            response = requests.post(
                f"http://localhost:{self.port}/completion",
                json=payload,
                stream=True,
                timeout=timeout
            )
            
            for line in response.iter_lines():
                if line:
                    chunk = line.decode('utf-8')
                    if chunk.startswith("data: "):
                        data = json.loads(chunk[6:])
                        token = data.get("content", "")
                        if token:
                            yield token
            
            self.last_used = time.time()
        except Exception as e:
            self.logger.error(f"Edge Streaming Error: {e}")
            yield f"\n[Edge Error]: {e}"

    def generate(self, messages: List[Dict[str, str]], max_tokens: int = 512, timeout: int = 15) -> str:
        full = ""
        for t in self.generate_stream(messages, max_tokens, timeout):
            full += t
        return full

    def _format_prompt(self, messages: List[Dict[str, str]]) -> str:
        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                formatted += f"<|im_start|>system\n{content}<|im_end|>\n"
            elif role == "user":
                formatted += f"<|im_start|>user\n{content}<|im_end|>\n"
            elif role == "assistant":
                formatted += f"<|im_start|>assistant\n{content}<|im_end|>\n"
        formatted += "<|im_start|>assistant\n"
        return formatted

# Singleton
edge_engine = EdgeEngine()
