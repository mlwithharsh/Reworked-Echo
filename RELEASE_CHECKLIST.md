# HELIX Release Checklist

This checklist must be performed before any major, minor, or patch release to the `main` branch.

---

### 1. Functional Integrity
- [ ] **API Functional Check**: Verify `/api/v1/status` returns correct online/offline status.
- [ ] **Cloud Routing Check**: Confirm complex queries correctly route to Groq API.
- [ ] **Edge Routing Check**: Confirm simple queries or privacy-mode requests route to the local Edge engine.
- [ ] **Streaming (SSE) Check**: Verify tokens stream in real-time in the browser for both cloud and local paths.
- [ ] **Chat Persistence Check**: Confirm session history is correctly saved to Supabase/PostgreSQL.

### 2. Resilience & Performance
- [ ] **Offline Simulation**: Disable internet and verify HELIX continues to respond via the local GGUF model.
- [ ] **Fallback Logic Check**: Manually kill the `llama-server` process and verify the system automatically switches to Cloud.
- [ ] **Stress Test (20 requests)**: Run the `helix_backend/tests/edge_validation.py` suite.
- [ ] **Latency Benchmark**: Verify P95 latency is within acceptable limits (<2.5s first-token target).

### 3. Stability & Resources
- [ ] **Memory Audit**: Confirm the idle monitor unloads the GGUF model after 5 minutes of inactivity.
- [ ] **System RAM Check**: Verify maximum RAM usage doesn't exceed 1.5GB total on the host machine.
- [ ] **Input Sanitization Check**: Test the backend against long (5000+ char) and non-printable character inputs.

### 4. Code & Documentation
- [ ] **README Update**: Ensure latest API endpoints and installation steps are documented.
- [ ] **CHANGELOG Update**: Add a new entry for the current version.
- [ ] **Semantic Tagging**: Verify that the version follows MAJOR.MINOR.PATCH format.
- [ ] **Git Sync**: Ensure `dev` branch is fully merged into `main`.

---

### **Final Release Approval**
**Version**: v1.0.0-beta
**Approver**: Antigravity Agent
**Date**: 2026-04-05
