# Stage 1: Base image with common dependencies
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04 as base

# Prevents prompts from packages asking for user input during installation
ENV DEBIAN_FRONTEND=noninteractive
# Prefer binary wheels over source distributions for faster pip installations
ENV PIP_PREFER_BINARY=1
# Ensures output from python is printed immediately to the terminal without buffering
ENV PYTHONUNBUFFERED=1 

# Install Python, git and other necessary tools
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget

# Impact pack deps
RUN apt-get install -y libgl1-mesa-glx libglib2.0-0

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI repository
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /comfyui

# Change working directory to ComfyUI
WORKDIR /comfyui

# Install ComfyUI dependencies
RUN pip3 install --upgrade --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 \
    && pip3 install --no-cache-dir xformers==0.0.23 --index-url https://download.pytorch.org/whl/cu121 \
    && pip3 install --upgrade -r requirements.txt

# Install runpod
RUN pip3 install runpod requests

# Install custom nodes

WORKDIR /comfyui/custom_nodes

RUN wget https://github.com/ntdviet/comfyui-ext/blob/main/custom_nodes/gcLatentTunnel/gcLatentTunnel.py
RUN git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Manager.git
RUN cd ComfyUI-Manager && pip3 install -r requirements.txt
RUN git clone --depth 1 https://github.com/rgthree/rgthree-comfy.git
RUN cd rgthree-comfy && pip3 install -r requirements.txt
RUN git clone --depth 1 https://github.com/griptape-ai/ComfyUI-Griptape.git
RUN cd ComfyUI-Griptape && pip3 install -r requirements.txt
RUN git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Impact-Pack.git
RUN cd ComfyUI-Impact-Pack && pip3 install -r requirements.txt
RUN git clone https://github.com/WASasquatch/was-node-suite-comfyui
RUN cd was-node-suite-comfyui && pip3 install -r requirements.txt
RUN git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
RUN cd ComfyUI_IPAdapter_plus && pip3 install -r requirements.txt
RUN git clone https://github.com/cubiq/ComfyUI_InstantID.git
RUN cd ComfyUI_InstantID && pip3 install -r requirements.txt
RUN git clone https://github.com/cubiq/PuLID_ComfyUI.git
RUN cd PuLID_ComfyUI && pip3 install -r requirements.txt
RUN git clone https://github.com/Gourieff/comfyui-reactor-node.git
RUN cd comfyui-reactor-node && pip3 install -r requirements.txt
RUN git clone https://github.com/Extraltodeus/ComfyUI-AutomaticCFG.git
RUN cd ComfyUI-AutomaticCFG && pip3 install -r requirements.txt
RUN git clone https://github.com/Extraltodeus/pre_cfg_comfy_nodes_for_ComfyUI.git
RUN cd pre_cfg_comfy_nodes_for_ComfyUI && pip3 install -r requirements.txt
RUN git clone https://github.com/rgthree/rgthree-comfy.git
RUN cd rgthree-comfy.git && pip3 install -r requirements.txt
RUN git clone https://github.com/crystian/ComfyUI-Crystools.git
RUN cd ComfyUI-Crystools && pip3 install -r requirements.txt

WORKDIR /comfyui

# Support for the network volume
ADD src/extra_model_paths.yaml ./

# Go back to the root
WORKDIR /

# Add the start and the handler
ADD src/start.sh src/rp_handler.py test_input.json ./
RUN chmod +x /start.sh

# # Stage 2: Download models
# FROM base as downloader

# ARG HUGGINGFACE_ACCESS_TOKEN
# ARG MODEL_TYPE

# Change working directory to ComfyUI
# WORKDIR /comfyui

# Download checkpoints/vae/LoRA to include in image based on model type
# RUN if [ "$MODEL_TYPE" = "sdxl" ]; then \
#       wget -O models/checkpoints/sd_xl_base_1.0.safetensors https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors && \
#       wget -O models/vae/sdxl_vae.safetensors https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors && \
#       wget -O models/vae/sdxl-vae-fp16-fix.safetensors https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors; \
#       git clone https://github.com/rgthree/rgthree-comfy.git custom_nodes/rgthree-comfy; \

#     elif [ "$MODEL_TYPE" = "sd3" ]; then \
#       wget --header="Authorization: Bearer ${HUGGINGFACE_ACCESS_TOKEN}" -O models/checkpoints/sd3_medium_incl_clips_t5xxlfp8.safetensors https://huggingface.co/stabilityai/stable-diffusion-3-medium/resolve/main/sd3_medium_incl_clips_t5xxlfp8.safetensors; \
#     fi

# Stage 3: Final image
# FROM base as final

# Copy models from stage 2 to the final image
# COPY --from=downloader /comfyui/models /comfyui/models

# Start the container
CMD /start.sh