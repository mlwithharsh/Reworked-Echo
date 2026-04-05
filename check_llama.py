import os
from pathlib import Path
try:
    from llama_cpp import Llama
    print("SUCCESS: llama_cpp found.")
except ImportError as e:
    print(f"FAIL: llama_cpp NOT found. {e}")

model_path = r"d:\ECHO V1\helix_backend\models\qwen2-0_5b-instruct-q4_k_m.gguf"
print(f"Checking path: {model_path}")
if os.path.exists(model_path):
    print(f"SUCCESS: File exists. Size: {os.path.getsize(model_path)/1e6:.1f}MB")
else:
    print("FAIL: File does NOT exist.")

import psutil
available_ram = psutil.virtual_memory().available / (1024 * 1024)
print(f"Available RAM: {available_ram:.1f}MB")
if available_ram < 1024:
    print("WARNING: RAM below 1GB threshold.")
