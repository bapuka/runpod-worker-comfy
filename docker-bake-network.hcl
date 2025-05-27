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
    default = "v0.3.5"
}

target "default" {
    dockerfile = "Dockerfile.network"
    tags = ["${REGISTRY}/${REGISTRY_USER}/${APP}:${RELEASE}-network.post1"]
    args = {
        RELEASE = "${RELEASE}"        
    }
    platforms = ["linux/amd64"]
}
