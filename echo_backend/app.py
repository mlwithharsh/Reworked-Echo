from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv

# Add project root and echo_backend to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_root = os.path.dirname(os.path.abspath(__file__))

if project_root not in sys.path:
    sys.path.append(project_root)
if backend_root not in sys.path:
    sys.path.append(backend_root)

# Import components
from Core_Brain.nlp_engine.nlp_engine import NLPEngine
from Core_Brain.memory_manager import MemoryManager
from Core_Brain.nlp_engine.personality_router import PersonalityRouter

# Load environment variables BEFORE initializing components
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'echo-v1-frontend', '.env'))

app = Flask(__name__)
CORS(app)

# Initialize Core Brain
nlp_engine = NLPEngine()
memory_manager = MemoryManager()
personality_router = PersonalityRouter()

@app.route('/', methods=['GET'])
def root():
    return jsonify({"message": "ECHO V1 Backend is active", "status": "online"})

@app.errorhandler(404)
def not_found(error):
    print(f"404 error: {request.path} [{request.method}]")
    return jsonify({"error": "Endpoint not found", "path": request.path}), 404

@app.route('/core/status', methods=['GET'])
def get_status():
    return jsonify({"status": "online", "version": "1.0.0"})

@app.route('/text/process', methods=['POST'])
def process_text():
    data = request.json
    user_text = data.get('text', '')
    personality = data.get('personality', 'Echo')
    
    if not user_text:
        return jsonify({"error": "No text provided"}), 400
    
    try:
        # Set personality - Normalize to lowercase for the router
        target_personality = personality.lower()
        personality_router.set_personality(target_personality)
        
        # Get analysis once
        analysis = nlp_engine.get_analysis(user_text)
        
        # Get response using router (passing the pre-computed analysis)
        response_text = personality_router.get_response(user_text, memory_manager, analysis)
        
        return jsonify({
            "text": user_text,
            "response": response_text,
            "emotion": analysis.get("emotion", "neutral").upper(),
            "intent": analysis.get("intent", "unknown").upper(),
            "sentiment": analysis.get("sentiment", "neutral").upper(),
            "timestamp": "Just now"
        })
    except Exception as e:
        print(f"Error in /text/process: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/memory/history', methods=['GET'])
def get_history():
    # Convert encrypted memory to text for frontend
    history_text = memory_manager.get_context_text()
    # Simple parsing back to list for frontend
    history_list = []
    if history_text:
        parts = history_text.split('\nUser: ')
        for part in parts:
            if not part: continue
            # Handle first part differently
            if not part.startswith('User: '):
                part = 'User: ' + part
            
            try:
                u_part, e_part = part.split('\nEcho: ')
                history_list.append({
                    "input_text": u_part.replace('User: ', ''),
                    "response": e_part,
                    "timestamp": "Recent"
                })
            except:
                continue
                
    return jsonify({"history": history_list})

@app.route('/memory/clear', methods=['POST'])
def clear_memory():
    memory_manager.clear_memory()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
