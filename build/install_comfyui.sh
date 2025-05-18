#!/usr/bin/env bash
set -e

# Clone the repo
cd /
git clone --depth=1 https://github.com/comfyanonymous/ComfyUI.git 
cd ComfyUI
git checkout ${COMFYUI_VERSION}

# Create and activate the venv
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Install torch and xformers
pip3 install --no-cache-dir --force-reinstall torch=="${TORCH_VERSION}" torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip3 install --no-cache-dir xformers=="${XFORMERS_VERSION}" --index-url https://download.pytorch.org/whl/cu121

# Install requirements
pip3 install --no-cache-dir -r requirements.txt
pip3 install --no-cache-dir accelerate insightface lark compel onnxruntime-gpu bitsandbytes python-dotenv 

# Install runpod
pip3 install --no-cache-dir runpod requests huggingface_hub 

# Install ComfyUI Custom Nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager
cd custom_nodes/ComfyUI-Manager
pip3 install -r requirements.txt

cd /ComfyUI
git clone https://github.com/ntdviet/comfyui-ext.git custom_nodes/comfyui-ext
cp custom_nodes/comfyui-ext/custom_nodes/gcLatentTunnel/gcLatentTunnel.py ./custom_nodes/gcLatentTunnel.py
rm -rf custom_nodes/comfyui-ext

cd /ComfyUI
git clone --depth 1 https://github.com/rgthree/rgthree-comfy.git custom_nodes/rgthree-comfy
cd custom_nodes/rgthree-comfy 
pip3 install -r requirements.txt

cd /ComfyUI
git clone --depth 1 https://github.com/griptape-ai/ComfyUI-Griptape.git custom_nodes/ComfyUI-Griptape
cd custom_nodes/ComfyUI-Griptape 
pip3 install -r requirements.txt

cd /ComfyUI
git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Impact-Pack.git custom_nodes/ComfyUI-Impact-Pack
cd custom_nodes/ComfyUI-Impact-Pack 
pip3 install -r requirements.txt

cd /ComfyUI
git clone --depth 1 https://github.com/WASasquatch/was-node-suite-comfyui custom_nodes/was-node-suite-comfyui
cd custom_nodes/was-node-suite-comfyui 
pip3 install -r requirements.txt

cd /ComfyUI
git clone --depth 1 https://github.com/cubiq/ComfyUI_IPAdapter_plus.git custom_nodes/ComfyUI_IPAdapter_plus
git clone --depth 1 https://github.com/cubiq/ComfyUI_InstantID.git custom_nodes/ComfyUI_InstantID
cd custom_nodes/ComfyUI_InstantID 
pip3 install -r requirements.txt

cd /ComfyUI
git clone --depth 1 https://github.com/cubiq/PuLID_ComfyUI.git custom_nodes/PuLID_ComfyUI
cd custom_nodes/PuLID_ComfyUI 
pip3 install -r requirements.txt

# git clone --depth 1 https://github.com/Gourieff/comfyui-reactor-node.git custom_nodes/comfyui-reactor-node
# cd custom_nodes/comfyui-reactor-node 
# pip3 install -r requirements.txt
cd /ComfyUI
git clone --depth 1 https://github.com/Extraltodeus/ComfyUI-AutomaticCFG.git custom_nodes/ComfyUI-AutomaticCFG
cd custom_nodes/ComfyUI-AutomaticCFG 
pip3 install -r requirements.txt

cd /ComfyUI
git clone --depth 1 https://github.com/Extraltodeus/pre_cfg_comfy_nodes_for_ComfyUI.git custom_nodes/pre_cfg_comfy_nodes_for_ComfyUI
git clone --depth 1 https://github.com/crystian/ComfyUI-Crystools.git custom_nodes/ComfyUI-Crystools
cd custom_nodes/ComfyUI-Crystools 
pip3 install -r requirements.txt

cd /ComfyUI
git clone --depth 1 https://github.com/XLabs-AI/x-flux-comfyui.git custom_nodes/x-flux-comfyui
cd custom_nodes/x-flux-comfyui 
python3 setup.py

cd /ComfyUI
git clone https://github.com/shiimizu/ComfyUI_smZNodes.git custom_nodes/ComfyUI_smZNodes
git clone https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git custom_nodes/ComfyUI-Custom-Scripts
git clone https://github.com/ssitu/ComfyUI_UltimateSDUpscale.git custom_nodes/ComfyUI_UltimateSDUpscale --recursive
git clone https://github.com/shiimizu/ComfyUI-TiledDiffusion.git custom_nodes/ComfyUI-TiledDiffusion
git clone https://github.com/yolain/ComfyUI-Easy-Use.git custom_nodes/ComfyUI-Easy-Use
cd custom_nodes/ComfyUI-Easy-Use
bash ./install.sh


cd /ComfyUI
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git custom_nodes/comfyui_controlnet_aux
cd custom_nodes/comfyui_controlnet_aux 
pip3 install -r requirements.txt

echo "Downloading SDXL Refiner"
cd /ComfyUI/models/checkpoints
wget https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors

echo "Downloading SDXL VAE"
cd /ComfyUI/models/vae
wget https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors

echo "Creating log directory"
mkdir -p /logs

pip3 cache purge
deactivate
