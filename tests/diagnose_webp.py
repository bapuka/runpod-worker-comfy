import base64
import os
import sys
from io import BytesIO
from PIL import Image, ImageFile

# Enable loading truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

def diagnose_image(image_path):
    """
    Diagnose issues with an image file by attempting to load and convert it.
    
    Args:
        image_path (str): Path to the image file
    """
    print(f"Diagnosing image: {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        print(f"Error: File does not exist: {image_path}")
        return
    
    # Get file size
    file_size = os.path.getsize(image_path)
    print(f"File size: {file_size} bytes")
    
    # Try to open the image
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            
        # Check file header
        print(f"File header (first 20 bytes): {image_data[:20]}")
        
        # Try to open with PIL
        try:
            img = Image.open(BytesIO(image_data))
            print(f"PIL can open the image: format={img.format}, mode={img.mode}, size={img.size}")
            
            # Try to load the image data
            try:
                img.load()
                print("Image data loaded successfully")
            except Exception as e:
                print(f"Error loading image data: {str(e)}")
                
            # Try to convert to RGB
            try:
                if img.mode != 'RGB':
                    img_rgb = img.convert('RGB')
                    print(f"Converted to RGB: mode={img_rgb.mode}, size={img_rgb.size}")
                else:
                    print("Image is already in RGB mode")
            except Exception as e:
                print(f"Error converting to RGB: {str(e)}")
                
            # Try to save as PNG
            try:
                output = BytesIO()
                img.save(output, format='PNG')
                png_data = output.getvalue()
                print(f"Successfully saved as PNG: {len(png_data)} bytes")
                
                # Try to open the PNG
                try:
                    png_img = Image.open(BytesIO(png_data))
                    png_img.load()
                    print(f"PNG image is valid: format={png_img.format}, mode={png_img.mode}, size={png_img.size}")
                except Exception as e:
                    print(f"Error opening PNG: {str(e)}")
            except Exception as e:
                print(f"Error saving as PNG: {str(e)}")
                
        except Exception as e:
            print(f"Error opening image with PIL: {str(e)}")
            
    except Exception as e:
        print(f"Error reading file: {str(e)}")

def diagnose_base64(base64_string, name="base64_image"):
    """
    Diagnose issues with a base64-encoded image.
    
    Args:
        base64_string (str): Base64-encoded image string
        name (str): Name for the image (for logging)
    """
    print(f"Diagnosing base64 image: {name}")
    
    # Check if it's a data URL
    if ';base64,' in base64_string:
        mime_part = base64_string.split(';base64,')[0]
        base64_string = base64_string.split(';base64,')[1]
        print(f"Detected data URL with MIME type: {mime_part}")
    
    # Try to decode base64
    try:
        image_data = base64.b64decode(base64_string)
        print(f"Base64 decoded successfully: {len(image_data)} bytes")
        
        # Save to temporary file for inspection
        temp_path = f"temp_{name}"
        with open(temp_path, 'wb') as f:
            f.write(image_data)
        print(f"Saved decoded data to: {temp_path}")
        
        # Diagnose the decoded data
        diagnose_image(temp_path)
        
    except Exception as e:
        print(f"Error decoding base64: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If a file path is provided
        diagnose_image(sys.argv[1])
    else:
        print("Usage: python diagnose_webp.py <image_path>")
        print("Or paste a base64 string when prompted")
        
        # Allow pasting a base64 string
        print("\nPaste a base64 string (Ctrl+D or Ctrl+Z to end):")
        base64_string = sys.stdin.read().strip()
        if base64_string:
            diagnose_base64(base64_string)
