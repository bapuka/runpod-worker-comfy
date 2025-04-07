#!/usr/bin/env bash
set -e

# Clone the repo
git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
cd /ComfyUI
git checkout ${COMFYUI_VERSION}

# Create and activate the venv
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Install torch and xformers
pip3 install --no-cache-dir --force-reinstall torch=="${TORCH_VERSION}" torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip3 install --no-cache-dir xformers=="${XFORMERS_VERSION}" --index-url https://download.pytorch.org/whl/cu121

# Install requirements
pip3 install --no-cache-dir -r requirements.txt
pip3 install --no-cache-dir accelerate insightface

# Install runpod
pip3 install --no-cache-dir runpod requests

# Install ComfyUI Custom Nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager
cd custom_nodes/ComfyUI-Manager
pip3 install -r requirements.txt

git clone https://github.com/ntdviet/comfyui-ext.git /ComfyUI/custom_nodes/comfyui-ext
cp /ComfyUI/custom_nodes/comfyui-ext/custom_nodes/gcLatentTunnel/gcLatentTunnel.py .
rm -rf comfyui-ext

git clone --depth 1 https://github.com/rgthree/rgthree-comfy.git /ComfyUI/custom_nodes/rgthree-comfy
cd /ComfyUI/custom_nodes/rgthree-comfy 
pip3 install -r requirements.txt

git clone --depth 1 https://github.com/griptape-ai/ComfyUI-Griptape.git /ComfyUI/custom_nodes/ComfyUI-Griptape
cd /ComfyUI/custom_nodes/ComfyUI-Griptape 
pip3 install -r requirements.txt

git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Impact-Pack.git /ComfyUI/custom_nodes/ComfyUI-Impact-Pack
cd /ComfyUI/custom_nodes/ComfyUI-Impact-Pack 
pip3 install -r requirements.txt

git clone --depth 1 https://github.com/WASasquatch/was-node-suite-comfyui /ComfyUI/custom_nodes/was-node-suite-comfyui
cd /ComfyUI/custom_nodes/was-node-suite-comfyui 
pip3 install -r requirements.txt

git clone --depth 1 https://github.com/cubiq/ComfyUI_IPAdapter_plus.git /ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus
git clone --depth 1 https://github.com/cubiq/ComfyUI_InstantID.git /ComfyUI/custom_nodes/ComfyUI_InstantID
cd /ComfyUI/custom_nodes/ComfyUI_InstantID 
pip3 install -r requirements.txt

git clone --depth 1 https://github.com/cubiq/PuLID_ComfyUI.git /ComfyUI/custom_nodes/PuLID_ComfyUI
cd /ComfyUI/custom_nodes/PuLID_ComfyUI 
pip3 install -r requirements.txt

# git clone --depth 1 https://github.com/Gourieff/comfyui-reactor-node.git custom_nodes/comfyui-reactor-node
# cd custom_nodes/comfyui-reactor-node 
# pip3 install -r requirements.txt

git clone --depth 1 https://github.com/Extraltodeus/ComfyUI-AutomaticCFG.git /ComfyUI/custom_nodes/ComfyUI-AutomaticCFG
cd /ComfyUI/custom_nodes/ComfyUI-AutomaticCFG 
pip3 install -r requirements.txt

git clone --depth 1 https://github.com/Extraltodeus/pre_cfg_comfy_nodes_for_ComfyUI.git /ComfyUI/custom_nodes/pre_cfg_comfy_nodes_for_ComfyUI
git clone --depth 1 https://github.com/crystian/ComfyUI-Crystools.git /ComfyUI/custom_nodes/ComfyUI-Crystools
cd /ComfyUI/custom_nodes/ComfyUI-Crystools 
pip3 install -r requirements.txt

git clone --depth 1 https://github.com/XLabs-AI/x-flux-comfyui.git /ComfyUI/custom_nodes/x-flux-comfyui
cd /ComfyUI/custom_nodes/x-flux-comfyui 
python3 setup.py

git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git /ComfyUI/custom_nodes/comfyui_controlnet_aux
cd /ComfyUI/custom_nodes/comfyui_controlnet_aux 
pip3 install -r requirements.txt

pip3 cache purge
deactivate