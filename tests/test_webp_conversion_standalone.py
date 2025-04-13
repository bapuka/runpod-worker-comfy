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
    # WebP images start with "RIFF" header followed by file size and "WEBP" identifier
    # In base64, this pattern can be detected at the beginning of the string
    try:
        # Decode a small portion of the base64 string to check the header
        header = base64.b64decode(base64_string[:32])
        return header.startswith(b'RIFF') and b'WEBP' in header[:16]
    except:
        return False

def convert_webp_to_png(webp_data):
    """
    Convert WebP image data to PNG format.
    
    Args:
        webp_data (bytes): The WebP image data
        
    Returns:
        bytes: The converted PNG image data
    """
    try:
        # Open the WebP image using PIL
        img = Image.open(BytesIO(webp_data))
        
        # Convert to PNG
        output = BytesIO()
        img.save(output, format='PNG')
        return output.getvalue()
    except Exception as e:
        print(f"Error converting WebP to PNG: {str(e)}")
        # Return original data if conversion fails
        return webp_data

class TestWebPConversion(unittest.TestCase):
    
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
    
    def test_is_webp_base64(self):
        """Test the is_webp_base64 function"""
        # Test with WebP image
        webp_base64 = self.create_webp_base64()
        self.assertTrue(is_webp_base64(webp_base64), "Should detect WebP image")
        
        # Test with PNG image
        png_base64 = self.create_png_base64()
        self.assertFalse(is_webp_base64(png_base64), "Should not detect PNG as WebP")
    
    def test_convert_webp_to_png(self):
        """Test the convert_webp_to_png function"""
        # Create WebP image
        webp_base64 = self.create_webp_base64()
        webp_data = base64.b64decode(webp_base64)
        
        # Convert to PNG
        png_data = convert_webp_to_png(webp_data)
        
        # Verify the result is a valid PNG
        img = Image.open(BytesIO(png_data))
        self.assertEqual(img.format, 'PNG', "Converted image should be PNG format")
        
        # Verify the image content is preserved
        self.assertEqual(img.width, 100, "Width should be preserved")
        self.assertEqual(img.height, 100, "Height should be preserved")
        
        # Check the color (should still be red)
        center_pixel = img.getpixel((50, 50))
        self.assertEqual(center_pixel[0], 255, "Red channel should be 255")
        # Allow small variations in green and blue channels due to compression artifacts
        self.assertLess(center_pixel[1], 5, "Green channel should be close to 0")
        self.assertLess(center_pixel[2], 5, "Blue channel should be close to 0")

if __name__ == '__main__':
    unittest.main()
