#!/usr/bin/env bash

# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true
export HF_HOME="/"

# Serve the API and don't shutdown the container
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    echo "runpod-worker-comfy: Starting local ComfyUI"
    cd /ComfyUI
    source venv/bin/activate
    python3 main.py --disable-auto-launch --disable-metadata --listen --port 3001 > /logs/comfyui.log 2>&1 &
    deactivate
    
    echo "runpod-worker-comfy: Starting RunPod Handler"
    python3 -u /rp_handler.py --rp_serve_api --rp_api_host=0.0.0.0
else
    echo "runpod-worker-comfy: Starting ComfyUI"    
    cd /ComfyUI
    source venv/bin/activate
    python3 main.py --disable-auto-launch --disable-metadata --listen --port 3001 > /logs/comfyui.log 2>&1 &
    deactivate
    
    echo "runpod-worker-comfy: Starting RunPod Handler"
    python3 -u /rp_handler.py
fi