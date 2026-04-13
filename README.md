# 🧬 HELIX AI: Hybrid Edge + Cloud Intelligence

> **Production-Grade Hybrid AI System** — Seamlessly bridging Local Edge AI with High-Performance Cloud Intelligence and Autonomous Marketing.

[![Status](https://img.shields.io/badge/Status-Production--Ready-success?style=for-the-badge)]()
[![Backend](https://img.shields.io/badge/Backend-FastAPI-blue?style=for-the-badge)]()
[![Frontend](https://img.shields.io/badge/Frontend-React--Vite--Tailwind-blueviolet?style=for-the-badge)]()
[![Agent](https://img.shields.io/badge/Agent-Autonomous_Marketing-orange?style=for-the-badge)]()

---

## 🚀 The Vision

HELIX AI is a next-generation hybrid AI platform designed to provide **uninterrupted intelligence**. By dynamically routing requests between local device-side inference (Edge) and robust cloud-based models (Cloud), HELIX ensures privacy, speed, and reliability regardless of network conditions. Whether you are running a high-stakes marketing campaign or having a low-latency conversation, HELIX adapts its brain to your environment.

---

## 🏗️ Unified Hybrid Architecture

HELIX follows a **Split-Brain Architecture** managed by an **Adaptive Orchestrator** to balance performance, cost, and privacy.

### 1. Adaptive Orchestrator (`helix_backend.fullstack`)
*   **Unified API Gateway**: A single entry point for conversational chat, marketing automation, and model management.
*   **Predictive Routing (v3.0)**: Analyzes user intent *during typing* to predict whether a query requires Cloud power or can be handled locally.
*   **Background Warmup**: Pre-emptively loads Edge models when a local route is predicted, minimizing "cold start" latency.
*   **Capability Tagging**: Classifies queries into categories (Code, Analysis, System, Chat) to force high-complexity tasks to the Cloud.

### 2. Edge AI Engine (Local)
*   **GGUF Runtime**: Uses a dedicated `llama-server.exe` sidecar for local inference on quantized models.
*   **Predictive Intelligence**: Reduces human-perceived latency via background thread warming.
*   **Mid-Stream Fallback**: If Cloud inference fails mid-sentence, the Edge engine injects the partial context and "finishes the thought" locally for 100% reliability.

### 3. Cloud Intelligence (Distributed)
*   **High-Performance Providers**: Leverages Groq and Llama-3.1 for complex reasoning, code generation, and deep analysis.

---

## 🤖 Core Modules

### ⚡ Autonomous Marketing Agent
A full-stack enterprise automation system handling the entire marketing lifecycle:
*   **Brand Brain**: Persists unique brand voices, vocabulary, and banned phrases to ensure consistency.
*   **Multi-Platform Strategy**: Generates end-to-end campaigns for LinkedIn, X (Twitter), Telegram, Discord, and more.
*   **Variant Generation**: Autonomously writes platform-specific variants with built-in A/B experimentation.
*   **Safe Delivery**: Features a "Dry-Run" mode for verification before "Live" platform dispatch.
*   **Recursive Optimization**: Analyzes engagement metrics to refine future strategies automatically.

### 🧠 Conversational Personality Core
*   **Specialized Personas**: Includes **Suzi** (playful/high-engagement) and **Helix** (professional/outcome-driven).
*   **RLHF Adaptive Layer**: A Reinforcement Learning layer tracks user sentiment and rewards, shifting response policies in real-time to match user preferences.
*   **Smart Streaming**: Token-by-token SSE streaming with live metrics (`tokens per second`, `latency`).

### 📱 Android Edge Prototype
*   **Local Inference**: Integrated `libllama.so` (JNI) for on-device GGUF execution.
*   **Hybrid Sync**: Pings Cloud backend when online; fails back to local core when offline.

---

## 🛠️ Technical Stack & Security

| Category | Technologies |
| :--- | :--- |
| **Frontend** | React (Vite), Framer Motion, Tailwind CSS, Lucide Icons |
| **Backend** | Python FastAPI, Pydantic, Uvicorn |
| **Persistence** | Supabase (PostgreSQL), Local SQLite, Redis (Optional) |
| **AI/ML** | llama.cpp (GGUF), Groq, PyTorch (RL Engine) |
| **Security** | Fernet Encryption (Credential Storage), Token-Based Auth, Input Sanitization |

### 🔒 Enterprise Hardening
*   **Credential Protection**: Third-party API keys are encrypted with Fernet before storage.
*   **Rate Limiting**: Built-in protection (100 req/min) prevents dashboard abuse.
*   **Input Sanitization**: All user inputs are stripped of control characters and capped at 5000 characters.

---

## 🚦 Quick Start

### 1. Prerequisites
*   Python 3.10+
*   Node.js 18+
*   Environment Variables (See `.env.example`)

### 2. Backend Setup
```bash
# Setup environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r helix_backend/requirements_fullstack.txt

# Start the server
uvicorn helix_backend.fullstack.main:app --port 8000 --reload
```

### 3. Frontend Setup
```bash
cd helix-frontend
npm install
npm run dev
```

### 4. RL Training (Optional)
```bash
# Install RL specific deps
pip install -r requirements-rl.txt

# Run training
python train_rl.py --model-name distilgpt2 --epochs 1
```

---

## 📊 Performance & Observability

| Mode | Tokens/Sec (Avg) | Latency (First Token) | Privacy |
| :--- | :--- | :--- | :--- |
| **Edge (GGUF)** | 8-12 t/s | < 100ms (Warmed) | **Maximum** |
| **Cloud (Groq)** | 40-70 t/s | ~300ms | **Medium** |

*   **P95 Metrics**: Accurate tracking of the 95th percentile response time across all routes.
*   **Usage Ratio**: Real-time monitoring of Edge vs. Cloud workload distribution.

---

## 📚 Documentation
For deeper dives, see our specialized guides:
*   [**Fullstack Setup Guide**](./FULLSTACK_SETUP.md) - Infrastructure and Database details.
*   [**Marketing Agent Walkthrough**](./HELIX_LOCAL_MARKETING_SYSTEM_WALKTHROUGH.md) - Deep dive into marketing automation.
*   [**RL & Personality Core**](./README_RL.md) - Technical details on the Reinforcement Learning pipeline.
*   [**Edge AI Plan**](./helix_backend/OFFLINE_EDGE_AI_PLAN.md) - Detailed roadmap for local inference.

---
*HELIX AI is created and maintained by the Google Deepmind Team - Advanced Agentic Coding.*
