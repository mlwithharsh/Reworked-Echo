# HELIX Edge AI: Hybrid Intelligence System — Implementation & Integration Plan

This document outlines the architecture, integration plan, and performance benchmarks for the HELIX Hybrid Cloud + Edge AI system.

## 1. Hybrid Architecture Overview

HELIX now operates using a **Hybrid Intelligence System** that dynamically routes queries between a local Edge AI model (Privacy-first, Offline-capable) and a powerful Cloud-based model (Complexity-optimized).

### Key Components:
- **`ModelRouter`**: The decision engine that analyzes query complexity, network status, and user privacy settings.
- **`EdgeEngine`**: A lightweight, CPU-optimized inference layer based on `llama-cpp-python` (GGUF).
- **`NetworkChecker`**: Real-time detection of connectivity status to enable seamless offline fallback.

---

## 2. Android Integration Plan (Mobile Edge AI)

To bring HELIX's Edge AI capabilities to Android devices, we will leverage the **ONNX Runtime Mobile** and **llama.cpp JNI bindings** for efficient on-device inference.

### Implementation Steps:
1. **Model Optimization**:
   - Quantize the base model (e.g., TinyLlama-1.1B or Phi-2) to **4-bit (Q4_K_M)** using `llama.cpp` tools.
   - Target model size: **< 1.0 GB** for high compatibility across mid-range devices.
2. **Inference Engine**:
   - Use `onnxruntime-mobile` for high-performance CPU execution on Android.
   - Alternatively, integrate `llama-android-cpp` as a native library for direct GGUF support.
3. **Background Lifecycle**:
   - Implement **Lazy Loading** to ensure the model only consumes RAM when the user starts a session.
   - Use Android **Foreground Services** if background processing is required to prevent OS-level termination.
4. **Offline Sync**:
   - Implement a message queue that buffers local interactions while offline.
   - Automatically sync to Supabase once the device regains internet connectivity using a `ConnectivityManager` listener.

---

## 3. Performance Benchmarks (Estimated)

*Based on hardware with 8GB RAM and 4+ CPU Cores*

| Metric | Edge AI (Local) | Cloud AI (Groq/API) |
| :--- | :--- | :--- |
| **First Token Latency** | ~200ms - 500ms | ~400ms - 1.2s |
| **Token Generation Rate** | ~10 - 20 tokens/sec | ~50+ tokens/sec |
| **Memory Usage (RAM)** | ~800MB - 1.2GB | < 100MB |
| **Reliability** | 100% (No Internet needed) | ~98% (Network dependent) |
| **Privacy Tier** | Maximum (On-device Only) | Standard (SSL Encrypted) |

### Performance Optimization Strategies:
- **Quantization**: Always use 4-bit or 8-bit quantized models to fit within the 8GB RAM target.
- **KV Cache**: Persist the key-value cache between turns to reduce "First Token Latency" in long conversations.
- **Model Switching**: Only load the local model into memory if the router predicts it will be needed (e.g., simple queries) or if the device is offline.

---

## 4. Privacy & Offline Controls

Users can now control their AI processing via the Chat UI:
1. **Privacy Mode**: Forces all data to stay on-device. No external API calls are made, even if internet is available.
2. **Go Offline**: Forces the HELIX Router to use only the Edge AI model, simulating an offline state for testing or data-saving.

---

## 5. Next Steps
- [ ] Download and place `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` into `helix_backend/models/`.
- [ ] Install dependencies: `pip install llama-cpp-python`.
- [ ] Conduct live benchmarks on target production hardware.
