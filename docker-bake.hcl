variable "REGISTRY" {
    default = "docker.io"
}

variable "REGISTRY_USER" {
    default = "bapuka"
}

variable "APP" {
    default = "comfyui"
}

variable "RELEASE" {
    default = "v0.3.34"
}

variable "CU_VERSION" {
    default = "121"
}

variable "BASE_IMAGE_REPOSITORY" {
    default = "ashleykza/runpod-base"
}

variable "BASE_IMAGE_VERSION" {
    default = "2.4.1"
}

variable "CUDA_VERSION" {
    default = "12.1.1"
}

variable "TORCH_VERSION" {
    default = "2.5.1"
}

variable "PYTHON_VERSION" {
    default = "3.12"
}

target "default" {
    dockerfile = "Dockerfile.runpod"
    tags = ["${REGISTRY}/${REGISTRY_USER}/${APP}:${RELEASE}.post1"]
    args = {
        RELEASE = "${RELEASE}"
        BASE_IMAGE = "${BASE_IMAGE_REPOSITORY}:${BASE_IMAGE_VERSION}-python${PYTHON_VERSION}-cuda${CUDA_VERSION}-torch${TORCH_VERSION}"
        INDEX_URL = "https://download.pytorch.org/whl/cu${CU_VERSION}"
        TORCH_VERSION = "${TORCH_VERSION}+cu${CU_VERSION}"
        XFORMERS_VERSION = "0.0.29.post1"
        COMFYUI_VERSION = "${RELEASE}"
        APP_MANAGER_VERSION = "1.2.2"
    }
    platforms = ["linux/amd64"]
}
