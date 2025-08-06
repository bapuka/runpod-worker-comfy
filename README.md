# runpod-worker-comfy

Reference: https://blib.la/blog/comfyui-on-runpod

---
```
docker rm -vf $(docker ps -aq)
docker rmi -f $(docker images -aq)
docker buildx bake -f docker-bake.hcl --push
```