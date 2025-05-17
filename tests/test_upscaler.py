import os
import sys
import json
import base64
from PIL import Image
from io import BytesIO

def test_upscaler_import():
    """
    Test if we can import the upscaler module without activating the virtual environment.
    This uses the same approach as our fix in rp_handler.py.
    """
    try:
        print("Testing upscaler import...")
        
        # Add the ComfyUI venv site-packages to Python path
        venv_site_packages = '/ComfyUI/venv/lib/python3.10/site-packages'
        if os.path.exists(venv_site_packages):
            print(f"ComfyUI venv site-packages directory exists: {venv_site_packages}")
            if venv_site_packages not in sys.path:
                sys.path.insert(0, venv_site_packages)
                print(f"Added ComfyUI venv site-packages to Python path")
        else:
            print(f"WARNING: ComfyUI venv site-packages directory not found: {venv_site_packages}")
            # Try to find other possible paths
            possible_paths = [
                '/ComfyUI/venv/lib/python3.9/site-packages',
                '/ComfyUI/venv/lib/python3.8/site-packages',
                '/ComfyUI/venv/lib/python3.7/site-packages',
                '/ComfyUI/venv/lib/python3/site-packages'
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    print(f"Found alternative site-packages: {path}")
                    sys.path.insert(0, path)
                    print(f"Added alternative site-packages to Python path")
                    break
        
        # Add the current directory to sys.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
            print(f"Added current directory to Python path: {current_dir}")
        
        # Try to import the queue function from upscaler module
        print("Attempting to import upscaler module...")
        from upscaler import queue
        print("Successfully imported upscaler.queue!")
        
        # Print information about the imported module
        print(f"Upscaler module location: {queue.__module__}")
        
        return True
    except ImportError as e:
        print(f"Failed to import upscaler module: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Python version:", sys.version)
    print("Python executable:", sys.executable)
    print("Current working directory:", os.getcwd())
    
    # List sys.path before our modifications
    print("\nPython path before modifications:")
    for p in sys.path:
        print(f"  {p}")
    
    # Run the test
    result = test_upscaler_import()
    
    # List sys.path after our modifications
    print("\nPython path after modifications:")
    for p in sys.path:
        print(f"  {p}")
    
    print("\nTest result:", "SUCCESS" if result else "FAILURE")
