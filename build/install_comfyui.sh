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
pip3 install --no-cache-dir protobuf --upgrade 

# Install runpod
pip3 install --no-cache-dir runpod requests huggingface_hub 

# git lfs install
# git clone --depth 1 https://huggingface.co/kidyu/antelopev2-for-InstantID-ComfyUI /ComfyUI/models/insightface/models/antelopev2

# wget https://huggingface.co/netrunner-exe/Insight-Swap-models/resolve/main/inswapper_128.fp16.onnx -O /ComfyUI/models/insightface/inswapper_128.fp16.onnx
# wget https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx -O /ComfyUI/models/insightface/inswapper_128.onnx

# Install ComfyUI Custom Nodes
# git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager
# cd custom_nodes/ComfyUI-Manager
# pip3 install -r requirements.txt

cd /ComfyUI
git clone https://github.com/ntdviet/comfyui-ext.git custom_nodes/comfyui-ext
cp custom_nodes/comfyui-ext/custom_nodes/gcLatentTunnel/gcLatentTunnel.py ./custom_nodes/gcLatentTunnel.py
rm -rf custom_nodes/comfyui-ext

cd /ComfyUI
git clone --depth 1 https://github.com/rgthree/rgthree-comfy.git custom_nodes/rgthree-comfy
cd custom_nodes/rgthree-comfy 
pip3 install -r requirements.txt

# cd /ComfyUI
# git clone --depth 1 https://github.com/griptape-ai/ComfyUI-Griptape.git custom_nodes/ComfyUI-Griptape
# cd custom_nodes/ComfyUI-Griptape 
# pip3 install -r requirements.txt

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
# Temporarily disable exit on error for this problematic section
set +e
echo "Cloning ComfyUI-Easy-Use..."
if git clone https://github.com/yolain/ComfyUI-Easy-Use.git custom_nodes/ComfyUI-Easy-Use; then
    cd custom_nodes/ComfyUI-Easy-Use
    echo "Attempting to install ComfyUI-Easy-Use..."
    if bash ./install.sh; then
        echo "ComfyUI-Easy-Use installation completed successfully"
    else
        echo "WARNING: ComfyUI-Easy-Use installation script failed with exit code $?, but continuing with the build"
    fi
    cd /ComfyUI
else
    echo "WARNING: Failed to clone ComfyUI-Easy-Use repository, but continuing with the build"
fi
# Re-enable exit on error
set -e


cd /ComfyUI
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git custom_nodes/comfyui_controlnet_aux
cd custom_nodes/comfyui_controlnet_aux 
pip3 install -r requirements.txt

# Temporarily disable exit on error for model downloads
set +e

echo "Downloading SDXL Refiner"
cd /ComfyUI/models/checkpoints
if wget https://civitai.com/api/download/models/656688 --content-disposition -O CHEYENNE_v18.safetensors; then
    echo "CHEYENNE_v18 downloaded successfully"
else 
    echo "WARNING: Failed to download CHEYENNE_v18, but continuing with the build"
fi

cd /ComfyUI/models/loras
if wget https://civitai.com/api/download/models/436121?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O add_details_xl.safetensors; then
    echo "add_details_xl lora downloaded successfully"
else
    echo "WARNING: Failed to download add_details_xl lora, but continuing with the build"
fi

if wget wget https://civitai.com/api/download/models/723149?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O aidmaMidjourneyV6.1-v0.1.safetensors; then
    echo "aidmaMidjourneyV6.1-v0.1 lora downloaded successfully"
else
    echo "WARNING: Failed to download aidmaMidjourneyV6.1-v0.1 lora, but continuing with the build"
fi

if wget https://civitai.com/api/download/models/413566?token=e7522ef2981c6950569b9ee98de0af15  --content-disposition -O sss-000009.safetensors; then
    echo "Translucent-Subsurface-Scattering lora downloaded successfully"
else
    echo "WARNING: Failed to download Translucent-Subsurface-Scattering lora, but continuing with the build"
fi

if wget https://civitai.com/api/download/models/430643?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O SDXL-vanta-black_contrast_V3.0.safetensors; then
    echo "SDXL-vanta-black_contrast_V3.0 lora downloaded successfully"
else
    echo "WARNING: Failed to download SDXL-vanta-black_contrast_V3.0 lora, but continuing with the build"
fi

if wget https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid_sdxl_lora.safetensors?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip-adapter-faceid_sdxl_lora.safetensors; then
    echo "ip-adapter-faceid_sdxl_lora downloaded successfully"
else
    echo "WARNING: Failed to download ip-adapter-faceid_sdxl_lora, but continuing with the build"
fi

if wget https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sdxl_lora.safetensors?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip-adapter-faceid-plusv2_sdxl_lora.safetensors; then
    echo "ip-adapter-faceid-plusv2_sdxl_lora downloaded successfully"
else
    echo "WARNING: Failed to download ip-adapter-faceid-plusv2_sdxl_lora, but continuing with the build"
fi

cd /ComfyUI/models/clip_vision
if wget https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors; then
    echo "CLIP-ViT-H-14-laion2B-s32B-b79K downloaded successfully"
else
    echo "WARNING: Failed to download CLIP-ViT-H-14-laion2B-s32B-b79K, but continuing with the build"
fi

cd /ComfyUI/models/ipadapter
if wget https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter_sdxl_vit-h.safetensors?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip-adapter_sdxl_vit-h.safetensors; then
    echo "ip-adapter_sdxl_vit-h downloaded successfully"
else
    echo "WARNING: Failed to download ip-adapter_sdxl_vit-h, but continuing with the build"
fi

if wget https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip-adapter-plus_sdxl_vit-h.safetensors; then
    echo "ip-adapter-plus_sdxl_vit-h downloaded successfully"
else
    echo "WARNING: Failed to download ip-adapter-plus_sdxl_vit-h, but continuing with the build"
fi

if wget https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip-adapter-plus-face_sdxl_vit-h.safetensors; then
    echo "ip-adapter-plus-face_sdxl_vit-h downloaded successfully"
else
    echo "WARNING: Failed to download ip-adapter-plus-face_sdxl_vit-h, but continuing with the build"
fi

if wget https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter_sdxl.safetensors?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip-adapter_sdxl.safetensors; then
    echo "ip-adapter_sdxl downloaded successfully"
else
    echo "WARNING: Failed to download ip-adapter_sdxl, but continuing with the build"
fi

if wget https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sdxl.bin?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip-adapter-faceid-plusv2_sdxl.bin; then
    echo "ip-adapter-faceid-plusv2_sdxl downloaded successfully"
else
    echo "WARNING: Failed to download ip-adapter-faceid-plusv2_sdxl, but continuing with the build"
fi

if wget https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-portrait_sdxl.bin?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip-adapter-faceid-portrait_sdxl.bin; then
    echo "ip-adapter-faceid-portrait_sdxl downloaded successfully"
else
    echo "WARNING: Failed to download ip-adapter-faceid-portrait_sdxl, but continuing with the build"
fi

if wget https://huggingface.co/ostris/ip-composition-adapter/blob/main/ip_plus_composition_sdxl.safetensors?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip_plus_composition_sdxl.safetensors; then
    echo "ip_plus_composition_sdxl downloaded successfully"
else
    echo "WARNING: Failed to download ip_plus_composition_sdxl, but continuing with the build"
fi

if wget https://huggingface.co/Kwai-Kolors/Kolors-IP-Adapter-Plus/resolve/main/ip_adapter_plus_general.bin?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O ip_adapter_plus_general.bin; then
    echo "ip_adapter_plus_general downloaded successfully"
else
    echo "WARNING: Failed to download ip_adapter_plus_general, but continuing with the build"
fi

cd /ComfyUI/models/insightface/models
if wget https://huggingface.co/public-data/insightface/resolve/main/models/buffalo_l.zip?token=e7522ef2981c6950569b9ee98de0af15 --content-disposition -O buffalo_l.zip; then
    echo "buffalo_l model downloaded successfully"
else
    echo "WARNING: Failed to download buffalo_l model, but continuing with the build"
fi

cd /ComfyUI/models/sams
if wget https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth; then
    echo "SAM model downloaded successfully"
else
    echo "WARNING: Failed to download SAM model, but continuing with the build"
fi

# if wget https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors; then
#     echo "SDXL Refiner downloaded successfully"
# else
#     echo "WARNING: Failed to download SDXL Refiner, but continuing with the build"
# fi

echo "Downloading SDXL VAE"
cd /ComfyUI/models/vae
if wget https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors; then
    echo "SDXL VAE downloaded successfully"
else
    echo "WARNING: Failed to download SDXL VAE, but continuing with the build"
fi

# Re-enable exit on error
set -e

echo "Creating log directory"
mkdir -p /logs

pip3 cache purge
deactivate
