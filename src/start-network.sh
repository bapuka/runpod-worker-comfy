#!/usr/bin/env bash
set -e
# Use libtcmalloc for better memory management
TCMALLOC="$(ldconfig -p | grep -Po "libtcmalloc.so.\d" | head -n 1)"
export LD_PRELOAD="${TCMALLOC}"
export PYTHONUNBUFFERED=true
export HF_HOME="/"

ln -sfn "/runpod-volume/miniconda3" "/workspace/miniconda3"
ln -sfn "/runpod-volume/logs" "/logs"

# Set environment
# Debug: List directory structure to help diagnose path issues
echo "runpod-worker-comfy: Listing root directory structure"
ls -la /
echo "runpod-worker-comfy: Listing workspace directory"
ls -la /workspace
echo "runpod-worker-comfy: Listing network volume directory"
ls -la /runpod-volume
echo "runpod-worker-comfy: Listing conda directory"
ls -la /runpod-volume/miniconda3/etc/profile.d
echo "runpod-worker-comfy: Listing workflows directory"
ls -la /workflows

# # Configuration
# COMFYUI_NETWORK_PATH="/runpod-volume/ComfyUI"
# # VENV_PATH="${COMFYUI_NETWORK_PATH}/venv"
# CONTAINER_COMFYUI_PATH="/ComfyUI"

# # --- Pre-flight Checks ---
# # echo "Checking for ComfyUI installation on network storage..."
# # if [ ! -d "$COMFYUI_NETWORK_PATH" ]; then
# #     echo "ERROR: ComfyUI directory not found at $COMFYUI_NETWORK_PATH."
# #     echo "Please ensure your ComfyUI installation is at the root of your network storage, under a folder named 'comfyui'."
# #     exit 1
# # fi

# # echo "Checking for ComfyUI virtual environment..."
# # if [ ! -d "$VENV_PATH" ]; then
# #     echo "ERROR: Virtual environment not found at $VENV_PATH."
# #     echo "Please ensure your venv is located at $COMFYUI_NETWORK_PATH/venv."
# #     exit 1
# # fi

# # --- Setup ---
# echo "Creating a symbolic link to ComfyUI from network storage..."
# # We create a symlink so ComfyUI thinks it's in /comfyui within the container.
# # This avoids copying large files and uses the existing installation directly.
# ln -sfn "$COMFYUI_NETWORK_PATH" "$CONTAINER_COMFYUI_PATH"

# echo "Activating ComfyUI's virtual environment..."
# source /workspace/miniconda3/bin/activate
# conda activate comfyui
# # source "${VENV_PATH}/bin/activate"
# echo "Pip list:"
# pip list | head -15
# --- ComfyUI Specific Setup (Optional but Recommended) ---
# Set paths for models and custom nodes if they are also on network storage
# This assumes your models are in /runpod-volume/comfyui/models (standard location)
# If your models are in a different location on network storage, adjust these paths.
# For example, if you have a shared models folder at /runpod-volume/models_shared
# then set these env vars accordingly.
# export COMFYUI_ROOT="$CONTAINER_COMFYUI_PATH"
# export COMFYUI_OUTPUT_DIR="${CONTAINER_COMFYUI_PATH}/output" # Or your desired output directory
# export COMFYUI_TEMP_DIR="${CONTAINER_COMFYUI_PATH}/temp"

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
    echo "Starting RunPod Serverless setup..."

    # 1. Source the Conda initialization script
    # This is crucial for making the `conda` command available and initializing the base environment.
    # Make sure this path is correct for your Miniconda installation on network storage.
    echo "Sourcing Conda initialization..."
    chmod a+x /runpod-volume/miniconda3/etc/profile.d/conda.sh
    source /runpod-volume/miniconda3/etc/profile.d/conda.sh

    # 2. Activate your specific Conda environment for ComfyUI
    echo "Activating 'comfyui' Conda environment..."
    conda activate comfyui

    # 3. Navigate to your ComfyUI directory on network storage
    echo "Navigating to ComfyUI directory..."
    cd /runpod-volume/ComfyUI

    # export VIRTUAL_ENV="/runpod-volum e/ComfyUI/venv"
    echo "runpod-worker-comfy: Starting ComfyUI"    
    # cd /runpod-volume/ComfyUI
    # export PYTHONPATH="/runpod-volume/ComfyUI/venv/lib/python3.11/site-packages:$PYTHONPATH"
    # source venv/bin/activate 
    # cd "$CONTAINER_COMFYUI_PATH"
    # echo "VIRTUAL_ENV: $VIRTUAL_ENV"
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
