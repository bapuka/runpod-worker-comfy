import runpod
from runpod.serverless.utils.rp_validator import validate
from runpod.serverless.utils import rp_upload
from runpod.serverless.modules.rp_logger import RunPodLogger
from requests.adapters import HTTPAdapter, Retry
from schemas.input import INPUT_SCHEMA
import logging
import logging.handlers
import json
import urllib.request
import urllib.parse
import time
import traceback
import os
import requests
import base64
from io import BytesIO
from PIL import Image
import re
from collections import defaultdict

# Time to wait between API check attempts in milliseconds
COMFY_API_AVAILABLE_INTERVAL_MS = 50
# Maximum number of API check attempts
COMFY_API_AVAILABLE_MAX_RETRIES = 500
# Time to wait between poll attempts in milliseconds
COMFY_POLLING_INTERVAL_MS = os.environ.get("COMFY_POLLING_INTERVAL_MS", 250)
# Maximum number of poll attempts
COMFY_POLLING_MAX_RETRIES = os.environ.get("COMFY_POLLING_MAX_RETRIES", 500)
# Host where ComfyUI is running
COMFY_HOST = "127.0.0.1:3001"
# Enforce a clean state after each job is done
# see https://docs.runpod.io/docs/handler-additional-controls#refresh-worker
REFRESH_WORKER = os.environ.get("REFRESH_WORKER", "false").lower() == "true"

# Dictionary to store uploaded images by batchId
# Structure: {batchId: {"original_name": "updated_name"}}
batch_uploaded_images = defaultdict(dict)

# Dictionary to track active batch processing
# Structure: {batchId: {"status": "processing|completed", "last_activity": timestamp, "prompt_ids": [list of prompt_ids]}}
active_batches = {}

# Time in seconds after which a batch is considered inactive (default: 10 minutes)
BATCH_TIMEOUT = 600

BASE_URI = f'http://{COMFY_HOST}'
VOLUME_MOUNT_PATH = '/runpod-volume'
LOG_FILE= 'comfyui-worker.log'
LOG_LEVEL = 'INFO'
TIMEOUT = 600

def is_batch_active(batch_id):
    """
    Check if a batch is currently active and not timed out.
    
    Args:
        batch_id (str): The batch ID to check
        
    Returns:
        bool: True if the batch is active, False otherwise
    """
    # Handle case where batch_id is "undefined" or None or empty
    if not batch_id or batch_id == "undefined" or batch_id not in active_batches:
        return False
        
    batch_info = active_batches[batch_id]
    current_time = time.time()
    
    # Check if the batch has timed out
    if current_time - batch_info['last_activity'] > BATCH_TIMEOUT:
        # Batch has timed out, remove it from active batches
        del active_batches[batch_id]
        return False
        
    return batch_info['status'] == 'processing'

def update_batch_status(batch_id, status, prompt_id=None):
    """
    Update the status of a batch.
    
    Args:
        batch_id (str): The batch ID to update
        status (str): The new status ('processing' or 'completed')
        prompt_id (str, optional): The prompt ID to add to the batch's prompt_ids list
    """
    # Handle case where batch_id is "undefined" or None or empty
    if not batch_id or batch_id == "undefined":
        return
        
    current_time = time.time()
    
    if batch_id not in active_batches:
        active_batches[batch_id] = {
            'status': status,
            'last_activity': current_time,
            'prompt_ids': []
        }
    else:
        active_batches[batch_id]['status'] = status
        active_batches[batch_id]['last_activity'] = current_time
        
    if prompt_id and batch_id in active_batches:
        if 'prompt_ids' not in active_batches[batch_id]:
            active_batches[batch_id]['prompt_ids'] = []
        active_batches[batch_id]['prompt_ids'].append(prompt_id)

def clean_inactive_batches():
    """
    Clean up inactive batches that have timed out.
    """
    current_time = time.time()
    batch_ids_to_remove = []
    
    for batch_id, batch_info in active_batches.items():
        if current_time - batch_info['last_activity'] > BATCH_TIMEOUT:
            batch_ids_to_remove.append(batch_id)
            
    for batch_id in batch_ids_to_remove:
        del active_batches[batch_id]

session = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[502, 503, 504])
session.mount('http://', HTTPAdapter(max_retries=retries))
rp_logger = RunPodLogger()

def send_get_request(endpoint):
    return session.get(
        url=f'{BASE_URI}/{endpoint}',
        timeout=TIMEOUT
    )


def send_post_request(endpoint, payload):
    return session.post(
        url=f'{BASE_URI}/{endpoint}',
        json=payload,
        timeout=TIMEOUT
    )

def wait_for_service(url):
    retries = 0

    while True:
        try:
            requests.get(url)
            return
        except requests.exceptions.RequestException:
            retries += 1

            # Only log every 15 retries so the logs don't get spammed
            if retries % 15 == 0:
                rp_logger.info('Service not ready yet. Retrying...', url)
        except Exception as err:
            rp_logger.error(f'Error: {err}')

        time.sleep(0.2)


def validate_input(job_input):
    """
    Validates the input for the handler function.

    Args:
        job_input (dict): The input data to validate.

    Returns:
        tuple: A tuple containing the validated data and an error message, if any.
               The structure is (validated_data, error_message).
    """
    # Validate if job_input is provided
    if job_input is None:
        return None, "Please provide input"

    # Check if input is a string and try to parse it as JSON
    if isinstance(job_input, str):
        try:
            job_input = json.loads(job_input)
        except json.JSONDecodeError:
            return None, "Invalid JSON format in input"

    # Validate 'workflow' in input
    workflow = job_input.get("workflow")
    if workflow is None:
        return None, "Missing 'workflow' parameter"

    # Validate 'images' in input, if provided
    images = job_input.get("images")
    if images is not None:
        if not isinstance(images, list) or not all(
            "name" in image and "image" in image for image in images
        ):
            return (
                None,
                "'images' must be a list of objects with 'name' and 'image' keys",
            )

    # Return validated data and no error
    return {"workflow": workflow, "images": images}, None


def check_server(url, retries=500, delay=50):
    """
    Check if a server is reachable via HTTP GET request

    Args:
    - url (str): The URL to check
    - retries (int, optional): The number of times to attempt connecting to the server. Default is 50
    - delay (int, optional): The time in milliseconds to wait between retries. Default is 500

    Returns:
    bool: True if the server is reachable within the given number of retries, otherwise False
    """

    for i in range(retries):
        try:
            response = requests.get(url)

            # If the response status code is 200, the server is up and running
            if response.status_code == 200:
                print(f"runpod-worker-comfy - API is reachable")
                return True
        except requests.RequestException as e:
            # If an exception occurs, the server may not be ready
            pass

        # Wait for the specified delay before retrying
        time.sleep(delay / 1000)

    print(
        f"runpod-worker-comfy - Failed to connect to server at {url} after {retries} attempts."
    )
    return False

def get_workflow_payload(workflow_name, payload, image_names=None, job_id=None):
    # Try multiple possible locations for the workflow file
    possible_paths = [        
        f'/workflows/{workflow_name}.json', 
        f'/src/workflows/{workflow_name}.json',     
        f'./workflows/{workflow_name}.json',
        f'./src/workflows/{workflow_name}.json',  
    ]
    
    workflow_file = None
    for path in possible_paths:
        try:
            rp_logger.info(f'Trying to open workflow file at: {path}')
            with open(path, 'r') as json_file:
                workflow = json.load(json_file)
                rp_logger.info(f'Successfully loaded workflow from: {path}')
                workflow_file = path
                break
        except FileNotFoundError:
            rp_logger.info(f'Workflow file not found at: {path}')
            continue
    
    if workflow_file is None:
        raise FileNotFoundError(f"Could not find workflow file for: {workflow_name}. Tried paths: {possible_paths}")

    if workflow_name == 'img2imgPersona':
        workflow = get_img2imgPersona_payload(workflow, payload, image_names, job_id)
        rp_logger.info(f'Workflow payload for {workflow_name} generated successfully', job_id)
        
    if workflow_name == 'txt2imgSceneSDXL':
        workflow = get_txt2imgSceneSDXL_payload(workflow, payload, job_id)
        rp_logger.info(f'Workflow payload for {workflow_name} generated successfully', job_id)
        
    if workflow_name == 'upscaleSDXL':
        workflow = get_upscaleSDXL_payload(workflow, payload, image_names, job_id)
        rp_logger.info(f'Workflow payload for {workflow_name} generated successfully', job_id)

    return workflow

def get_upscaleSDXL_payload(workflow, payload, image_names, prefix):
    """ KSampler """
    workflow["12"]["inputs"]["seed"] = payload["seed"]
    workflow["12"]["inputs"]["steps"] = payload["steps"]
    workflow["12"]["inputs"]["cfg"] = payload["cfg_scale"]
    workflow["12"]["inputs"]["sampler_name"] = payload["sampler_name"]
    workflow["12"]["inputs"]["scheduler"] = payload["scheduler"]
    workflow["12"]["inputs"]["denoise"] = payload["denoise"]
    
    """ Checkpoint"""
    workflow["1"]["inputs"]["ckpt_name"] = payload["ckpt_name"]
    """ Positive prompt """
    workflow["4"]["inputs"]["width"] = payload["width"]
    workflow["4"]["inputs"]["height"] = payload["height"]
    workflow["4"]["inputs"]["target_width"] = payload["width"]
    workflow["4"]["inputs"]["target_height"] = payload["height"]
    workflow["4"]["inputs"]["text"] = payload["prompt"]
    """ Negative prompt """
    workflow["5"]["inputs"]["width"] = payload["width"]
    workflow["5"]["inputs"]["height"] = payload["height"]
    workflow["5"]["inputs"]["target_width"] = payload["width"]
    workflow["5"]["inputs"]["target_height"] = payload["height"]
    workflow["5"]["inputs"]["text"] = payload["negative_prompt"]
    """ LoadImage """
    workflow["8"]["inputs"]["image"] = image_names[0]    
    """ SaveImage """    
    workflow["25"]["inputs"]["filename_prefix"] = prefix
    return workflow

def get_img2imgPersona_payload(workflow, payload, image_names, prefix):
    workflow["10"]["inputs"]["seed"] = payload["seed"]
    workflow["10"]["inputs"]["steps"] = payload["steps"]
    workflow["10"]["inputs"]["cfg"] = payload["cfg_scale"]
    workflow["10"]["inputs"]["sampler_name"] = payload["sampler_name"]
    workflow["10"]["inputs"]["scheduler"] = payload["scheduler"]
    # workflow["10"]["inputs"]["denoise"] = payload["denoise"]
    """ Checkpoint"""
    workflow["7"]["inputs"]["ckpt_name"] = payload["ckpt_name"]
    workflow["8"]["inputs"]["width"] = payload["width"]
    workflow["8"]["inputs"]["height"] = payload["height"]
    workflow["8"]["inputs"]["batch_size"] = payload["batch_size"]
    """ Positive prompt """
    workflow["174"]["inputs"]["width"] = payload["width"]
    workflow["174"]["inputs"]["height"] = payload["height"]
    workflow["174"]["inputs"]["target_width"] = payload["width"]
    workflow["174"]["inputs"]["target_height"] = payload["height"]
    workflow["174"]["inputs"]["text"] = payload["prompt"]
    """ Negative prompt """
    workflow["176"]["inputs"]["width"] = payload["width"]
    workflow["176"]["inputs"]["height"] = payload["height"]
    workflow["176"]["inputs"]["target_width"] = payload["width"]
    workflow["176"]["inputs"]["target_height"] = payload["height"]
    workflow["176"]["inputs"]["text"] = payload["negative_prompt"]
    """ LoadImage """
    workflow["184"]["inputs"]["image"] = image_names[0]
    workflow["186"]["inputs"]["image"] = image_names[1] if image_names[1] else image_names[0]
    workflow["188"]["inputs"]["image"] = image_names[2] if image_names[2] else image_names[0]
    workflow["190"]["inputs"]["image"] = image_names[3] if image_names[3] else image_names[0]    
    """ SaveImage """
    workflow["193"]["inputs"]["filename_prefix"] = prefix
    return workflow

def get_txt2imgSceneSDXL_payload(workflow, payload, prefix):
    workflow["10"]["inputs"]["seed"] = payload["seed"]
    workflow["10"]["inputs"]["steps"] = payload["steps"]
    workflow["10"]["inputs"]["cfg"] = payload["cfg_scale"]
    workflow["10"]["inputs"]["sampler_name"] = payload["sampler_name"]
    workflow["10"]["inputs"]["scheduler"] = payload["scheduler"]
    """ Checkpoint"""
    workflow["7"]["inputs"]["ckpt_name"] = payload["ckpt_name"]
    workflow["8"]["inputs"]["width"] = payload["width"]
    workflow["8"]["inputs"]["height"] = payload["height"]
    workflow["8"]["inputs"]["batch_size"] = payload["batch_size"]
    """ Positive prompt """
    workflow["174"]["inputs"]["width"] = payload["width"]
    workflow["174"]["inputs"]["height"] = payload["height"]
    workflow["174"]["inputs"]["target_width"] = payload["width"]
    workflow["174"]["inputs"]["target_height"] = payload["height"]
    workflow["174"]["inputs"]["text"] = payload["prompt"]
    """ Negative prompt """
    workflow["176"]["inputs"]["width"] = payload["width"]
    workflow["176"]["inputs"]["height"] = payload["height"]
    workflow["176"]["inputs"]["target_width"] = payload["width"]
    workflow["176"]["inputs"]["target_height"] = payload["height"]    
    workflow["176"]["inputs"]["text"] = payload["negative_prompt"]
    """ SaveImage """
    workflow["193"]["inputs"]["filename_prefix"] = prefix
    return workflow

def is_webp_base64(base64_string):
    """
    Check if a base64 string represents a WebP image.
    
    Args:
        base64_string (str): The base64 encoded image string
        
    Returns:
        bool: True if the image is WebP, False otherwise
    """
    try:
        # Decode the base64 string
        image_data = base64.b64decode(base64_string)
        
        # Method 1: Check for WebP signature in header
        # WebP files start with "RIFF" followed by file size and "WEBP"
        if len(image_data) >= 12:
            if image_data.startswith(b'RIFF') and b'WEBP' in image_data[0:12]:
                return True
        
        # Method 2: Try to open with PIL and check format
        try:
            with Image.open(BytesIO(image_data)) as img:
                return img.format == 'WEBP'
        except:
            pass
            
        # Method 3: Check file extension in MIME type if available
        # This would be in the base64 string metadata if present
        if ',' in base64_string and ';base64,' in base64_string:
            mime_part = base64_string.split(';base64,')[0]
            if 'webp' in mime_part.lower():
                return True
                
        return False
    except Exception as e:
        rp_logger.error(f"Error in is_webp_base64: {str(e)}")
        return False

def convert_webp_to_png(webp_data):
    """
    Convert WebP image data to PNG format with robust handling of different image modes.
    
    Args:
        webp_data (bytes): The WebP image data
        
    Returns:
        bytes: The converted PNG image data
    """
    try:
        # Open the WebP image using PIL
        img = Image.open(BytesIO(webp_data))
        
        # Handle transparency in WebP images
        if img.mode == 'RGBA' or img.mode == 'LA':
            # Create a white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            # Paste the image on the background, using alpha as mask
            if 'A' in img.mode:
                background.paste(img, mask=img.split()[img.mode.find('A')])
                img = background
            else:
                img = img.convert('RGB')
        elif img.mode != 'RGB':
            # Convert other modes to RGB
            img = img.convert('RGB')
        
        # Convert to PNG
        output = BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
    except Exception as e:
        rp_logger.error(f"Error converting WebP to PNG: {str(e)}")
        # Return original data if conversion fails
        return webp_data

def is_valid_image(image_data):
    """
    Check if the data is a valid image that can be opened by PIL.
    
    Args:
        image_data (bytes): The image data to check
        
    Returns:
        bool: True if the data is a valid image, False otherwise
    """
    try:
        with Image.open(BytesIO(image_data)) as img:
            # Try to load the image data - this will fail if it's not a valid image
            img.load()
            return True
    except Exception:
        return False

def upload_images(images, batch_id=None):
    """
    Upload a list of base64 encoded images to the ComfyUI server using the /upload/image endpoint.
    Automatically converts all images to PNG format to ensure compatibility with ComfyUI.
    
    If batch_id is provided, it will check if images have already been uploaded for this batch
    and reuse them instead of uploading again.

    Args:
        images (list): A list of dictionaries, each containing the 'name' of the image and the 'image' as a base64 encoded string.
        batch_id (str, optional): A unique identifier for batch processing. If provided, images will only be uploaded once per batch.

    Returns:
        dict: A dictionary containing upload status, messages, and updated filenames.
    """
    global batch_uploaded_images
    
    if not images:
        return {"status": "success", "message": "No images to upload", "details": []}

    responses = []
    upload_errors = []
    # Track the updated filenames during the upload process
    updated_filenames = []
    
    # Check if we have a batch_id and if we've already uploaded some images for this batch
    if batch_id and batch_id in batch_uploaded_images:
        rp_logger.info(f"Using previously uploaded images for batch: {batch_id}")
        
        # Create a mapping of original names to already uploaded names
        uploaded_map = batch_uploaded_images[batch_id]
        
        # Filter out images that have already been uploaded
        images_to_upload = []
        for image in images:
            original_name = image["name"]
            if original_name in uploaded_map:
                # Image already uploaded, use the updated name
                updated_name = uploaded_map[original_name]
                rp_logger.info(f"Reusing previously uploaded image: {original_name} -> {updated_name}")
                updated_filenames.append(updated_name)
                responses.append(f"Reusing previously uploaded {updated_name}")
            else:
                # Image not uploaded yet, add to the list to upload
                images_to_upload.append(image)
        
        # If all images were already uploaded, return success
        if not images_to_upload:
            return {
                "status": "success",
                "message": "All images were previously uploaded",
                "details": responses,
                "updated_filenames": updated_filenames
            }
        
        # Otherwise, continue with uploading the remaining images
        images = images_to_upload
        print(f"runpod-worker-comfy - uploading {len(images)} new images for batch {batch_id}")
    else:
        print(f"runpod-worker-comfy - image(s) upload" + (f" for batch {batch_id}" if batch_id else ""))

    for image in images:
        original_name = image["name"]
        name = original_name  # Start with the original name
        image_data = image["image"]
        
        # Strip MIME type prefix if present (e.g., "data:image/webp;base64,")
        if ';base64,' in image_data:
            image_data = image_data.split(';base64,', 1)[1]
        
        # Decode the base64 image
        try:
            blob = base64.b64decode(image_data)
        except Exception as e:
            rp_logger.error(f"Error decoding base64 image: {str(e)}")
            upload_errors.append(f"Error decoding base64 image {name}: {str(e)}")
            continue
        
        # Check if the image is WebP
        is_webp = is_webp_base64(image_data)
        
        # Verify this is actually a valid image before trying to convert
        if not is_valid_image(blob):
            rp_logger.error(f"Invalid image data for {name}")
            upload_errors.append(f"Invalid image data for {name}")
            continue
        
        # Convert images to PNG to ensure compatibility
        try:
            if is_webp:
                print(f"runpod-worker-comfy - detected WebP image, converting to PNG: {name}")
                # Use our specialized WebP to PNG conversion for WebP images
                blob = convert_webp_to_png(blob)
            else:
                # For non-WebP images, use standard conversion
                print(f"runpod-worker-comfy - converting image to PNG: {name}")
                img = Image.open(BytesIO(blob))
                output = BytesIO()
                img.save(output, format='PNG')
                blob = output.getvalue()
            
            # Update the file extension if it's not already PNG
            if not name.lower().endswith('.png'):
                # Remove old extension if present
                if '.' in name:
                    name = name.rsplit('.', 1)[0]
                name = name + '.png'
                
            # Verify the converted image is valid
            if is_valid_image(blob):
                print(f"runpod-worker-comfy - image successfully converted: {name}")
            else:
                raise Exception("Converted image is not valid")
                
        except Exception as e:
            rp_logger.error(f"Error converting image to PNG: {str(e)}")
            # If conversion fails, we'll try to use the original image
            print(f"runpod-worker-comfy - conversion failed, using original image: {name}")

        # Prepare the form data
        files = {
            "image": (name, BytesIO(blob), "image/png"),
            "overwrite": (None, "true"),
        }

        # POST request to upload the image
        response = requests.post(f"http://{COMFY_HOST}/upload/image", files=files)
        if response.status_code != 200:
            upload_errors.append(f"Error uploading {name}: {response.text}")
            # Add the original name to the updated filenames list for consistency
            updated_filenames.append(original_name)
        else:
            rp_logger.info(f"Image uploaded successfully: {name}")
            responses.append(f"Successfully uploaded {name}")
            # Add the updated name to the list
            updated_filenames.append(name)
            
            # If we have a batch_id, store the mapping of original name to updated name
            if batch_id:
                batch_uploaded_images[batch_id][original_name] = name
    
    # Log the updated filenames for debugging
    rp_logger.info(f"Original filenames: {[img['name'] for img in images]}")
    rp_logger.info(f"Updated filenames: {updated_filenames}")
    
    if upload_errors:
        print(f"runpod-worker-comfy - image(s) upload with errors")
        return {
            "status": "error",
            "message": "Some images failed to upload",
            "details": upload_errors,
            "updated_filenames": updated_filenames  # Include even on error for partial success
        }

    print(f"runpod-worker-comfy - image(s) upload complete")
    return {
        "status": "success",
        "message": "All images uploaded successfully",
        "details": responses,
        "updated_filenames": updated_filenames  # Include the updated filenames
    }


def queue_workflow(workflow):
    """
    Queue a workflow to be processed by ComfyUI

    Args:
        workflow (dict): A dictionary containing the workflow to be processed

    Returns:
        dict: The JSON response from ComfyUI after processing the workflow
    """

    # The top level element "prompt" is required by ComfyUI
    data = json.dumps({"prompt": workflow}).encode("utf-8")

    req = urllib.request.Request(f"http://{COMFY_HOST}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())


def get_history(prompt_id):
    """
    Retrieve the history of a given prompt using its ID

    Args:
        prompt_id (str): The ID of the prompt whose history is to be retrieved

    Returns:
        dict: The history of the prompt, containing all the processing steps and results
    """
    with urllib.request.urlopen(f"http://{COMFY_HOST}/history/{prompt_id}") as response:
        return json.loads(response.read())


def base64_encode(img_path):
    """
    Returns base64 encoded image.

    Args:
        img_path (str): The path to the image

    Returns:
        str: The base64 encoded image
    """
    with open(img_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return f"{encoded_string}"

"""
Get the filenames of the output images
"""
def get_filenames(output):
    for key, value in output.items():
        if 'images' in value and isinstance(value['images'], list):
            return value['images']

def handle_python_upscaler(image_names, job_id):
    """
    Handle the Python server upscaler functionality.
    
    Args:
        image_names (list): List of image names to upscale
        job_id (str): The job ID for logging
        
    Returns:
        dict: A dictionary containing the upscaled images
    """
    try:
        # Use absolute import instead of relative import
        import sys
        import os
        import subprocess
        
        # More comprehensive approach to handle the virtual environment
        # First, try to find the Python version used in the venv
        venv_path = '/ComfyUI/venv'
        
        # Check if the venv directory exists
        if not os.path.exists(venv_path):
            rp_logger.error(f"ComfyUI venv directory not found: {venv_path}", job_id)
            raise RuntimeError(f"ComfyUI venv directory not found: {venv_path}")
        
        # Try to find the Python executable in the venv
        venv_python = os.path.join(venv_path, 'bin', 'python')
        if not os.path.exists(venv_python):
            rp_logger.error(f"Python executable not found in venv: {venv_python}", job_id)
            raise RuntimeError(f"Python executable not found in venv: {venv_python}")
        
        # Get the Python version from the venv
        try:
            python_version_cmd = f"{venv_python} --version"
            python_version_output = subprocess.check_output(python_version_cmd, shell=True, text=True)
            rp_logger.info(f"Venv Python version: {python_version_output.strip()}", job_id)
        except subprocess.CalledProcessError as e:
            rp_logger.error(f"Failed to get Python version from venv: {e}", job_id)
        
        # Try to execute the upscaler using the venv Python directly
        try:
            rp_logger.info(f"Executing upscaler using venv Python directly", job_id)
            
            # Create a temporary script to import and run the upscaler
            temp_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_upscaler.py')
            with open(temp_script_path, 'w') as f:
                f.write(f'''
import sys
import os
from upscaler import queue

# Log the Python path for debugging
print("Python path:", sys.path)

# Run the upscaler
result = queue("{image_names[0]}", 4)
print("Upscaler result:", result)
''')
            
            # Execute the script with the venv Python
            cmd = f"{venv_python} {temp_script_path}"
            rp_logger.info(f"Executing command: {cmd}", job_id)
            result = subprocess.check_output(cmd, shell=True, text=True)
            rp_logger.info(f"Upscaler output: {result}", job_id)
            
            # Clean up the temporary script
            os.remove(temp_script_path)
            
            # Parse the result from the output
            # This is a simple approach - you might need to adjust based on the actual output format
            import re
            match = re.search(r"Upscaler result: (.*)", result)
            if match:
                response = eval(match.group(1))  # Be careful with eval - only use with trusted input
                rp_logger.info(f'Upscaling completed successfully', job_id)
                return {
                    'images': response
                }
            else:
                raise RuntimeError("Could not parse upscaler result from output")
        except Exception as e:
            rp_logger.error(f'Error executing upscaler with venv Python: {e}', job_id)
            rp_logger.info(f'Falling back to direct import method', job_id)
            
            # Add the current directory to sys.path if not already there
            current_dir = os.path.dirname(os.path.abspath(__file__))
            if current_dir not in sys.path:
                sys.path.append(current_dir)
            
            # Try to find and add the site-packages directory from the venv
            site_packages_paths = [
                os.path.join(venv_path, 'lib', 'python3.10', 'site-packages'),
                os.path.join(venv_path, 'lib', 'python3.9', 'site-packages'),
                os.path.join(venv_path, 'lib', 'python3.8', 'site-packages'),
                os.path.join(venv_path, 'lib', 'python3.7', 'site-packages'),
                os.path.join(venv_path, 'lib', 'python3', 'site-packages'),
                os.path.join(venv_path, 'lib64', 'python3.10', 'site-packages'),
                os.path.join(venv_path, 'lib64', 'python3.9', 'site-packages'),
                os.path.join(venv_path, 'lib64', 'python3.8', 'site-packages'),
                os.path.join(venv_path, 'lib64', 'python3.7', 'site-packages'),
                os.path.join(venv_path, 'lib64', 'python3', 'site-packages')
            ]
            
            for path in site_packages_paths:
                if os.path.exists(path) and path not in sys.path:
                    sys.path.insert(0, path)
                    rp_logger.info(f'Added venv site-packages to Python path: {path}', job_id)
            
            # Import the queue function from upscaler module
            from upscaler import queue
            
            # Log the upscaling process
            rp_logger.info(f'Starting upscaling process with image: {image_names[0]}', job_id)
            
            # Call the queue function with the first image name and scale factor 4
            response = queue(image_names[0], 4)
            
            rp_logger.info(f'Upscaling completed successfully', job_id)
            
            return {
                'images': response
            }
    except ImportError as e:
        rp_logger.error(f'Failed to import upscaler module: {e}', job_id)
        raise RuntimeError(f'Failed to import upscaler module: {e}')
    except Exception as e:
        rp_logger.error(f'Error in Python server: {e}', job_id)
        raise RuntimeError(f'Error in Python server: {e}')

def handler(event):
    """
    The main function that handles a job of generating an image.

    This function validates the input, sends a prompt to ComfyUI for processing,
    polls ComfyUI for result, and retrieves generated images.

    Args:
        job (dict): A dictionary containing job details and input parameters.

    Returns:
        dict: A dictionary containing either an error message or a success status with generated images.
    """
    rp_logger.info('Starting RunPod Serverless handler', event["id"])
    job_id = event["id"]

    try:
        # Make sure that the input is valid
        validated_input = validate(event['input'], INPUT_SCHEMA)
        if 'errors' in validated_input:
            return {
                'error': '\n'.join(validated_input['errors'])
            }
        else:
            rp_logger.info('Input validated successfully', job_id)

        # Extract validated data
        validated_data = validated_input["validated_input"]     
        server_type = validated_data["server"]   
        workflow = validated_data["workflow"]
        payload = validated_data['payload']
        images = validated_data['images'] if 'images' in validated_data else []
        
        if workflow == 'default':
            workflow = 'txt2img'
        
        rp_logger.info(f'Workflow: {workflow}', job_id)
        
        if server_type == 'comfyui':

            # Make sure that the ComfyUI API is available
            check_server(
                f"http://{COMFY_HOST}",
                COMFY_API_AVAILABLE_MAX_RETRIES,
                COMFY_API_AVAILABLE_INTERVAL_MS,
            )

        # Check if batchId is provided in the input
        batch_id = validated_data.get('batchId')
        
        # Handle case where batch_id is "undefined"
        if batch_id == "undefined":
            rp_logger.info("Client sent batchId: undefined, treating as no batch ID", job_id)
            batch_id = None
        
        # Clean up any inactive batches
        clean_inactive_batches()
        
        # If a batchId is provided, check if it's already being processed
        if batch_id and is_batch_active(batch_id):
            rp_logger.info(f"Batch {batch_id} is already being processed, using ComfyUI queue system", job_id)
            # Mark this batch as still active
            update_batch_status(batch_id, 'processing')
        
        # Upload images if they exist and track the updated filenames
        # If batchId is provided, it will be used to reuse previously uploaded images
        upload_result = upload_images(images, batch_id)
        if upload_result["status"] == "error":
            return upload_result
        
        # Get the updated image names (which may have changed from .webp to .png)
        updated_image_names = []
        if "updated_filenames" in upload_result:
            updated_image_names = upload_result["updated_filenames"]
        else:
            # Fallback if updated filenames aren't provided
            for image in images:
                name = image["name"]
                # Ensure .webp extensions are changed to .png
                if name.lower().endswith('.webp'):
                    name = name[:-5] + '.png'
                updated_image_names.append(name)
        
        rp_logger.info(f'Updated image names: {updated_image_names}', job_id)
        
        # Now get the workflow payload with the updated image names
        if workflow == 'img2imgPersona':
            try:
                payload = get_workflow_payload(workflow, payload, updated_image_names, job_id)
            except Exception as e:
                rp_logger.error(f'Unable to load workflow payload for: {workflow}', job_id)
                raise
            
        if workflow == 'txt2imgSceneSDXL':
            try:
                payload = get_workflow_payload(workflow, payload, None, job_id)
            except Exception as e:
                rp_logger.error(f'Unable to load workflow payload for: {workflow}', job_id)
                raise
            
        if workflow == 'upscaleSDXL':
            try:
                payload = get_workflow_payload(workflow, payload, updated_image_names, job_id)
            except Exception as e:
                rp_logger.error(f'Unable to load workflow payload for: {workflow}', job_id)
                raise
        # If a batchId is provided, mark it as processing
        if batch_id:
            update_batch_status(batch_id, 'processing')
        
        if server_type == 'python':    
            return handle_python_upscaler(updated_image_names, job_id)
        elif server_type == 'comfyui':
            queue_response = send_post_request(
                'prompt',
                {
                    'prompt': payload
                }
            )
            rp_logger.info(f'Prompt: {payload}', job_id)
            
            if queue_response.status_code == 200:
                resp_json = queue_response.json()
                prompt_id = resp_json['prompt_id']
                rp_logger.info(f'runpod-worker-comfy - Prompt queued successfully: {prompt_id}', job_id)
                retries = 0
                
                while True:
                    # Only log every 15 retries so the logs don't get spammed
                    if retries == 0 or retries % 15 == 0:
                        rp_logger.info(f'Getting status of prompt: {prompt_id}', job_id)
                    
                    r = send_get_request(f'history/{prompt_id}')
                    resp_json = r.json()

                    if r.status_code == 200 and len(resp_json):
                        break

                    time.sleep(0.2)
                    retries += 1
                    
                status = resp_json[prompt_id]['status']
                if status['status_str'] == 'success' and status['completed']:
                    # Job was processed successfully
                    outputs = resp_json[prompt_id]['outputs']

                    if len(outputs):
                        rp_logger.info(f'Images generated successfully for prompt: {prompt_id}', job_id)
                        image_filenames = get_filenames(outputs)
                        images = []

                        for image_filename in image_filenames:
                            filename = image_filename['filename']
                            image_path = f'/ComfyUI/output/{filename}'
                            rp_logger.info(f'Image path: {image_path}', job_id)
                                                    
                            with Image.open(image_path) as img:
                                # width, height = img.size
                                # rp_logger.info(f"The image size is: {img.size}")
                                # rp_logger.info(f"The image resolution is: {width}x{height}")
                                output = BytesIO()
                                img.save(output, format='PNG')
                                images.append(base64.b64encode(output.getvalue()).decode('utf-8'))
                                # output.close()
                            # with open(image_path, 'rb') as image_file:                            
                            #     images.append(base64.b64encode(image_file.read()).decode('utf-8'))

                            # rp_logger.info(f'Deleting output file: {image_path}', job_id)
                            # os.remove(image_path)

                        # If a batchId was provided, mark it as completed
                        if batch_id:
                            update_batch_status(batch_id, 'completed', prompt_id)
                            
                        return {
                            'images': images
                        }
                    else:
                        raise RuntimeError(f'No output found for prompt id: {prompt_id}')
                else:
                    # Job did not process successfully
                    for message in status['messages']:
                        key, value = message

                        if key == 'execution_error':
                            if 'node_type' in value and 'exception_message' in value:
                                node_type = value['node_type']
                                exception_message = value['exception_message']
                                raise RuntimeError(f'{node_type}: {exception_message}')
                            else:
                                # Log to file instead of RunPod because the output tends to be too verbose
                                # and gets dropped by RunPod logging
                                error_msg = f'Job did not process successfully for prompt_id: {prompt_id}'
                                logging.error(error_msg)
                                logging.info(f'{job_id}: Response JSON: {resp_json}')
                                raise RuntimeError(error_msg)
            else:
                try:
                    queue_response_content = queue_response.json()
                except Exception as e:
                    queue_response_content = str(queue_response.content)

                rp_logger.error(f'HTTP Status code: {queue_response.status_code}', job_id)
                rp_logger.error(queue_response_content, job_id)

                return {
                    'error': f'HTTP status code: {queue_response.status_code}',
                    'output': queue_response_content
                }      
    
    except Exception as e:
        rp_logger.error(f'An exception was raised: {e}', job_id)
        
        # If a batchId was provided, mark it as completed with error
        if 'batch_id' in locals() and batch_id and batch_id != "undefined":
            update_batch_status(batch_id, 'completed')
            rp_logger.info(f"Marked batch {batch_id} as completed due to error", job_id)

        return {
            'error': traceback.format_exc(),
            'refresh_worker': True
        }


# Start the handler only if this script is run directly
if __name__ == "__main__":
    # Setup log file
    logging.getLogger().setLevel(LOG_LEVEL)
    # log_handler = logging.handlers.WatchedFileHandler(f'{VOLUME_MOUNT_PATH}/{LOG_FILE}')
    # formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
    # log_handler.setFormatter(formatter)
    # logging.getLogger().addHandler(log_handler)

    # Set up RunPod logger
    rp_logger.set_level(LOG_LEVEL)
    
    # Debug: Print current directory and check if workflows directory exists
    import os
    rp_logger.info(f'Current working directory: {os.getcwd()}')
    rp_logger.info(f'Workflows directory exists: {os.path.exists("/workflows")}')
    rp_logger.info(f'Src/workflows directory exists: {os.path.exists("/src/workflows")}')
    rp_logger.info(f'./src/workflows directory exists: {os.path.exists("./src/workflows")}')
    
    # List files in current directory
    rp_logger.info(f'Files in current directory: {os.listdir(".")}')
    
    # Try to list files in workflows directory if it exists
    if os.path.exists("/workflows"):
        rp_logger.info(f'Files in workflows directory: {os.listdir("/workflows")}')

    wait_for_service(url=f'{BASE_URI}/system_stats')
    rp_logger.info('ComfyUI API is ready')
    rp_logger.info('Starting RunPod Serverless...')
    
    runpod.serverless.start({"handler": handler})
