import base64
import os
import sys
from io import BytesIO
from PIL import Image, ImageFile

# Enable loading truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True

def convert_webp_to_png(webp_path, output_path=None):
    """
    Convert a WebP image file to PNG format.
    
    Args:
        webp_path (str): Path to the WebP image file
        output_path (str, optional): Path to save the PNG image. If not provided,
                                    will use the same name with .png extension
    
    Returns:
        str: Path to the saved PNG image
    """
    if not os.path.exists(webp_path):
        print(f"Error: File does not exist: {webp_path}")
        return None
    
    if not output_path:
        # Use the same name but with .png extension
        output_path = os.path.splitext(webp_path)[0] + '.png'
    
    try:
        # Open the WebP image
        with Image.open(webp_path) as img:
            print(f"Original image: format={img.format}, mode={img.mode}, size={img.size}")
            
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
            
            # Save as PNG
            img.save(output_path, 'PNG')
            print(f"Saved PNG image to: {output_path}")
            
            # Verify the saved image
            with Image.open(output_path) as png_img:
                print(f"Converted image: format={png_img.format}, mode={png_img.mode}, size={png_img.size}")
            
            return output_path
    
    except Exception as e:
        print(f"Error converting image: {str(e)}")
        return None

def convert_base64_webp_to_png(base64_string):
    """
    Convert a base64-encoded WebP image to PNG format.
    
    Args:
        base64_string (str): Base64-encoded WebP image
    
    Returns:
        str: Base64-encoded PNG image
    """
    try:
        # Strip MIME type prefix if present
        if ';base64,' in base64_string:
            base64_string = base64_string.split(';base64,', 1)[1]
        
        # Decode base64 string
        webp_data = base64.b64decode(base64_string)
        print(f"Decoded base64 data: {len(webp_data)} bytes")
        
        # Open the WebP image
        with Image.open(BytesIO(webp_data)) as img:
            print(f"Original image: format={img.format}, mode={img.mode}, size={img.size}")
            
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
            
            # Save as PNG
            output = BytesIO()
            img.save(output, format='PNG')
            png_data = output.getvalue()
            print(f"Converted to PNG: {len(png_data)} bytes")
            
            # Encode as base64
            png_base64 = base64.b64encode(png_data).decode('utf-8')
            
            # Save the PNG to a file for inspection
            with open('converted_image.png', 'wb') as f:
                f.write(png_data)
            print(f"Saved PNG image to: converted_image.png")
            
            return png_base64
    
    except Exception as e:
        print(f"Error converting base64 image: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # If a file path is provided
        webp_path = sys.argv[1]
        convert_webp_to_png(webp_path)
    else:
        print("Usage: python test_webp_conversion_simple.py <webp_image_path>")
        print("Or paste a base64 string when prompted")
        
        # Allow pasting a base64 string
        print("\nPaste a base64 string (Ctrl+D or Ctrl+Z to end):")
        base64_string = sys.stdin.read().strip()
        if base64_string:
            png_base64 = convert_base64_webp_to_png(base64_string)
            if png_base64:
                print("\nConverted base64 PNG (first 100 chars):")
                print(png_base64[:100] + "...")
