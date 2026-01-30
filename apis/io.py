import os
import csv
import logging
from . import utils

# Try importing OpenCV for image saving
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False
    logging.warning("OpenCV not found. Image saving may fail if not handled by caller.")

def save_image(filepath, image_data, color_mode=None):
    """
    Save image_data (numpy array) to filepath (TIFF).
    color_mode: None (no conversion), "rgb" (convert RGB->BGR), "bgr" (no-op).
    """
    if not HAS_OPENCV:
        raise ImportError("OpenCV (cv2) is required to save images.")
    
    # Ensure directory
    directory = os.path.dirname(filepath)
    if directory:
        utils.ensure_dir(directory)

    # Validate image data
    if image_data is None or image_data.size == 0:
        logging.error(f"Cannot save image: Data is None or empty. File: {filepath}")
        return False
        
    # check extension
    if not filepath.lower().endswith(('.tif', '.tiff')):
        filepath += ".tif"
        
    # Optional color conversion for OpenCV (expects BGR)
    if color_mode == "rgb" and image_data.ndim == 3 and image_data.shape[2] == 3:
        image_data = cv2.cvtColor(image_data, cv2.COLOR_RGB2BGR)

    # Save (OpenCV handles TIFF if extension is .tif)
    try:
        success = cv2.imwrite(filepath, image_data)
        if not success:
            raise IOError(f"cv2.imwrite failed for {filepath}")
        logging.info(f"Saved image: {filepath}")
        return True
    except Exception as e:
        logging.error(f"Failed to save image: {e}")
        return False

def append_to_log(log_path, data_dict):
    """
    Append a dictionary row to a CSV log file.
    Automatically writes header if file doesn't exist.
    """
    file_exists = os.path.isfile(log_path)
    
    utils.ensure_dir(os.path.dirname(log_path))
    
    fieldnames = [
        "timestamp", "mode", "exposure_us", "gain", 
        "polarizer_angle", "sample_angle", "filepath", 
        "arduino_response", "attempt_count"
    ]
    
    try:
        with open(log_path, mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
                
            # Filter data_dict to only known fields to avoid errors
            row = {k: data_dict.get(k, "") for k in fieldnames}
            writer.writerow(row)
            return True
            
    except Exception as e:
        logging.error(f"Failed to write log {log_path}: {e}")
        return False
