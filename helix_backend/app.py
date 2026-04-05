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

# Import Helix Core Components
# Core imports (using project-relative paths)
try:
    from Core_Brain.nlp_engine.nlp_engine import NLPEngine
    from Core_Brain.memory_manager import MemoryManager
    from Core_Brain.nlp_engine.personality_router import PersonalityRouter
    from Core_Brain.adaptive_core.orchestration import AdaptiveOrchestrator
    from fullstack.services.repository import SupabaseRepository
    from fullstack.config import get_settings
    from utils.network_checker.checker import helper as network_checker
    from edge_model.engine import edge_engine
    from router.router import get_routing_decision
except ImportError:
    # Fallback for different CWDs on Render
    from helix_backend.Core_Brain.nlp_engine.nlp_engine import NLPEngine
    from helix_backend.Core_Brain.memory_manager import MemoryManager
    from helix_backend.Core_Brain.nlp_engine.personality_router import PersonalityRouter
    from helix_backend.Core_Brain.adaptive_core.orchestration import AdaptiveOrchestrator
    from helix_backend.fullstack.services.repository import SupabaseRepository
    from helix_backend.fullstack.config import get_settings
    from helix_backend.utils.network_checker.checker import helper as network_checker
    from helix_backend.edge_model.engine import edge_engine
    from helix_backend.router.router import get_routing_decision

# Load Environment
load_dotenv(os.path.join(project_root, 'helix-frontend', '.env'))

# --- HELIX PRODUCTION APP ---
app = Flask(__name__)
app.start_time = time.time()
CORS(app, resources={r"/api/*": {"origins": ["https://helix-ai-eta.vercel.app", "http://localhost:3000"]}})

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
        
        for token in nlp_engine.smart_generate_stream(
            messages,
            privacy_mode=privacy_mode,
            force_offline=force_offline,
            personality=personality
        ):
            payload = json.dumps({"token": token})
            yield f"data: {payload}\n\n"
        
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

# --- LEGACY COMPATIBILITY (REDIRECTS) ---
@app.route('/api/chat', methods=['POST'])
@app.route('/api/chat/stream', methods=['POST'])
@app.route('/api/status', methods=['GET'])
@app.route('/text/process', methods=['POST'])
def legacy_routes():
    # Redirect to v1 version (keeping method/data)
    target = f"/api/v1{request.path}"
    if request.path == "/text/process": target = "/api/v1/chat"
    return redirect(target, code=307)

if __name__ == '__main__':
    # Production server usually run via Gunicorn, but this allows direct dev testing
    app.run(host='0.0.0.0', port=8000, threaded=True)
