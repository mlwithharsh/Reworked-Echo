# CHANGELOG: HELIX AI

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-beta] - 2026-04-05
### Added
- **Hybrid Intelligence Engine**: Real-time switching between Cloud (Groq) and local Edge (GGUF).
- **Native Sidecar Architecture**: Integrated `llama-server` binary for robust, multi-platform local inference.
- **Score-Based Routing**: Intelligent query complexity evaluation (0-100 score).
- **Full-Stack Streaming**: SSE token delivery from both cloud and edge backends.
- **Advanced Lifecycle Management**: Auto-unload idle models (5m), manual warmup/unload hooks.
- **Production Metrics**: `/api/v1/metrics` with P95 latency and usage ratios.
- **Security Suite**: API Key validation, bucket rate-limiting, and input sanitization.
- **Response Caching**: LRU-based instant replies for frequent queries.

### Fixed
- **Deployment Resilience**: Resolved `ModuleNotFoundError` for `llama-cpp-python` on Windows/Linux by switching to native sidecar.
- **Fallback Logic**: Implemented "Partial Mid-Stream Fallback" from cloud to edge.
- **Path Resolution**: Fixed absolute pathing for AI weights across dev/prod environments.

### Changed
- **API Standard**: Migrated all endpoints to `/api/v1/` prefix.
- **Model Standard**: Migrated from ONNX to **GGUF (Q4_K_M)** for production.
- **Project Name**: Complete rebranding from "Echo" to **HELIX AI**.

---
[1.0.0-beta]: https://github.com/mlwithharsh/HELIX-AI/releases/tag/v1.0.0-beta
