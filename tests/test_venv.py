import subprocess
import sys
import os

def test_venv_activation():
    try:
        # Try to activate the virtual environment using bash
        print("Attempting to activate virtual environment...")
        result = subprocess.run('source /ComfyUI/venv/bin/activate && python -c "import sys; print(sys.executable)"', 
                               shell=True, 
                               executable='/bin/bash', 
                               check=True,
                               capture_output=True,
                               text=True)
        
        print(f"Command executed successfully")
        print(f"Output: {result.stdout}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error activating virtual environment: {e}")
        print(f"Exit code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False

if __name__ == "__main__":
    test_venv_activation()
