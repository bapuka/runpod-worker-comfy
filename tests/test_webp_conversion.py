import sys
import os
import base64
from io import BytesIO
from PIL import Image
import unittest

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.rp_handler import is_webp_base64, convert_webp_to_png

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
        self.assertEqual(center_pixel[1], 0, "Green channel should be 0")
        self.assertEqual(center_pixel[2], 0, "Blue channel should be 0")

if __name__ == '__main__':
    unittest.main()
