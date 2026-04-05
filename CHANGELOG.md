# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), 
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]
### Added
- Upcoming Android Edge AI prototype
- Improved routing heuristics (adaptive scoring)

---

## [1.0.0-beta] - 2026-04-05

### Added
- **Hybrid Intelligence Engine**: Dynamic real-time routing between Cloud (Groq) and local Edge (GGUF) inference layers.
- **Native Sidecar Architecture**: Integrated `llama-server` binary for robust, isolated local inference.
- **Score-Based Routing**: Intelligent query complexity evaluation (0–100 scoring heuristic).
- **Full-Stack Streaming**: SSE token delivery from both cloud and edge backends.
- **Advanced Lifecycle Management**: Auto-unload idle models (5m), manual warmup/unload hooks.
- **Production Metrics**: `/api/v1/metrics` with P95 latency and usage ratios.
- **Security Suite**: API key validation, bucket-based rate limiting, and input sanitization safeguards.
- **Response Caching**: LRU-based instant replies for frequent queries.

### Fixed
- **Deployment Resilience**: Resolved `ModuleNotFoundError` for `llama-cpp-python` via native sidecar architecture.
- **Fallback Logic**: Implemented partial mid-stream fallback from cloud to edge.
- **Path Resolution**: Fixed absolute pathing for model weights across environments.

### Changed
- **API Standard**: Migrated all endpoints to `/api/v1/` prefix.
- **Model Standard**: Migrated from ONNX to GGUF (Q4_K_M) for production.
- **Project Name**: Rebranded from "Echo" to HELIX AI.

### Removed
- Deprecated ONNX-based inference pipeline.

---

[Unreleased]: https://github.com/mlwithharsh/HELIX-AI/compare/v1.0.0-beta...HEAD
[1.0.0-beta]: https://github.com/mlwithharsh/HELIX-AI/releases/tag/v1.0.0-beta
