"""
Exact copy of reference code's camera init and capture.
Run this to verify hardware works.
"""
import sys
sys.path.insert(0, ".")

from ximea import xiapi
from PIL import Image
import numpy as np

def main():
    print("=== XIMEA Exact Reference Test ===")
    
    cam = xiapi.Camera()
    
    print("1. Opening device...")
    cam.open_device()
    
    # Get device info
    print(f"   Model: {cam.get_device_name()}")
    print(f"   Serial: {cam.get_device_sn()}")
    
    print("2. Setting parameters (Reference defaults)...")
    cam.set_imgdataformat('XI_RGB24')
    cam.set_exposure(50000)  # 50ms
    cam.set_gain(0.0)
    
    # White balance
    cam.set_wb_kr(1.531)
    cam.set_wb_kg(1.0)
    cam.set_wb_kb(1.305)
    
    # Disable auto
    cam.disable_aeag()
    
    print(f"   Exposure Range: {cam.get_exposure_minimum()} - {cam.get_exposure_maximum()}")
    print(f"   Auto WB: {cam.is_auto_wb()}")
    
    print("3. Capturing image (Start -> Get -> Stop)...")
    img = xiapi.Image()
    
    cam.start_acquisition()
    cam.get_image(img)  # No timeout, like reference
    cam.stop_acquisition()
    
    print("4. Converting to numpy...")
    data = img.get_image_data_numpy(invert_rgb_order=True)  # Reference uses this!
    
    print(f"   Shape: {data.shape}")
    print(f"   Dtype: {data.dtype}")
    print(f"   Mean: {data.mean():.2f}")
    print(f"   Min/Max: {data.min()} / {data.max()}")
    
    # Save test image
    pil_img = Image.fromarray(data, 'RGB')
    pil_img.save("test_capture.bmp")
    print(f"5. Saved to test_capture.bmp")
    
    cam.close_device()
    print("6. Closed. SUCCESS!")

if __name__ == "__main__":
    main()
