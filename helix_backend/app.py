from flask import Flask, request, jsonify, Response, stream_with_context, redirect
from flask_cors import CORS
import os
import sys
import time
import json
import logging
import threading
import psutil
from datetime import datetime
from dotenv import load_dotenv

# Path setup for internal modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from helix_backend.Core_Brain.nlp_engine.nlp_engine import NLPEngine
    from helix_backend.Core_Brain.memory_manager import MemoryManager
    from helix_backend.Core_Brain.nlp_engine.personality_router import PersonalityRouter
    from helix_backend.Core_Brain.adaptive_core.orchestration import AdaptiveOrchestrator
    from helix_backend.fullstack.services.repository import SupabaseRepository
    from helix_backend.fullstack.config import get_settings
    from helix_backend.utils.network_checker.checker import helper as network_checker
    from helix_backend.edge_model.engine import edge_engine
    from helix_backend.router.router import get_routing_decision
except ImportError:
    # Alternative path for when helix_backend is the CWD
    from Core_Brain.nlp_engine.nlp_engine import NLPEngine
    from Core_Brain.memory_manager import MemoryManager
    from Core_Brain.nlp_engine.personality_router import PersonalityRouter
    from Core_Brain.adaptive_core.orchestration import AdaptiveOrchestrator
    from fullstack.services.repository import SupabaseRepository
    from fullstack.config import get_settings
    from utils.network_checker.checker import helper as network_checker
    from edge_model.engine import edge_engine
    from router.router import get_routing_decision


# Load Environment
load_dotenv(os.path.join(project_root, '.env'))


# --- HELIX PRODUCTION APP ---
app = Flask(__name__)
app.start_time = time.time()
CORS(app, resources={r"/api/*": {
    "origins": ["https://helix-ai-eta.vercel.app", "http://localhost:3000"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization", "X-API-Key", "X-API-Token"],
    "supports_credentials": True
}})


# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("HELIX.API")

# Initialize Singletons with extreme caution
try:
    settings = get_settings()
    nlp_engine = NLPEngine()
    memory_manager = MemoryManager()
    personality_router = PersonalityRouter()
    adaptive_orchestrator = AdaptiveOrchestrator(memory_manager)
    repository = SupabaseRepository(settings)
except Exception as e:
    logger.error(f"FATAL: Singleton initialization failed: {e}")
    # Partial mock to prevent hard crashes
    repository = None
    nlp_engine = NLPEngine()

# --- SECURITY & UTILS ---
API_KEY = os.getenv("HELIX_API_KEY", "prod-helix-key-2024")
API_SESSIONS = {} # Rate tracking
MAX_CONTENT_LENGTH = 100 * 1024 # 100KB limit per request

def sanitize_input(text: str) -> str:
    """Production input sanitization."""
    if not text: return ""
    # Remove potentially harmful control characters and trim
    return "".join(c for c in text if c.isprintable()).strip()[:5000]

@app.before_request
def limit_payload_size():
    """Security: Enforce payload size limits."""
    if request.content_length and request.content_length > MAX_CONTENT_LENGTH:
        return jsonify({"error": "Payload too large"}), 413

def validate_api_key():
    key = request.headers.get("X-API-Key")
    if key != API_KEY:
        return False
    return True

def check_rate_limit(user_id):
    now = time.time()
    user_data = API_SESSIONS.get(user_id, {"last": 0, "count": 0})
    if now - user_data["last"] < 1: # 1 req/sec limit
        if user_data["count"] > 3: # allow burst of 3
            return False
        user_data["count"] += 1
    else:
        user_data["count"] = 1
    
    user_data["last"] = now
    API_SESSIONS[user_id] = user_data
    return True

# --- SHARED API v1 HELPERS ---
def model_to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj

# --- AUTHENTICATION v1 ---
@app.route('/api/auth/signup', methods=['POST'])
def auth_signup():
    data = request.json
    name = data.get("name", "")
    email = data.get("email", "")
    password = data.get("password", "")
    if not repository: return jsonify({"error": "DB Unavailable"}), 503
    user_id, error = repository.signup(email, password, name)
    if error: return jsonify({"error": error}), 400
    return jsonify({"user_id": user_id, "message": "Success"})

@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.json
    email = data.get("email", "")
    password = data.get("password", "")
    if not repository: return jsonify({"error": "DB Unavailable"}), 503
    user_id, error = repository.login(email, password)
    if error: return jsonify({"error": error}), 401
    return jsonify({"user_id": user_id, "message": "Login Success"})

@app.route('/api/users/<user_id>/profile', methods=['GET', 'PUT'])
def user_profile(user_id):
    if not repository: return jsonify({"error": "DB Unavailable"}), 503
    if request.method == 'GET':
        profile = repository.get_user_profile(user_id)
        return jsonify(model_to_dict(profile))
    else:
        # PUT logic (update)
        # Simplified: assume input matches model
        from helix_backend.fullstack.schemas import PersonalityProfile
        try:
            profile_data = PersonalityProfile(**request.json)
            updated = repository.upsert_user_profile(profile_data)
            return jsonify(model_to_dict(updated))
        except Exception as e:
            return jsonify({"error": str(e)}), 400

@app.route('/api/users/<user_id>/history', methods=['GET'])
def user_history(user_id):
    if not repository: return jsonify({"error": "DB Unavailable"}), 503
    records = repository.list_recent_interactions(user_id)
    # Convert records to dicts for JSON
    items = []
    for r in records:
        d = model_to_dict(r)
        # Ensure timestamp is ISO string
        if isinstance(d.get('created_at'), datetime):
            d['created_at'] = d['created_at'].isoformat()
        items.append(d)
    return jsonify({"items": items})

@app.route('/api/users/<user_id>/clear', methods=['POST'])
def clear_user_history(user_id):
    if not repository: return jsonify({"error": "DB Unavailable"}), 503
    repository.clear_history(user_id)
    return jsonify({"status": "cleared"})

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    if not repository: return jsonify({"error": "DB Unavailable"}), 503
    from helix_backend.fullstack.schemas import FeedbackRequest
    from helix_backend.fullstack.services.reward_service import feedback_reward
    try:
        data = request.json
        fb_req = FeedbackRequest(**data)
        reward = feedback_reward(fb_req.vote, fb_req.tags)
        repository.add_feedback(fb_req, reward)
        
        # Update user profile based on reward/tags (simplified)
        current = repository.get_user_profile(fb_req.user_id)
        from helix_backend.fullstack.services.profile_adapter import update_profile_from_feedback
        updated = update_profile_from_feedback(current, fb_req)
        repository.upsert_user_profile(updated)
        
        return jsonify({"reward": reward, "updated_profile": model_to_dict(updated)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- API v1 CONTRACTS ---


@app.route('/api/v1/status', methods=['GET'])
def get_status():
    """PRODUCTION v1: Status observability."""
    is_online = network_checker.is_online()
    try:
        ram_avail = int(psutil.virtual_memory().available / (1024*1024))
    except:
        ram_avail = 0
    return jsonify({
        "status": "online",
        "version": "1.0.0-beta",
        "provider": "HELIX-HYBRID",
        "network": "online" if is_online else "offline",
        "edge_engine": "warm" if edge_engine.is_loaded else "cold",
        "ram_available_mb": ram_avail,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/v1/metrics', methods=['GET'])
def get_metrics():
    """PRODUCTION v1: Measurable performance metrics."""
    if not validate_api_key():
        return jsonify({"error": "Unauthorized metrics access"}), 401
    return jsonify({
        "helix_engine_metrics": nlp_engine.metrics,
        "system_ram_mb": int(psutil.virtual_memory().available / (1024*1024)),
        "uptime_sec": int(time.time() - getattr(app, 'start_time', time.time()))
    })

@app.route('/api/v1/warmup', methods=['POST'])
def edge_warmup():
    """LIFECYCLE v1: Manual activation of the Edge AI model."""
    success = edge_engine.warmup()
    return jsonify({"success": success, "status": "warm" if success else "failed"})

@app.route('/api/v1/unload', methods=['POST'])
def edge_unload():
    """LIFECYCLE v1: Manual release of system RAM."""
    edge_engine.unload_model()
    return jsonify({"success": True, "status": "cold"})

@app.route('/api/v1/predict', methods=['POST'])
def predict_route():
    """PREEMPTIVE v1: Predict route and warm up engine while user is typing."""
    data = request.json
    partial_text = data.get('text', '')
    if not partial_text: return jsonify({"status": "idle"})
    
    routing_data = get_routing_decision(partial_text)
    route = routing_data["route"]
    
    if route == "edge":
        # Background warmup
        threading.Thread(target=edge_engine.warmup).start()
        return jsonify({"prediction": "edge", "action": "warming_up"})
    
    return jsonify({"prediction": "cloud", "action": "none"})

@app.route('/api/v1/chat', methods=['POST'])
def chat_blocking():
    """PRODUCTION v1: Standard chat endpoint."""
    data = request.json
    user_id = data.get('user_id', 'guest')
    user_text = sanitize_input(data.get('message', '') or data.get('text', ''))
    
    if not user_text:
        return jsonify({"error": "Message content required"}), 400
        
    if not check_rate_limit(user_id):
        return jsonify({"error": "Rate limit exceeded"}), 429

    logger.info(f"Chat request starting: user={user_id}")
    start_time = time.time()
    
    # Extract settings
    personality = data.get('personality', 'Helix').lower()
    privacy_mode = data.get('privacy_mode', False)
    force_offline = data.get('force_offline', False)
    
    # Process through Hybrid Engine
    analysis = nlp_engine.get_analysis(user_text)
    messages = [{"role": "user", "content": user_text}] # Simplified
    
    response_text = nlp_engine.smart_generate(
        messages, 
        privacy_mode=privacy_mode, 
        force_offline=force_offline,
        personality=personality
    )
    
    latency = time.time() - start_time
    logger.info(f"Chat completed: latency={latency:.2f}s")
    
    # Persistent Record
    if repository:
        repository.create_interaction(
            user_id, user_text, response_text, 
            "1.0.0-beta", # version
            {"latency": f"{latency:.2f}s", "model": "edge" if force_offline or privacy_mode else "hybrid"}
        )
    
    return jsonify({
        "interaction_id": f"int-{int(time.time())}",
        "response": response_text,
        "metadata": {
            "latency": f"{latency:.2f}s",
            "model_path": "edge" if force_offline or privacy_mode else "hybrid"
        }
    })


@app.route('/api/v1/chat/stream', methods=['POST'])
def chat_streaming():
    """PRODUCTION v1: SSE Streaming Endpoint with JSON Fallback."""
    data = request.json
    user_id = data.get('user_id', 'guest')
    user_text = sanitize_input(data.get('message', ''))
    
    if not user_text:
        return jsonify({"error": "Message content required"}), 400

    personality = data.get('personality', 'Helix').lower()
    privacy_mode = data.get('privacy_mode', False)
    force_offline = data.get('force_offline', False)

    # SECURE FALLBACK: If client is not requesting event-stream, return full JSON
    # This fixes SyntaxErrors on the Vercel frontend if it uses standard fetch()
    accept_header = request.headers.get("Accept", "")
    if "text/event-stream" not in accept_header:
        logger.info(f"Stream called via standard Request: user={user_id}. Using JSON fallback.")
        messages = [{"role": "user", "content": user_text}]
        response_text = nlp_engine.smart_generate(
            messages,
            privacy_mode=privacy_mode,
            force_offline=force_offline,
            personality=personality
        )
        return jsonify({"response": response_text, "mode": "json_fallback"})

    def generate():
        logger.info(f"SSE Stream starting: user={user_id}")
        messages = [{"role": "user", "content": user_text}]
        full_response = ""
        
        try:
            for token in nlp_engine.smart_generate_stream(
                messages,
                privacy_mode=privacy_mode,
                force_offline=force_offline,
                personality=personality
            ):
                full_response += token
                payload = json.dumps({"token": token})
                yield f"data: {payload}\n\n"
            
            # Persistent Record at End of Stream
            if repository and full_response:
                repository.create_interaction(
                    user_id, user_text, full_response, 
                    "1.0.0-beta", 
                    {"mode": "stream", "model": "hybrid"}
                )
        except Exception as e:
            import traceback
            logger.error(f"Stream error Traceback: {traceback.format_exc()}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


# --- LEGACY COMPATIBILITY (REDIRECTS) ---
@app.route('/api/chat', methods=['POST'])
@app.route('/api/chat/stream', methods=['POST'])
@app.route('/api/status', methods=['GET'])
@app.route('/text/process', methods=['POST'])
def legacy_routes():
    # Redirect to v1 version (keeping method/data)
    # FIX: Ensure we don't double-prefix if request is already v1
    if request.path.startswith("/api/v1/"): return f"Already v1", 200
    
    target = request.path.replace("/api/", "/api/v1/", 1)
    if request.path == "/text/process": target = "/api/v1/chat"
    return redirect(target, code=307)

if __name__ == '__main__':
    # Production server usually run via Gunicorn, but this allows direct dev testing
    app.run(host='0.0.0.0', port=8000, threaded=True)
