import sys
import time
import numpy as np

# Mock config
sys.path.append(".")
try:
    from ximea import xiapi
    print("STEP 1: XIMEA SDK Imported.")
except ImportError:
    print("STEP 1: FAILED to import ximea. SDK missing.")
    sys.exit(1)

def main():
    print("STEP 2: Initializing Camera...")
    cam = xiapi.Camera()
    
    try:
        cam.open_device()
        print("STEP 3: Device Opened.")
        
        cam.set_exposure(10000) # 10ms
        print("STEP 4: Exposure set.")
        
        try:
             cam.set_imgdataformat('XI_RGB24')
             print("STEP 5: Format set to RGB24.")
        except:
             print("STEP 5: Format set failed (maybe Mono?). Continuing.")
             
        cam.start_acquisition()
        print("STEP 6: Acquisition Started.")
        
        img = xiapi.Image()
        
        print("STEP 7: Attempting to grab 5 frames...")
        for i in range(5):
            t0 = time.time()
            cam.get_image(img, timeout=2000)
            data = img.get_image_data_numpy()
            dt = time.time() - t0
            
            print(f"  Frame {i+1}: Shape={data.shape}, Dtype={data.dtype}, Mean={data.mean():.2f}, Time={dt:.4f}s")
            
        cam.stop_acquisition()
        cam.close_device()
        print("STEP 8: Closed successfully.")
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
