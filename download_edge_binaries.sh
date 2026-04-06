#!/bin/bash
# HELIX AI - Edge AI Binary Downloader for Linux (Render/Cloud)
# This script downloads the correct llama-server binary for Linux x64 CPU.

SET_DIR="helix_backend/edge_model"
BINARY_URL="https://github.com/ggml-org/llama.cpp/releases/download/b8672/llama-b8672-bin-ubuntu-x64.tar.gz"

echo "🚀 Preparing Edge AI binaries for Linux..."

# Create directory if not exists
mkdir -p $SET_DIR

# Download
echo "📥 Downloading llama-server from GitHub..."
curl -L $BINARY_URL -o llama_bin.tar.gz

# Extract
echo "📦 Extracting binaries..."
tar -xzf llama_bin.tar.gz -C $SET_DIR --strip-components=1

# Clean up
rm llama_bin.tar.gz

# Set permissions
chmod +x $SET_DIR/llama-server
chmod +x $SET_DIR/llama-cli

echo "✅ Edge AI binaries ready in $SET_DIR"
