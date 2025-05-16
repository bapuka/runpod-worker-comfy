import os
import random
import sys
from typing import Sequence, Mapping, Any, Union
import torch


def get_value_at_index(obj: Union[Sequence, Mapping], index: int) -> Any:
    """Returns the value at the given index of a sequence or mapping.

    If the object is a sequence (like list or string), returns the value at the given index.
    If the object is a mapping (like a dictionary), returns the value at the index-th key.

    Some return a dictionary, in these cases, we look for the "results" key

    Args:
        obj (Union[Sequence, Mapping]): The object to retrieve the value from.
        index (int): The index of the value to retrieve.

    Returns:
        Any: The value at the given index.

    Raises:
        IndexError: If the index is out of bounds for the object and the object is not a mapping.
    """
    try:
        return obj[index]
    except KeyError:
        return obj["result"][index]


def find_path(name: str, path: str = None) -> str:
    """
    Recursively looks at parent folders starting from the given path until it finds the given name.
    Returns the path as a Path object if found, or None otherwise.
    """
    # If no path is given, use the current working directory
    if path is None:
        path = os.getcwd()

    # Check if the current directory contains the name
    if name in os.listdir(path):
        path_name = os.path.join(path, name)
        print(f"{name} found: {path_name}")
        return path_name

    # Get the parent directory
    parent_directory = os.path.dirname(path)

    # If the parent directory is the same as the current directory, we've reached the root and stop the search
    if parent_directory == path:
        return None

    # Recursively call the function with the parent directory
    return find_path(name, parent_directory)


def add_comfyui_directory_to_sys_path() -> None:
    """
    Add 'ComfyUI' to the sys.path
    """
    comfyui_path = find_path("ComfyUI")
    if comfyui_path is not None and os.path.isdir(comfyui_path):
        sys.path.append(comfyui_path)
        print(f"'{comfyui_path}' added to sys.path")


def add_extra_model_paths() -> None:
    """
    Parse the optional extra_model_paths.yaml file and add the parsed paths to the sys.path.
    """
    try:
        from main import load_extra_path_config
    except ImportError:
        print(
            "Could not import load_extra_path_config from main.py. Looking in utils.extra_config instead."
        )
        from utils.extra_config import load_extra_path_config

    extra_model_paths = find_path("extra_model_paths.yaml")

    if extra_model_paths is not None:
        load_extra_path_config(extra_model_paths)
    else:
        print("Could not find the extra_model_paths config file.")


add_comfyui_directory_to_sys_path()
add_extra_model_paths()


def import_custom_nodes() -> None:
    """Find all custom nodes in the custom_nodes folder and add those node objects to NODE_CLASS_MAPPINGS

    This function sets up a new asyncio event loop, initializes the PromptServer,
    creates a PromptQueue, and initializes the custom nodes.
    """
    import asyncio
    import execution
    from nodes import init_extra_nodes
    import server

    # Creating a new event loop and setting it as the default loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Creating an instance of PromptServer with the loop
    server_instance = server.PromptServer(loop)
    execution.PromptQueue(server_instance)

    # Initializing custom nodes
    init_extra_nodes()


from nodes import NODE_CLASS_MAPPINGS


def queue(image="", scale=2):
    import subprocess
    result = subprocess.run(['source', '/ComfyUI/venv/bin/activate'], shell=True, check=True)
    
    import_custom_nodes()
    with torch.inference_mode():
        upscalemodelloader = NODE_CLASS_MAPPINGS["UpscaleModelLoader"]()
        upscalemodelloader_3 = upscalemodelloader.load_model(
            model_name="4x-UltraSharp.pth"
        )

        checkpointloadersimple = NODE_CLASS_MAPPINGS["CheckpointLoaderSimple"]()
        checkpointloadersimple_7 = checkpointloadersimple.load_checkpoint(
            ckpt_name="sdxl/CHEYENNE_v18.safetensors"
        )

        cliptextencode = NODE_CLASS_MAPPINGS["CLIPTextEncode"]()
        cliptextencode_8 = cliptextencode.encode(
            text="an award-winning, ultra high quality model, masterpiece, sharp focus, 8k, HD, HDR, XDR, focus + sharpen + wide-angle 8K resolution + HDR10 Ken Burns effect + Adobe Lightroom + rule-of-thirds + high-detailed bark. Canon EOS 5D Mark III, 1/160s, f/8, ISO 100. The resulting image is a masterpiece, extremely detailed, UHD , cinematic lighting, volumetric lighting, Film grain, cinematic film still, shallow depth of field, highly detailed,",
            clip=get_value_at_index(checkpointloadersimple_7, 1),
        )

        cliptextencode_9 = cliptextencode.encode(
            text="blurry, malformed, low quality, worst quality, artifacts, noise, text, watermark, glitch, deformed, ugly, horror, ill",
            clip=get_value_at_index(checkpointloadersimple_7, 1),
        )

        loadimage = NODE_CLASS_MAPPINGS["LoadImage"]()
        loadimage_10 = loadimage.load_image(image=image)

        automatic_cfg = NODE_CLASS_MAPPINGS["Automatic CFG"]()
        ultimatesdupscale = NODE_CLASS_MAPPINGS["UltimateSDUpscale"]()
        # image_comparer_rgthree = NODE_CLASS_MAPPINGS["Image Comparer (rgthree)"]()
        saveimage = NODE_CLASS_MAPPINGS["SaveImage"]()

        for q in range(1):
            automatic_cfg_1 = automatic_cfg.patch(
                hard_mode=True,
                boost=True,
                model=get_value_at_index(checkpointloadersimple_7, 0),
            )

            ultimatesdupscale_2 = ultimatesdupscale.upscale(
                upscale_by=scale,
                seed=random.randint(1, 2**64),
                steps=20,
                cfg=8,
                sampler_name="dpmpp_2m_sde_gpu",
                scheduler="karras",
                denoise=0.14,
                mode_type="Linear",
                tile_width=512,
                tile_height=512,
                mask_blur=8,
                tile_padding=32,
                seam_fix_mode="None",
                seam_fix_denoise=1,
                seam_fix_width=64,
                seam_fix_mask_blur=8,
                seam_fix_padding=16,
                force_uniform_tiles=True,
                tiled_decode=False,
                image=get_value_at_index(loadimage_10, 0),
                model=get_value_at_index(automatic_cfg_1, 0),
                positive=get_value_at_index(cliptextencode_8, 0),
                negative=get_value_at_index(cliptextencode_9, 0),
                vae=get_value_at_index(checkpointloadersimple_7, 2),
                upscale_model=get_value_at_index(upscalemodelloader_3, 0),
            )

            # image_comparer_rgthree_11 = image_comparer_rgthree.compare_images(
            #     image_a=get_value_at_index(loadimage_10, 0),
            #     image_b=get_value_at_index(ultimatesdupscale_2, 0),
            # )

            saveimage_13 = saveimage.save_images(
                filename_prefix="ComfyUI",
                images=get_value_at_index(ultimatesdupscale_2, 0),
            )
            
            return get_value_at_index(ultimatesdupscale_2, 0)


# if __name__ == "__main__":
#     main()
