#!/usr/bin/env bash

# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true
export HF_HOME="/"

# Set environment
# Debug: List directory structure to help diagnose path issues
echo "runpod-worker-comfy: Listing root directory structure"
ls -la /
echo "runpod-worker-comfy: Listing workspace directory"
ls -la /workspace
echo "runpod-worker-comfy: Listing network volume directory"
ls -la /runpod-volume
echo "runpod-worker-comfy: Listing workflows directory"
ls -la /workflows

# Ensure workflows are accessible from the expected location
echo "runpod-worker-comfy: Setting up workflows directory"

# First try to create a symlink
if [ ! -d "./workflows" ] && [ -d "/workflows" ]; then
    ln -sf /workflows ./workflows
    echo "runpod-worker-comfy: Symlink created successfully"
    ls -la ./workflows
else
    echo "runpod-worker-comfy: Symlink not needed or couldn't be created"
    
    # If symlink didn't work, try to create the directory and copy files
    if [ ! -d "./workflows" ]; then
        echo "runpod-worker-comfy: Creating workflows directory"
        mkdir -p ./workflows
    fi
    
    # Copy workflow files from possible locations
    if [ -d "/workflows" ]; then
        echo "runpod-worker-comfy: Copying workflow files from /workflows"
        cp -f /workflows/*.json ./workflows/ 2>/dev/null || echo "No JSON files found in /workflows"
    fi
    
    if [ -d "/src/workflows" ]; then
        echo "runpod-worker-comfy: Copying workflow files from /src/workflows"
        cp -f /src/workflows/*.json ./workflows/ 2>/dev/null || echo "No JSON files found in /src/workflows"
    fi
    
    # List the contents of the workflows directory
    echo "runpod-worker-comfy: Contents of ./workflows directory:"
    ls -la ./workflows
fi

# Create a specific copy of the img2imgPersona.json file if it exists in src/workflows
if [ -f "/src/workflows/img2imgPersona.json" ]; then
    echo "runpod-worker-comfy: Copying img2imgPersona.json from /src/workflows"
    cp -f /src/workflows/img2imgPersona.json ./workflows/
fi

# Serve the API and don't shutdown the container
if [ "$SERVE_API_LOCALLY" == "true" ]; then
    echo "runpod-worker-comfy: Starting local ComfyUI"
    cd /ComfyUI
    source venv/bin/activate
    python3 main.py --disable-auto-launch --disable-metadata --listen --port 3001 > /logs/comfyui.log 2>&1 &
    # deactivate
    
    echo "runpod-worker-comfy: Starting RunPod Handler"
    python3 -u /rp_handler.py --rp_serve_api --rp_api_host=0.0.0.0
else
    echo "runpod-worker-comfy: Starting ComfyUI"    
    cd /runpod-volume/ComfyUI
    export PYTHONPATH="/runpod-volume/ComfyUI/venv/lib/python3.11/site-packages:$PYTHONPATH"
    source venv/bin/activate 
    echo "VIRTUAL_ENV: $VIRTUAL_ENV"
    echo "Python path: $(which python)"
    echo "Pip list:"
    pip list | head -5
    python -c "import runpod; print('runpod imported successfully')"
    pip list | grep runpod > /dev/null || pip install -U runpod
    python main.py --disable-auto-launch --disable-metadata --listen --port 3001 > /logs/comfyui.log 2>&1 &
    echo "runpod-worker-comfy: Starting RunPod Handler"
    python -u /rp_handler.py
fi

# Test handler for development
# def test_handler():
#     """Test the handler locally"""
#     print("=== Testing ComfyUI Handler ===")
    
#     # Test system info
#     print("\nSystem Info:")
#     info = get_comfyui_info()
#     for key, value in info.items():
#         print(f"  {key}: {value}")
    
#     # Test basic workflow (you'd replace this with a real workflow)
#     test_event = {
#         "input": {
#             "workflow": {},  # Add your test workflow here
#             "output_format": "base64"
#         }
#     }
    
#     print("\nTesting workflow execution...")
#     # Uncomment to test with real workflow
#     # result = handler(test_event)
#     # print(f"Result: {result['status']}")
    
#     print("Handler test complete!")

# test_handler()
echo "Start script(s) finished, pod is ready to use."
sleep infinity
