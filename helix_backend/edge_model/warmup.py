import logging
import os
import sys

# Add backend to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from helix_backend.edge_model.engine import edge_engine

def warmup():
    print("🚀 HELIX Edge AI: Starting Local Component Activation...")
    logging.basicConfig(level=logging.INFO)
    
    # This will trigger the from_pretrained() download if not cached
    success = edge_engine.load_model()
    
    if success:
        print("\n✅ Edge AI successfully activated and model cached.")
        print("💡 You can now use 'Privacy Mode' or go offline with HELIX.")
    else:
        print("\n❌ Failed to activate Edge AI. Check your internet connection for the first-time setup.")

if __name__ == "__main__":
    warmup()
