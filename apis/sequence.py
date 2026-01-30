import time
import logging
import os
from . import config, utils, io

class PicsSequence:
    def __init__(self, controller, camera, log_callback=None):
        """
        controller: PicsController instance
        camera: object with set_exposure(us), capture() -> np.array, stop_live(), resume_live()
        log_callback: function(msg) for GUI updates
        """
        self.ctrl = controller
        self.cam = camera
        self.log_cb = log_callback
        self._abort_flag = False
        
    def log(self, msg):
        logging.info(msg)
        if self.log_cb:
            self.log_cb(msg)

    def abort(self):
        self._abort_flag = True
        self.log("Abort requested!")

    def _check_abort(self):
        if self._abort_flag:
            raise InterruptedError("Sequence aborted by user.")

    def _wait_settling(self, duration=config.SETTLING_TIME_S):
        """Sliced wait with abort check."""
        start = time.time()
        while (time.time() - start) < duration:
            self._check_abort()
            time.sleep(0.05) # 50ms slice

    def run_sequence(self, save_dir, sample_id, crosspol_exposure_us, normal_exposure_us, sample_angles=None, do_crosspol=True, do_normal=True):
        self._abort_flag = False
        if sample_angles is None:
            sample_angles = [90, 60, 45, 30, 0] # As per spec
        if not (do_crosspol or do_normal):
            raise RuntimeError("No modes enabled for sequence.")
        
        try:
            self.log("Starting Sequence...")
            
            # 1. Validation
            if not self.ctrl.is_connected:
                raise RuntimeError("Controller not connected.")
            
            # 2. Prepare Directories
            crosspol_dir = None
            normal_dir = None
            if do_crosspol:
                crosspol_dir = os.path.join(save_dir, sample_id, "crosspol")
                utils.ensure_dir(crosspol_dir)
            if do_normal:
                normal_dir = os.path.join(save_dir, sample_id, "normal")
                utils.ensure_dir(normal_dir)
            
            # 3. Pause Live View
            if hasattr(self.cam, 'stop_live'):
                self.cam.stop_live()
                
            # 4. Ensure ARMED
            self.log("Arming system (RESET)...")
            if not self.ctrl.reset():
                raise RuntimeError("Failed to ARM system (RESET command failed).")
                
            if do_crosspol:
                # --- PHASE 1: CROSSPOL ---
                self.log("Phase 1: Crosspol")
                self.cam.set_exposure(crosspol_exposure_us)
                
                # Move Polarizer to 90
                self.log("Moving Polarizer to 90...")
                if not self.ctrl.rotate_polarizer(90):
                   raise RuntimeError("Failed to move Polarizer to 90.")
                self._wait_settling()

                for angle in sample_angles:
                    self._check_abort()
                    self.log(f"Crosspol: Sample {angle} deg")
                    
                    # Move Sample
                    if not self.ctrl.rotate_sample(angle):
                        self.log(f"Error moving sample to {angle}. Retrying once...")
                        if not self.ctrl.rotate_sample(angle):
                             raise RuntimeError(f"Failed moving sample to {angle}")
                    
                    self._wait_settling()
                    
                    # Capture
                    img = self.cam.capture()
                    fname = f"{sample_id}_crosspol_{angle:03d}.tif"
                    fpath = os.path.join(crosspol_dir, fname)
                    io.save_image(fpath, img, color_mode="rgb")
                    
                    # Metalog
                    io.append_to_log(os.path.join(save_dir, sample_id, f"{sample_id}_log.csv"), {
                        "timestamp": utils.get_timestamp_iso(),
                        "mode": "crosspol",
                        "exposure_us": crosspol_exposure_us,
                        "polarizer_angle": 90,
                        "sample_angle": angle,
                        "filepath": fpath,
                        "arduino_response": "OK" 
                    })

            if do_normal:
                # --- PHASE 2: NORMAL ---
                self.log("Phase 2: Normal")
                self.cam.set_exposure(normal_exposure_us)
                
                # Move Polarizer to 0
                self.log("Moving Polarizer to 0...")
                if not self.ctrl.rotate_polarizer(0):
                    raise RuntimeError("Failed to move Polarizer to 0.")
                self._wait_settling()

                for angle in sample_angles:
                    self._check_abort()
                    self.log(f"Normal: Sample {angle} deg")
                    
                    if not self.ctrl.rotate_sample(angle):
                         raise RuntimeError(f"Failed moving sample to {angle}")
                    
                    self._wait_settling()
                    
                    img = self.cam.capture()
                    fname = f"{sample_id}_normal_{angle:03d}.tif"
                    fpath = os.path.join(normal_dir, fname)
                    io.save_image(fpath, img, color_mode="rgb")
                    
                    io.append_to_log(os.path.join(save_dir, sample_id, f"{sample_id}_log.csv"), {
                        "timestamp": utils.get_timestamp_iso(),
                        "mode": "normal",
                        "exposure_us": normal_exposure_us,
                        "polarizer_angle": 0,
                        "sample_angle": angle,
                        "filepath": fpath,
                        "arduino_response": "OK"
                    })

            # Finish
            self.log("Sequence Complete. Homing...")
            self.ctrl.home() # Optional check
            
        except InterruptedError:
            self.log("Sequence Aborted!")
            # Safety: ESTOP on abort? Or just Stop? Spec says "if controlled + still ARMED -> optional HOME then stop"
            # If user explicitly aborted, maybe we just stop. If Error, we might E-Stop.
            # "On abort: ... if controlled error and still ARMED -> optional HOME then stop"
            # I'll just leave it safely.
            
        except Exception as e:
            self.log(f"Sequence Error: {e}")
            # Spec: "treat as communication failure -> ABORT + ESTOP"
            # If it's severe, we ESTOP.
            self.log("Emergency Stop Triggered due to Error.")
            self.ctrl.emergency_stop()
            raise e
            
        finally:
            if hasattr(self.cam, 'resume_live'):
                self.cam.resume_live()
