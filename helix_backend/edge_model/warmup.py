import logging
import os
import sys

# Ensure d:\ECHO V1 is in path
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(ROOT)

from helix_backend.edge_model.engine import edge_engine

def warmup():
    print(f"🚀 HELIX Edge AI: Activating Local Component... (Root: {ROOT})")
    logging.basicConfig(level=logging.INFO)
    
    # This will trigger the from_pretrained() download if not cached
    success = edge_engine.load_model()
    
    if success:
        print("\n✅ Edge AI successfully activated and model cached.")
        print("💡 You can now use 'Privacy Mode' or go offline with HELIX.")
    else:
        print("\n❌ Failed to activate Edge AI. No compatible engine (ONNX/GGUF) could be initialized.")

if __name__ == "__main__":
    warmup()
