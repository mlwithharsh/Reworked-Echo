from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
from dotenv import load_dotenv

# Add project root and helix_backend to sys.path
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
from Core_Brain.adaptive_core.orchestration import AdaptiveOrchestrator
from fullstack.services.repository import SupabaseRepository
from fullstack.config import get_settings

# Load environment variables BEFORE initializing components
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'helix-frontend', '.env'))

app = Flask(__name__)
CORS(app)

# Initialize Core Brain & Repository
settings = get_settings()
nlp_engine = NLPEngine()
memory_manager = MemoryManager()
personality_router = PersonalityRouter()
adaptive_orchestrator = AdaptiveOrchestrator(memory_manager)
repository = SupabaseRepository(settings)

@app.route('/', methods=['GET'])
def root():
    return jsonify({"message": "HELIX V1 Backend is active", "status": "online"})

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    name = data.get('name', '')
    
    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400
        
    user_id, error = repository.signup(email, password, name)
    if error:
        return jsonify({"error": error}), 400
    
    return jsonify({"user_id": user_id, "message": "Signup successful"})

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400
        
    user_id, error = repository.login(email, password)
    if error:
        return jsonify({"error": error}), 401
    
    return jsonify({"user_id": user_id, "message": "Login successful"})

@app.errorhandler(404)
def not_found(error):
    print(f"404 error: {request.path} [{request.method}]")
    return jsonify({"error": "Endpoint not found", "path": request.path}), 404

@app.route('/core/status', methods=['GET'])
def get_status():
    return jsonify({"status": "online", "version": "2.0.0", "adaptive_core": True})

@app.route('/text/process', methods=['POST'])
def process_text():
    data = request.json
    user_text = data.get('text') or data.get('message', '')
    personality = data.get('personality', 'Helix')
    session_id = data.get('session_id')
    
    if not user_text:
        return jsonify({"error": "No text provided"}), 400
    
    try:
        # Set personality - Normalize to lowercase for the router
        target_personality = personality.lower()
        personality_router.set_personality(target_personality)
        
        # Get analysis once
        analysis = nlp_engine.get_analysis(user_text)
        prepared = adaptive_orchestrator.prepare(user_text, analysis)
        
        # Get response using router (passing the pre-computed analysis)
        response_text = personality_router.get_response(
            user_text,
            memory_manager,
            analysis,
            prepared,
        )
        if not response_text or str(response_text).startswith("[Groq Error]"):
            response_text = nlp_engine.build_fallback_response(
                user_text,
                analysis=analysis,
                adaptive_context=prepared,
                personality_name=personality,
            )

        completed = adaptive_orchestrator.complete(
            user_text,
            analysis,
            response_text,
            prepared.get("policy_state", {}),
            prepared.get("emotional_state", {}),
        )
        
        # Save to Local memory (for this session)
        memory_manager.add_memory(
            user_text,
            response_text,
            session_id=session_id,
            analysis=analysis,
            reward=completed.get("reward"),
            reflection=completed.get("reflection"),
        )
        
        # PERSIST to Supabase interaction table
        user_id = data.get('user_id') or "guest-user" 
        interaction = repository.create_interaction(
            user_id=user_id,
            input_text=user_text,
            response_text=response_text,
            model_version="2.0.0",
            metadata={
                "personality": personality,
                "analysis": analysis,
                "reward": completed.get("reward")
            }
        )
        
        emotional_state = prepared.get("emotional_state", {})
        policy_state = prepared.get("policy_state", {})
        memory_snapshot = prepared.get("memory_snapshot", {})
        
        return jsonify({
            "type": "done",
            "interaction_id": interaction.id,
            "text": user_text,
            "response": response_text,
            "emotion": analysis.get("emotion", "neutral").upper(),
            "intent": analysis.get("intent", "unknown").upper(),
            "sentiment": analysis.get("sentiment", "neutral").upper(),
            "item_timestamp": "Just now",
            "emotional_state": emotional_state.get("vector", {}),
            "emotional_alignment": emotional_state.get("alignment", "balanced").upper(),
            "policy": policy_state.get("policy", "supportive").upper(),
            "reward": completed.get("reward", 0),
            "reflection": completed.get("reflection", {}),
            "profile": memory_snapshot.get("user_profile", {}),
            "memory": {
                "relevant_memories": memory_snapshot.get("relevant_memories", []),
                "emotional_summary": memory_snapshot.get("emotional_summary", {}),
            },
            "metadata": {
                "model_version": "2.0.0",
                "personality": personality,
                "generation_backend": "flask-legacy"
            },
            "system_label": "Adapting to your preferences"
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
                u_part, e_part = part.split('\nHelix: ')
                history_list.append({
                    "input_text": u_part.replace('User: ', ''),
                    "response": e_part,
                    "timestamp": "Recent",
                    "emotion": "ADAPTIVE",
                    "intent": "MEMORY",
                    "sentiment": "STORED",
                })
            except:
                continue
                
    return jsonify({"history": history_list})

@app.route('/memory/profile', methods=['GET'])
def get_memory_profile():
    return jsonify(memory_manager.get_memory_snapshot())

@app.route('/memory/clear', methods=['POST'])
def clear_memory():
    memory_manager.clear_memory()
    return jsonify({"status": "success"})

# --- Compatibility Routes for /api prefix (Vercel Frontend) ---
@app.route('/api/status', methods=['GET', 'OPTIONS'])
def api_status():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"}), 200
    return jsonify({
        "status": "online", 
        "version": "2.0.0", 
        "adaptive_core": True,
        "supabase_connected": False 
    })

@app.route('/api/chat/stream', methods=['POST', 'OPTIONS'])
def api_chat_stream():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"}), 200
    # Proxies to the main process_text logic but for /api path
    return process_text()

@app.route('/api/users/<user_id>/profile', methods=['GET', 'OPTIONS'])
def api_user_profile(user_id):
    if request.method == 'OPTIONS': return jsonify({"status": "ok"}), 200
    return jsonify(memory_manager.get_memory_snapshot())

@app.route('/api/users/<user_id>/history', methods=['GET', 'OPTIONS'])
def api_user_history(user_id):
    if request.method == 'OPTIONS': return jsonify({"status": "ok"}), 200
    return get_history()

@app.route('/api/users/<user_id>/clear', methods=['POST', 'OPTIONS'])
def api_user_clear(user_id):
    if request.method == 'OPTIONS': return jsonify({"status": "ok"}), 200
    return clear_memory()

@app.route('/api/feedback', methods=['POST', 'OPTIONS'])
def api_feedback():
    if request.method == 'OPTIONS': return jsonify({"status": "ok"}), 200
    data = request.json
    from fullstack.schemas import FeedbackRequest
    
    try:
        feedback_obj = FeedbackRequest(
            interaction_id=data.get("interaction_id"),
            user_id=data.get("user_id", "guest-user"),
            vote=1 if data.get("vote") == 'up' else -1,
            tags=data.get("tags", []),
            notes=data.get("notes", "")
        )
        reward = 1.0 if feedback_obj.vote == 1 else -0.5
        
        # Save to DB
        repository.add_feedback(feedback_obj, reward)
        
        # Also update local memory snapshot
        memory_manager.submit_feedback(
            feedback_obj.interaction_id,
            data.get("vote"),
            feedback_obj.tags
        )
        
        return jsonify({
            "status": "success",
            "updated_profile": memory_manager.get_memory_snapshot()
        })
    except Exception as e:
        print(f"Feedback error: {e}")
        return jsonify({"error": "Failed to record feedback"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
