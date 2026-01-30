import unittest
from unittest.mock import MagicMock, patch
import time
from apis.pics_controller import PicsController
from apis import config

class TestPicsController(unittest.TestCase):
    
    def setUp(self):
        self.ctrl = PicsController()

    @patch('serial.Serial')
    def test_connect_handshake_success(self, mock_serial_cls):
        """Test standard connection where Arduino sends READY."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.in_waiting = True
        mock_ser.readline.return_value = b'READY\n'
        
        success = self.ctrl.connect("COM3")
        
        self.assertTrue(success)
        self.assertTrue(self.ctrl.is_connected)
        self.assertEqual(self.ctrl.last_state, config.STATE_LATCHED) # Boot = Latched

    @patch('serial.Serial')
    def test_connect_handshake_timeout_reset(self, mock_serial_cls):
        """Test connection where READY is missed, so RESET is sent."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        
        # Behavior: 
        # 1. No "READY" (in_waiting=False or readline empty)
        # 2. Controller sends RESET (98000)
        # 3. Controller reads "OK RESET"
        
        mock_ser.in_waiting = False # Simulate silence
        
        # When write is called (RESET), subsequent read should return OK RESET
        def side_effect_readline():
            return b'OK RESET\n'
            
        mock_ser.readline.side_effect = [b'', b'', b'OK RESET\n'] # A few empty reads then response
        
        # Speed up waits
        with patch('time.sleep', return_value=None):
            config.CONNECTION_WAIT_S = 0.1 # Shorten wait
            success = self.ctrl.connect("COM3")
            
        self.assertTrue(success)
        self.assertTrue(self.ctrl.is_connected)
        self.assertEqual(self.ctrl.last_state, config.STATE_ARMED) # Reset = Armed
        
        # Verify RESET was sent
        mock_ser.write.assert_called()
        args, _ = mock_ser.write.call_args
        self.assertIn(b'98000', args[0])

    @patch('serial.Serial')
    def test_send_command_success(self, mock_serial_cls):
        """Test sending a move command receiving OK."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.is_open = True
        
        # Setup connection manually
        self.ctrl.ser = mock_ser
        self.ctrl.is_connected = True
        
        mock_ser.readline.return_value = b'OK 10 090\n'
        
        success = self.ctrl.rotate_polarizer(90)
        self.assertTrue(success)
        mock_ser.write.assert_called_with(b'10090\n')

    @patch('serial.Serial')
    def test_emergency_stop(self, mock_serial_cls):
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.is_open = True
        self.ctrl.ser = mock_ser
        self.ctrl.is_connected = True
        
        mock_ser.readline.return_value = b'OK ESTOP\n'
        
        success = self.ctrl.emergency_stop()
        self.assertTrue(success)
        self.assertEqual(self.ctrl.last_state, config.STATE_LATCHED)
        mock_ser.write.assert_called_with(b'99000\n')

    @patch('serial.Serial')
    def test_retry_on_timeout(self, mock_serial_cls):
        """Test that controller retries on empty response."""
        mock_ser = MagicMock()
        mock_serial_cls.return_value = mock_ser
        mock_ser.is_open = True
        self.ctrl.ser = mock_ser
        self.ctrl.is_connected = True
        
        # Returns: Empty (timeout), Empty (timeout), OK (success)
        mock_ser.readline.side_effect = [b'', b'', b'OK 11 045\n']
        
        with patch('time.sleep', return_value=None): # Skip backoff wait
            success = self.ctrl.rotate_sample(45)
            
        self.assertTrue(success)
        self.assertEqual(mock_ser.write.call_count, 3) # Tried 3 times

if __name__ == '__main__':
    unittest.main()
