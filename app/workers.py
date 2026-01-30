import sys
import os
import time
import logging
import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QWaitCondition
import numpy as np
from apis import config

# Add project root if needed
sys.path.append(".")

# --- Dummy Camera Simulation (Replace with XIMEA SDK later) ---
class DummyCamera:
    def __init__(self):
        self.exposure_us = 12000
        self.gain = 0.0
        self.width = 640
        self.height = 480
        self._streaming = False
        self.is_open = False

    def check_available(self):
        return True

    def open(self):
        self.is_open = True
        logging.info("Dummy Camera Opened.")

    def close(self):
        self.is_open = False
        self._streaming = False
        logging.info("Dummy Camera Closed.")

    def start_acquisition(self):
        self._streaming = True

    def stop_acquisition(self):
        self._streaming = False

    def set_exposure(self, us):
        self.exposure_us = us
        logging.info(f"CAM: Exposure set to {us} us")

    def set_gain(self, gain):
        self.gain = gain
        logging.info(f"CAM: Gain set to {gain}")
        
    def get_image(self):
        if not self._streaming:
            return None
        # Simulate an image pattern
        img = np.zeros((self.height, self.width), dtype=np.uint8)
        # Moving stripe to show life
        t = int(time.time() * 20) % self.width
        cv2.line(img, (t, 0), (t, self.height), 255, 3)
        # Add noise based on gain
        if self.gain > 0:
            noise = np.random.normal(0, self.gain * 5, img.shape).astype(np.uint8)
            img = cv2.add(img, noise)
        return img
    
    def capture(self):
        """Simulate single capture for sequence"""
        return self.get_image()
    
    def stop_live(self):
        self._streaming = False
        
    def resume_live(self):
        self._streaming = True

# --- Real XIMEA Camera Wrapper ---
class XimeaCamera:
    def __init__(self):
        self._cam = None
        self._streaming = False
        self.exposure_us = 12000
        self.gain = 0.0
        self.is_open = False
        
        try:
            from ximea import xiapi
            self.xiapi = xiapi
            logging.info("XIMEA SDK found.")
        except ImportError:
            self._try_add_ximea_path()
            try:
                from ximea import xiapi
                self.xiapi = xiapi
                logging.info("XIMEA SDK found via system path.")
            except ImportError:
                self.xiapi = None
                logging.warning("XIMEA SDK not found. Install 'ximea' package.")

    def _try_add_ximea_path(self):
        # Add default XIMEA Python API path if present and not already on sys.path
        candidates = [
            r"C:\XIMEA\API\Python\v3",
        ]
        for p in candidates:
            if os.path.isdir(p) and p not in sys.path:
                sys.path.append(p)

    def check_available(self):
        return self.xiapi is not None

    def open(self):
        if not self.xiapi:
            raise RuntimeError("XIMEA SDK not installed.")
        
        self._cam = self.xiapi.Camera()
        self._cam.open_device() # Open first available
        
        # Log device info
        model_name = self._cam.get_device_name()
        serial_num = self._cam.get_device_sn()
        logging.info(f"XIMEA: Model={model_name}, Serial={serial_num}")
        
        # Configure default from Reference Code
        try:
            self._cam.set_imgdataformat('XI_RGB24')
            self._cam.set_exposure(10000) # 10ms default (Reduced from 50ms to prevent saturation)
            self._cam.set_gain(0.0)
            try:
                fmt = self._cam.get_imgdataformat()
                logging.info(f"XIMEA: imgdataformat={fmt}")
            except Exception:
                logging.warning("XIMEA: get_imgdataformat not available.")
            
            # White Balance (Reference values - Commented out for test)
            # If colors look gray, these specific gains might be cancelling them out for this light source
            # if self._cam.is_auto_wb():
            #      self._cam.disable_auto_wb()
            # self._cam.set_wb_kr(1.531)
            # self._cam.set_wb_kg(1.0)
            # self._cam.set_wb_kb(1.305)
            
            # Enable Auto WB if available for better color in general lighting
            if not self._cam.is_auto_wb():
                self._cam.enable_auto_wb()
            
            # Disable Auto Exposure / Gain (Critical)
            self._cam.disable_aeag()
            
            # Data output safety
            # self._cam.set_output_data_bit_depth(8) # Ensure 8-bit if needed

            # Ensure Free Run (Disable Trigger)
            try:
                self._cam.set_trigger_source('XI_TRG_OFF')
            except Exception:
                pass 
            
            # self._cam.start_acquisition() # Removed for per-frame acquisition
            self.is_open = True
            self._streaming = True
            logging.info("XIMEA Camera Opened (Ref Settings Applied).")
            
        except Exception as e:
            # If config fails, close
            try:
                self._cam.close_device()
            except: 
                pass
            raise e

    def close(self):
        if self._cam and self.is_open:
            try:
                self._cam.stop_acquisition()
            except: pass
            self._cam.close_device()
            self.is_open = False
            self._streaming = False
            logging.info("XIMEA Camera Closed.")

    def start_acquisition(self):
        self._streaming = True

    def stop_acquisition(self):
        self._streaming = False

    def set_exposure(self, us):
        self.exposure_us = us
        if self.is_open:
            try:
                self._cam.set_exposure(us)
            except Exception as e:
                logging.error(f"CAM Set Exposure Error: {e}")

    def set_gain(self, gain):
        self.gain = gain
        if self.is_open:
            try:
                self._cam.set_gain(gain)
            except Exception as e:
                logging.error(f"CAM Set Gain Error: {e}")
        
    def get_image(self):
        # Only check if camera is open - _streaming is irrelevant for per-frame acquisition
        if not self.is_open:
            print("DEBUG: get_image() called but camera not open")
            return None
        
        try:
            # Start-Get-Stop Pattern (from reference code)
            self._cam.start_acquisition()
            
            img = self.xiapi.Image()
            self._cam.get_image(img)  # NO TIMEOUT - reference code style
            data = img.get_image_data_numpy(invert_rgb_order=True)  # CRITICAL!
            
            self._cam.stop_acquisition()
            return data
        except Exception as e:
            # Try to stop if stuck
            try: self._cam.stop_acquisition()
            except: pass
            
            print(f"DEBUG: XIMEA get_image failed: {e}")
            return None
    
    def capture(self):
        return self.get_image()
    
    def stop_live(self):
        self._streaming = False
        
    def resume_live(self):
        self._streaming = True

class CameraThread(QThread):
    new_frame = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str) # New signal for errors
    
    def __init__(self, camera_obj=None):
        super().__init__()
        self.cam = camera_obj if camera_obj else DummyCamera()
        self._running = False
        self._paused = False
        self.fps = 30
        self._cam_mutex = QMutex()
        
    def run(self):
        self._running = True
        print("DEBUG: CameraThread Started")
        
        # Ensure camera is open
        try:
             if hasattr(self.cam, 'open'):
                 self.cam.open()
             # NOTE: DO NOT call start_acquisition here!
             # XimeaCamera.get_image() handles start/stop internally.
        except Exception as e:
             logging.error(f"Camera Start Error: {e}")
             self.error_occurred.emit(f"Failed to open camera: {str(e)}")
             self._running = False
             return

        while self._running:
            if not self._paused:
                self._cam_mutex.lock()
                try:
                    frame = self.cam.get_image()
                finally:
                    self._cam_mutex.unlock()
                if frame is not None:
                    #print(f"DEBUG: Emitting Frame {frame.shape}")
                    self.new_frame.emit(frame)
                else:
                    # print("DEBUG: Frame is None")
                    pass
            time.sleep(1.0 / self.fps)
            
    def stop(self):
        self._running = False
        self.wait()
        self.cam.stop_acquisition()

    def set_pause(self, paused):
        self._paused = paused
        if paused:
            self.cam.stop_live()
        else:
            self.cam.resume_live()
            
    def set_exposure(self, us):
        self.cam.set_exposure(us)
        
    def set_gain(self, g):
        self.cam.set_gain(g)

    def capture_frame(self):
        """Safely grab a single frame while the thread may be running."""
        self._cam_mutex.lock()
        try:
            return self.cam.get_image()
        finally:
            self._cam_mutex.unlock()


class SequenceThread(QThread):
    progress_update = pyqtSignal(str) # Status message
    progress_val = pyqtSignal(int)    # 0-100
    finished_ok = pyqtSignal()
    error_occurred = pyqtSignal(str)
    
    def __init__(self, sequence_logic, save_dir, sample_id, exp_crosspol, exp_normal, angles, do_crosspol, do_normal):
        super().__init__()
        self.seq = sequence_logic
        self.save_dir = save_dir
        self.sample_id = sample_id
        self.exp_crosspol = exp_crosspol
        self.exp_normal = exp_normal
        self.angles = angles
        self.do_crosspol = do_crosspol
        self.do_normal = do_normal
        
        # Override log callback to emit signal
        self.seq.log_cb = self._on_log
        
        # Calculate total steps for progress bar
        phase_count = int(self.do_crosspol) + int(self.do_normal)
        self.total_steps = max(1, len(self.angles) * phase_count)
        self.current_step = 0

    def _on_log(self, msg):
        self.progress_update.emit(msg)
        # Crude progress estimation based on keywords
        if "Sample" in msg:
            self.current_step += 1
            pct = int((self.current_step / self.total_steps) * 100)
            self.progress_val.emit(pct)

    def run(self):
        try:
            self.current_step = 0
            self.progress_val.emit(0)
            self.seq.run_sequence(
                self.save_dir, 
                self.sample_id, 
                self.exp_crosspol, 
                self.exp_normal,
                self.angles,
                self.do_crosspol,
                self.do_normal
            )
            self.progress_val.emit(100)
            self.finished_ok.emit()
            
        except InterruptedError:
            self.error_occurred.emit("Sequence Aborted by User")
            
        except Exception as e:
            self.error_occurred.emit(f"Sequence Error: {str(e)}")

    def abort(self):
        self.seq.abort()
