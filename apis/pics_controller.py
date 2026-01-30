import serial
import time
import threading
import logging
from . import config, utils

class PicsController:
    def __init__(self):
        self.ser = None
        self.lock = threading.Lock()
        self.is_connected = False
        self.last_state = config.STATE_LATCHED 
        self.port = None

    def connect(self, port, baud=config.SERIAL_BAUDRATE):
        """
        Connect to Arduino.
        Handshake policy:
        1. Open port (flush I/O).
        2. Wait for 'READY\\n' (Arduino boot message).
        3. If no 'READY' within timeout, assume it's already on and send RESET.
        4. If RESET fails, raise Error.
        """
        self.port = port
        logging.info(f"Connecting to {port} at {baud}...")

        try:
            self.ser = serial.Serial(port, baud, timeout=config.SERIAL_TIMEOUT_S)
            time.sleep(2.0) # wait for DTR reset pulse usually implies boot, but allow time. 
            # Note: On some Arduino/OS combos, opening serial resets the board (bootloader runs).
            # We wait for 'READY'.
            
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            # Attempt 1: Listen for Boot Message
            # Only wait up to CONNECTION_WAIT_S for initial line
            start_t = time.time()
            boot_msg_seen = False
            
            while (time.time() - start_t) < config.CONNECTION_WAIT_S:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line == "READY":
                        boot_msg_seen = True
                        break
                time.sleep(0.1)

            if boot_msg_seen:
                logging.info("Arduino BOOT detected (READY). State is LATCHED.")
                self.is_connected = True
                self.last_state = config.STATE_LATCHED
                # Optional: Send RESET to arm it?
                # Spec says: Boot -> LATCHED. User must explicit Reset to Arm.
                # So we leave it as LATCHED.
                return True

            # Attempt 2: Fallback (Arduino was already on) -> Force RESET
            logging.warning("No READY received. Sending FORCE RESET...")
            resp = self._send_raw_command(config.CMD_RESET, 0)
            if "OK RESET" in resp:
                logging.info("Force RESET successful. Connected & ARMED.")
                self.is_connected = True
                self.last_state = config.STATE_ARMED
                return True
            else:
                raise ConnectionError(f"Failed to connect. Response to RESET: {resp}")

        except Exception as e:
            self.is_connected = False
            if self.ser and self.ser.is_open:
                self.ser.close()
            logging.error(f"Connection failed: {e}")
            raise e

    def disconnect(self):
        with self.lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self.is_connected = False

    def _send_raw_command(self, pp, aaa, retry_count=config.MAX_RETRIES):
        """
        Internal: Send PPAAA, return raw response line.
        Protected by Lock.
        Handles Retries on TIMEOUT.
        """
        cmd_str = utils.format_command(pp, aaa)
        
        # Lock entire I/O transaction
        with self.lock:
            if not self.ser or not self.ser.is_open:
                return "ERR NO_CONNECTION"

            attempt = 0
            while attempt < retry_count:
                try:
                    # Clear input buffer to remove stale data
                    self.ser.reset_input_buffer()
                    
                    # Send
                    full_cmd = f"{cmd_str}\n" 
                    self.ser.write(full_cmd.encode('utf-8'))
                    self.ser.flush()
                    
                    # Read (blocking with timeout from serial init)
                    response = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    
                    if not response:
                        # Timeout
                        attempt += 1
                        logging.warning(f"Timeout cmd={cmd_str} (attempt {attempt}/{retry_count})")
                        # Exponential backoff
                        time.sleep(0.2 * (2 ** (attempt - 1)))
                        continue
                    
                    # We got a response
                    return response

                except Exception as e:
                    logging.error(f"Serial I/O Error: {e}")
                    return f"ERR EXCEPTION {str(e)}"

            return "ERR TIMEOUT"

    def send_command(self, pp, aaa):
        """
        Public API to send command and parse result.
        Returns: True if OK, False if ERR.
        """
        resp = self._send_raw_command(pp, aaa)
        logging.info(f"CMD: {pp:02d}{aaa:03d} -> {resp}")
        
        if resp.startswith("OK"):
            return True
        else:
            # Handle Errors
            return False

    def emergency_stop(self):
        """
        Send ESTOP (99). Always allowed.
        """
        resp = self._send_raw_command(config.CMD_ESTOP, 0)
        if "OK ESTOP" in resp:
            self.last_state = config.STATE_LATCHED
            return True
        return False

    def reset(self):
        """
        Send RESET (98). Always allowed. Arms the system.
        """
        resp = self._send_raw_command(config.CMD_RESET, 0)
        if "OK RESET" in resp:
            self.last_state = config.STATE_ARMED
            return True
        return False

    def home(self):
        """
        Send HOME (96). Allowed only if ARMED.
        """
        if self.last_state == config.STATE_LATCHED:
            logging.error("Ignored HOME while LATCHED.")
            return False
            
        resp = self._send_raw_command(config.CMD_HOME, 0)
        return "OK" in resp

    def rotate_polarizer(self, angle):
        """
        PP=10.
        """
        return self.send_command(config.CMD_POLARIZER, angle)

    def rotate_sample(self, angle):
        """
        PP=11.
        """
        return self.send_command(config.CMD_SAMPLE, angle)

    def get_state(self):
        return self.last_state
