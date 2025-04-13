import base64
from io import BytesIO
from PIL import Image
import unittest

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
        print(f"Error in is_webp_base64: {str(e)}")
        return False

def convert_to_png(image_data):
    """
    Convert any image data to PNG format.
    
    Args:
        image_data (bytes): The image data
        
    Returns:
        bytes: The converted PNG image data
    """
    try:
        # Open the image using PIL
        img = Image.open(BytesIO(image_data))
        
        # Convert to PNG
        output = BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
    except Exception as e:
        print(f"Error converting image to PNG: {str(e)}")
        # Return original data if conversion fails
        return image_data

class TestImprovedConversion(unittest.TestCase):
    
    def create_webp_base64(self):
        """Create a sample WebP image and return its base64 representation"""
        # Create a simple image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Save as WebP
        buffer = BytesIO()
        img.save(buffer, format='WEBP')
        buffer.seek(0)
        
        # Convert to base64
        webp_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return webp_base64
    
    def create_png_base64(self):
        """Create a sample PNG image and return its base64 representation"""
        # Create a simple image
        img = Image.new('RGB', (100, 100), color='blue')
        
        # Save as PNG
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Convert to base64
        png_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return png_base64
    
    def create_jpeg_base64(self):
        """Create a sample JPEG image and return its base64 representation"""
        # Create a simple image
        img = Image.new('RGB', (100, 100), color='green')
        
        # Save as JPEG
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        
        # Convert to base64
        jpeg_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return jpeg_base64
    
    def create_webp_with_mime_base64(self):
        """Create a WebP image with MIME type in the base64 string"""
        webp_base64 = self.create_webp_base64()
        return f"data:image/webp;base64,{webp_base64}"
    
    def test_is_webp_base64(self):
        """Test the improved is_webp_base64 function"""
        # Test with WebP image
        webp_base64 = self.create_webp_base64()
        self.assertTrue(is_webp_base64(webp_base64), "Should detect WebP image")
        
        # Test with WebP image with MIME type
        webp_mime_base64 = self.create_webp_with_mime_base64()
        self.assertTrue(is_webp_base64(webp_mime_base64), "Should detect WebP image with MIME type")
        
        # Test with PNG image
        png_base64 = self.create_png_base64()
        self.assertFalse(is_webp_base64(png_base64), "Should not detect PNG as WebP")
        
        # Test with JPEG image
        jpeg_base64 = self.create_jpeg_base64()
        self.assertFalse(is_webp_base64(jpeg_base64), "Should not detect JPEG as WebP")
    
    def test_convert_to_png(self):
        """Test the convert_to_png function with different image formats"""
        # Test with WebP image
        webp_base64 = self.create_webp_base64()
        webp_data = base64.b64decode(webp_base64)
        png_data = convert_to_png(webp_data)
        
        # Verify the result is a valid PNG
        img = Image.open(BytesIO(png_data))
        self.assertEqual(img.format, 'PNG', "Converted WebP should be PNG format")
        
        # Test with JPEG image
        jpeg_base64 = self.create_jpeg_base64()
        jpeg_data = base64.b64decode(jpeg_base64)
        png_data = convert_to_png(jpeg_data)
        
        # Verify the result is a valid PNG
        img = Image.open(BytesIO(png_data))
        self.assertEqual(img.format, 'PNG', "Converted JPEG should be PNG format")
        
        # Test with PNG image (should remain PNG)
        png_base64 = self.create_png_base64()
        png_data = base64.b64decode(png_base64)
        png_data2 = convert_to_png(png_data)
        
        # Verify the result is still a valid PNG
        img = Image.open(BytesIO(png_data2))
        self.assertEqual(img.format, 'PNG', "PNG should remain PNG format")

if __name__ == '__main__':
    unittest.main()
