# HELIX ENTERPRISE: Final Advanced Hybrid AI (GGUF) Plan

This document defines the final architectural state for HELIX Enterprise Intelligence, featuring adaptive systems and preemptive logic.

---

## 1. Preemptive Intelligence & Lifecycle
HELIX now predicts user intent during interaction to minimize human-perceived latency.

- **Preemptive Routing**: Via `/api/predict`, the system analyzes typing-time text to predict whether a query will go to Cloud or Edge.
- **Background Warmup**: If the predicted route is Edge, the system pre-emptively warms up the GGUF model in a background thread, ensuring it is ready *before* the user hits Enter.
- **Strict Edge Timeout**: Local inference is capped at **10 seconds** to prevent UI hangs and conserve CPU for other background tasks.

---

## 2. Adaptive Hybrid Routing (v3.0)
The routing engine now features **Capability Tagging** and **Self-Tuning Logic**:

- **Capability Tagging**: Automatically classifies queries into 4 categories:
  - `Code`: High-complexity, forced to Cloud for precision.
  - `Analysis`: Complex, routes to Cloud by default.
  - `System`: Simple, routes to Edge natively.
  - `Chat`: Balanced, routes based on adaptive score.
- **Adaptive Scoring**: The complexity threshold dynamically shifts based on real-world Cloud latency. If the Cloud API slows down (>15s), HELIX automatically lowers its threshold to utilize the local Edge engine more frequently.

---

## 3. Resilient "Partial Fallback" Architecture
To achieve 100% reliability, HELIX implements mid-stream recovery:
- **Mid-Stream Trigger**: If a Cloud (Groq) stream fails or times out *after* starting but before completion, the system detects the interruption.
- **Seamless Local Continuation**: HELIX injects the partial response into the local Edge context and **finishes the thought** natively on the CPU without the user seeing an error.

---

## 4. Enterprise Observability & Memory Hooks
- **Advanced Metrics**:
  - **P95 Latency**: Accurate tracking of the 95th percentile response time.
  - **Usage Ratio**: Continuous monitoring of Edge vs. Cloud workload distribution.
- **Memory Hook (RAG Readiness)**: A formal `memory_lookup_hook` is now integrated into the NLP pipeline, ready for immediate integration with vector databases (ChromaDB/FAISS) for long-term intelligence.

---

## 5. Security & Ingestion Hardening
- **Sanitization Layer**: All user inputs are stripped of non-printable control characters and capped at 5000 characters.
- **Payload Strictness**: All API requests are capped at **100KB** to eliminate buffer-injection or DOS vectors.
- **Credential Protection**: Unified Header-based X-API-Key validation for all administrative/metrics endpoints.

---

## 6. Final Engineering Checklist
- [x] **Preemptive Warming**: Predictive model loading.
- [x] **Capability Tagging**: Specialized classification logic.
- [x] **Adaptive Thresholds**: Performance-aware self-tuning.
- [x] **Partial Fallback**: Resilient mid-stream recovery.
- [x] **Security Hardening**: Sanitization and payload limits.
- [x] **P95 Metrics Suite**: Enterprise-grade observability.
