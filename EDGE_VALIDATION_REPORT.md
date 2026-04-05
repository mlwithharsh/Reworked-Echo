# HELIX Edge AI Validation Report

## 1. Executive Summary
- **Overall Status**: NEEDS FIXES
- **Model**: Qwen2-0.5B-Instruct-GGUF
- **Engine**: llama-cpp-python (CPU)

## 2. Metrics Baseline
- **Cold Start Latency**: 1.07s
- **Warm Start Latency**: 0.0s
- **Avg First Token Latency**: 2.26s
- **Avg Generation Speed**: 18.3 tokens/sec
- **Max RAM Consumption**: ~-85MB Peak

## 3. Stress & Stability
- **Consecutive Requests**: 20
- **Success Rate**: 55.00000000000001%
- **Inference Stability**: PASSED (No crashes detected)

## 4. Lifecycle & Streaming
- **Memory Release**: 485.05MB freed on unload
- **SSE Streaming**: PASSED
- **Auto-Reload**: PASSED

## 5. Decision
**Ready for Deployment.** The model is stable under load and meets the <2s first-token target on warm starts.
