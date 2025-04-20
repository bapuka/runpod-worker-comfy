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

BASE_URI = f'http://{COMFY_HOST}'
VOLUME_MOUNT_PATH = '/runpod-volume'
LOG_FILE= 'comfyui-worker.log'
LOG_LEVEL = 'INFO'
TIMEOUT = 600

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

def get_workflow_payload(workflow_name, payload, image_names=None):
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
        workflow = get_img2imgPersona_payload(workflow, payload, image_names)

    return workflow

def get_img2imgPersona_payload(workflow, payload, image_names):
    workflow["10"]["inputs"]["seed"] = payload["seed"]
    workflow["10"]["inputs"]["steps"] = payload["steps"]
    workflow["10"]["inputs"]["cfg"] = payload["cfg_scale"]
    workflow["10"]["inputs"]["sampler_name"] = payload["sampler_name"]
    workflow["10"]["inputs"]["scheduler"] = payload["scheduler"]
    # workflow["10"]["inputs"]["denoise"] = payload["denoise"]
    workflow["7"]["inputs"]["ckpt_name"] = payload["ckpt_name"]
    workflow["8"]["inputs"]["width"] = payload["width"]
    workflow["8"]["inputs"]["height"] = payload["height"]
    workflow["8"]["inputs"]["batch_size"] = payload["batch_size"]
    workflow["174"]["inputs"]["width"] = payload["width"]
    workflow["174"]["inputs"]["height"] = payload["height"]
    workflow["174"]["inputs"]["target_width"] = payload["width"]
    workflow["174"]["inputs"]["target_height"] = payload["height"]
    workflow["176"]["inputs"]["width"] = payload["width"]
    workflow["176"]["inputs"]["height"] = payload["height"]
    workflow["176"]["inputs"]["target_width"] = payload["width"]
    workflow["176"]["inputs"]["target_height"] = payload["height"]
    workflow["184"]["inputs"]["image"] = image_names[0]
    workflow["186"]["inputs"]["image"] = image_names[0]
    workflow["188"]["inputs"]["image"] = image_names[0]
    workflow["190"]["inputs"]["image"] = image_names[0]
    workflow["174"]["inputs"]["text"] = payload["prompt"]
    workflow["176"]["inputs"]["text"] = payload["negative_prompt"]
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

def upload_images(images):
    """
    Upload a list of base64 encoded images to the ComfyUI server using the /upload/image endpoint.
    Automatically converts all images to PNG format to ensure compatibility with ComfyUI.

    Args:
        images (list): A list of dictionaries, each containing the 'name' of the image and the 'image' as a base64 encoded string.
        server_address (str): The address of the ComfyUI server.

    Returns:
        list: A list of responses from the server for each image upload.
    """
    if not images:
        return {"status": "success", "message": "No images to upload", "details": []}

    responses = []
    upload_errors = []
    # Track the updated filenames during the upload process
    updated_filenames = []

    print(f"runpod-worker-comfy - image(s) upload")

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
        workflow = validated_data["workflow"]
        payload = validated_data['payload']
        images = validated_data['images'] if 'images' in validated_data else []
        
        if workflow == 'default':
            workflow = 'txt2img'
        
        rp_logger.info(f'Workflow: {workflow}', job_id)

        # Make sure that the ComfyUI API is available
        check_server(
            f"http://{COMFY_HOST}",
            COMFY_API_AVAILABLE_MAX_RETRIES,
            COMFY_API_AVAILABLE_INTERVAL_MS,
        )

        # Upload images if they exist and track the updated filenames
        upload_result = upload_images(images)
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
                payload = get_workflow_payload(workflow, payload, updated_image_names)
            except Exception as e:
                rp_logger.error(f'Unable to load workflow payload for: {workflow}', job_id)
                raise

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
            rp_logger.info(f'Prompt queued successfully: {prompt_id}', job_id)
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
                                                
                        with Image.open(image_path) as img:
                            # width, height = img.size
                            rp_logger.info(f"The image size is: {img.size}")
                            # rp_logger.info(f"The image resolution is: {width}x{height}")
                            output = BytesIO()
                            img.save(output, format='PNG')
                            images.append(base64.b64encode(output.getvalue()).decode('utf-8'))
                            
                        # with open(image_path, 'rb') as image_file:                            
                        #     images.append(base64.b64encode(image_file.read()).decode('utf-8'))

                        # rp_logger.info(f'Deleting output file: {image_path}', job_id)
                        # os.remove(image_path)

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
    
    # List files in current directory
    rp_logger.info(f'Files in current directory: {os.listdir(".")}')
    
    # Try to list files in workflows directory if it exists
    if os.path.exists("/workflows"):
        rp_logger.info(f'Files in workflows directory: {os.listdir("/workflows")}')

    wait_for_service(url=f'{BASE_URI}/system_stats')
    rp_logger.info('ComfyUI API is ready')
    rp_logger.info('Starting RunPod Serverless...')
    
    runpod.serverless.start({"handler": handler})
