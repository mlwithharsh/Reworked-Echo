# HELIX Hybrid AI Architecture Guide

HELIX is a next-generation hybrid AI platform that seamlessly alternates between low-latency local execution and high-performance cloud inference. It is designed to empower cross-platform marketing automation and personality-driven conversational experiences.

---

## 🏛️ Core Architecture

The system follows a split-brain architecture where data and logic are separated for maximum privacy and performance:

1.  **FastAPI Backend (`helix_backend.fullstack`)**:
    *   **Unified API**: Standardized endpoints for both personality-driven chat and enterprise-grade marketing workflows.
    *   **Adaptive Inference Layer**: Intelligently routes requests between local inference (`llama-server.exe`) and cloud providers (`Groq/Llama-3.1`) based on complexity and availability.
    *   **Persistence Layer**: A resilient Supabase-integrated repository that automatically falls back to local memory if connectivity is lost.

2.  **Edge Engine Sidecar**:
    *   Uses a dedicated `llama-server.exe` to run GGUF quantized models locally on the host machine.
    *   Ensures that privacy-sensitive interactions (Privacy Mode) remain fully offline.

---

## 🤖 Integrated Agents

### 1. The Marketing Automation Agent
A full-stack automation system that handles the entire marketing lifecycle:
*   **Brand Brain**: Persists and applies unique brand voices, banned phrases, and specific vocabulary.
*   **Strategy Engine**: Generates end-to-end campaign strategies across multiple platforms (LinkedIn, X, Telegram, Discord, etc.).
*   **Variant Generation**: Autonomously writes platform-specific content variants with A/B experiment labels.
*   **Scheduler & Delivery**: Manages job queues for future posts with built-in "dry-run" safety checks and "live" platform dispatch.
*   **Recursive Optimization**: Records engagement metrics and uses them to refine future content strategies.

### 2. Conversational Personas
*   **Suzi**: A playful, flirty, and high-engagement persona.
*   **Helix**: A sharp, professional, and outcome-driven persona.
*   **RL-Layer**: A Reinforcement Learning layer tracks user sentiment and rewards, adapting response policies in real-time.

---

## 🛠️ Technical Stack & Security

*   **Frontend**: React (Vite) + Framer Motion (for ultra-premium animations) + Lucide Icons.
*   **Backend**: Python FastAPI with Pydantic schemas.
*   **Database**: Supabase (PostgreSQL) + Local SQLite for marketing state.
*   **Security**:
    *   **Fernet Encryption**: Securely encrypts third-party platform credentials (tokens/API keys) before database storage.
    *   **Token-Based Auth**: Enforces `X-API-Token` for all system communication.
    *   **Rate Limiting**: Built-in protection (100 req/min) to prevent dashboard abuse while allowing burst traffic.

---

## 🚦 System Status

*   **Endpoint**: `http://localhost:8000`
*   **Frontend Environment**: `.env` (VITE_BACKEND_URL)
*   **Streaming Protocol**: Dedicated SSE (Server-Sent Events) with custom JSON-line payloads.

---
*Created by the Google Deepmind Team - Advanced Agentic Coding.*
