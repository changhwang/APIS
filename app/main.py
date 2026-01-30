import sys
import os
import time
import logging
import ctypes
import cv2
import re
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QComboBox, QGroupBox, QSpinBox, QCheckBox,
    QDoubleSpinBox, QSlider, QLineEdit, QProgressBar, QTextEdit, 
    QFileDialog, QMessageBox, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer
from PyQt6.QtGui import QImage, QPixmap, QColor, QPalette, QIcon

# Add project root to path
sys.path.append(".") 

from apis.controller import PicsController
from apis.sequence import PicsSequence
from apis import config, utils, io
from app.workers import CameraThread, SequenceThread, DummyCamera, XimeaCamera

# --- UI STATES ---
STATE_DISCONNECTED = "DISCONNECTED"
STATE_LATCHED = config.STATE_LATCHED # "LATCHED"
STATE_ARMED = config.STATE_ARMED     # "ARMED"
STATE_RUNNING = "RUNNING"
STATE_ERROR = "ERROR"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APIS (Automated Polarization Imaging System)")
        icon_candidates = [
            os.path.join(os.path.dirname(__file__), "assets", "apis_logo.png"),
            os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"),
            os.path.join(os.path.dirname(__file__), "assets", "icon.ico"),
        ]
        for icon_path in icon_candidates:
            if os.path.isfile(icon_path):
                self.setWindowIcon(QIcon(icon_path))
                break
        self.resize(1400, 850)
        
        # 1. Init Base State & UI (Required for Logging)
        self.current_state = STATE_DISCONNECTED
        self.init_ui()
        
        # --- Logic Objects ---
        self.ctrl = PicsController()
        
        # Camera Initialization strategy
        # 1. Try XimeaCamera
        # 2. Fallback to DummyCamera if SDK missing
        self.cam = XimeaCamera()
        if not self.cam.check_available():
            logging.warning("Ximea SDK missing. Using Dummy Camera.")
            self.cam = DummyCamera()
            self.log("Initialized: DummyCamera (Simulation)", "WARN")
        else:
            self.log("Initialized: XimeaCamera (Hardware)")
            
        self.sequence_logic = PicsSequence(self.ctrl, self.cam)
        
        self.cam_thread = None
        self.seq_thread = None
        self._logged_frame_info = False
        self._logged_channel_stats = False
        self._force_bgr_swap = False
        self._last_frame_rgb = None
        self._exp_cross_last = 50000
        self._exp_normal_last = 12000
        
        # Initial UI Update
        self.update_state_ui(STATE_DISCONNECTED)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # 0. LOGGING (Must be first)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        
        # Redirect Logger to UI
        logging.getLogger().setLevel(logging.INFO)

        # 1. TOP: SAFETY BAR
        self.safety_bar = self.create_safety_bar()
        main_layout.addWidget(self.safety_bar)

        # 2. MIDDLE: Split 3 Columns (Left: Devices, Center: Live, Right: Sequence)
        content_layout = QHBoxLayout()
        
        # Left Panel (Devices & Manual)
        left_panel = QVBoxLayout()
        left_panel.addWidget(self.create_connection_group())
        left_panel.addWidget(self.create_camera_settings_group())
        left_panel.addWidget(self.create_manual_control_group())
        left_panel.addStretch()
        content_layout.addLayout(left_panel, 1)

        # Center Panel (Live View)
        center_panel = QVBoxLayout()
        center_panel.addWidget(self.create_live_view_group())
        content_layout.addLayout(center_panel, 2)

        # Right Panel (Sequence)
        right_panel = QVBoxLayout()
        right_panel.addWidget(self.create_sequence_group())
        right_panel.addStretch()
        content_layout.addLayout(right_panel, 1)

        main_layout.addLayout(content_layout)

        # 3. BOTTOM: LOG
        log_layout = QHBoxLayout()
        self.btn_log_copy = QPushButton("Copy Log")
        self.btn_log_copy.clicked.connect(self.on_log_copy)
        self.btn_log_save = QPushButton("Save Log")
        self.btn_log_save.clicked.connect(self.on_log_save)
        log_layout.addStretch()
        log_layout.addWidget(self.btn_log_copy)
        log_layout.addWidget(self.btn_log_save)

        main_layout.addWidget(self.log_text)
        main_layout.addLayout(log_layout)
        
        # Redirect Logger to UI
        logging.getLogger().setLevel(logging.INFO)
        # (A fuller impl would attach a custom Handler, 
        #  here we just wrap log calls or rely on console for now + my log helper)
        
    def log(self, msg, level="INFO"):
        """Append log message to text area"""
        ts = time.strftime("%H:%M:%S")
        state = self.current_state
        formatted = f"[{ts}][{state}][{level}] {msg}"
        self.log_text.append(formatted)
        # Auto scroll
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())
        print(formatted) # console backup

    # --- UI CREATION HELPERS ---
    
    def create_safety_bar(self):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("background-color: #eee; border: 1px solid #ccc;")
        layout = QHBoxLayout(frame)
        
        self.lbl_status = QLabel("Controller: DISCONNECTED")
        self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
        
        self.lbl_cam_status = QLabel(" | Camera: DISCONNECTED")
        self.lbl_cam_status.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")

        self.lbl_info = QLabel(" | Pol: -- | Samp: -- | Exp: -- us | Gain: -- dB")
        self.lbl_info.setStyleSheet("font-size: 14px; color: #333;")
        
        self.btn_estop = QPushButton("E-STOP")
        self.btn_estop.setStyleSheet("background-color: red; color: white; font-weight: bold; font-size: 16px; padding: 10px;")
        self.btn_estop.clicked.connect(self.on_estop)
        
        self.btn_reset = QPushButton("RESET / ARM")
        self.btn_reset.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 16px; padding: 10px;")
        self.btn_reset.clicked.connect(self.on_reset)
        
        self.btn_home = QPushButton("HOME")
        self.btn_home.setStyleSheet("background-color: #e0e0e0; color: black; font-weight: bold; font-size: 16px; padding: 10px;")
        self.btn_home.clicked.connect(self.on_home)
        
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.lbl_cam_status)
        layout.addWidget(self.lbl_info)
        layout.addStretch()
        layout.addWidget(self.btn_home)
        layout.addWidget(self.btn_reset)
        layout.addWidget(self.btn_estop)
        return frame

    def create_connection_group(self):
        grp = QGroupBox("Device Connections")
        layout = QGridLayout()
        
        # --- Arduino Section ---
        layout.addWidget(QLabel("<b>Arduino Controller</b>"), 0, 0, 1, 3)
        
        layout.addWidget(QLabel("Port:"), 1, 0)
        self.cmb_port = QComboBox()
        self.on_refresh_ports() # Populate initially
        layout.addWidget(self.cmb_port, 1, 1)
        
        self.btn_refresh = QPushButton("↻")
        self.btn_refresh.setFixedWidth(30)
        self.btn_refresh.setToolTip("Refresh COM Ports")
        self.btn_refresh.clicked.connect(self.on_refresh_ports)
        layout.addWidget(self.btn_refresh, 1, 2)
        
        self.btn_connect = QPushButton("Connect Controller")
        self.btn_connect.clicked.connect(self.on_toggle_connect)
        layout.addWidget(self.btn_connect, 2, 0, 1, 3)
        
        # --- Camera Section ---
        layout.addWidget(QLabel("<b>Camera</b>"), 3, 0, 1, 3)
        
        self.btn_cam_connect = QPushButton("Connect Camera")
        self.btn_cam_connect.clicked.connect(self.on_toggle_camera)
        layout.addWidget(self.btn_cam_connect, 4, 0, 1, 3)
        
        grp.setLayout(layout)
        return grp

    def create_camera_settings_group(self):
        grp = QGroupBox("Camera Settings")
        layout = QGridLayout()
        
        layout.addWidget(QLabel("Exposure (us):"), 0, 0)
        self.spin_exp = QSpinBox()
        self.spin_exp.setRange(100, 1000000)
        self.spin_exp.setValue(12000)
        self.spin_exp.setSingleStep(1000)
        layout.addWidget(self.spin_exp, 0, 1)
        
        layout.addWidget(QLabel("Gain (dB):"), 1, 0)
        self.spin_gain = QDoubleSpinBox()
        self.spin_gain.setRange(0.0, 24.0)
        self.spin_gain.setValue(0.0)
        layout.addWidget(self.spin_gain, 1, 1)
        
        self.btn_cam_apply = QPushButton("Apply Settings")
        self.btn_cam_apply.clicked.connect(self.on_cam_apply)
        layout.addWidget(self.btn_cam_apply, 2, 0, 1, 2)

        self.spin_exp.valueChanged.connect(self.update_status_info)
        self.spin_gain.valueChanged.connect(self.update_status_info)
        
        lbl_rec = QLabel("Rec: Crosspol=50,000us (50ms), Normal=12,000us (12ms)")
        lbl_rec.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(lbl_rec, 3, 0, 1, 2)
        
        grp.setLayout(layout)
        return grp

    def create_manual_control_group(self):
        grp = QGroupBox("Manual Motor Control (Absolute Movement)")
        layout = QGridLayout()
        
        # Polarizer
        layout.addWidget(QLabel("Polarizer (Pin 10):"), 0, 0, 1, 2)
        self.spin_pol = QSpinBox()
        self.spin_pol.setRange(0, 180)
        self.btn_move_pol = QPushButton("Move")
        self.btn_move_pol.clicked.connect(lambda: self.on_manual_move(10))
        self.btn_pol_p45 = QPushButton("+45")
        self.btn_pol_p45.clicked.connect(lambda: self.on_add_angle(self.spin_pol, 45))
        
        layout.addWidget(self.spin_pol, 1, 0)
        layout.addWidget(self.btn_move_pol, 1, 1)
        layout.addWidget(self.btn_pol_p45, 1, 2)
        
        # Sample
        layout.addWidget(QLabel("Sample (Pin 11):"), 2, 0, 1, 2)
        self.spin_samp = QSpinBox()
        self.spin_samp.setRange(0, 180)
        self.btn_move_samp = QPushButton("Move")
        self.btn_move_samp.clicked.connect(lambda: self.on_manual_move(11))
        self.btn_samp_p45 = QPushButton("+45")
        self.btn_samp_p45.clicked.connect(lambda: self.on_add_angle(self.spin_samp, 45))
        
        layout.addWidget(self.spin_samp, 3, 0)
        layout.addWidget(self.btn_move_samp, 3, 1)
        layout.addWidget(self.btn_samp_p45, 3, 2)
        
        grp.setLayout(layout)
        return grp

    def create_live_view_group(self):
        grp = QGroupBox("Live View")
        layout = QVBoxLayout()
        
        self.lbl_live = QLabel("No Signal")
        self.lbl_live.setMinimumSize(640, 480)
        self.lbl_live.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_live.setStyleSheet("background-color: black; color: white;")
        layout.addWidget(self.lbl_live)
        
        self.lbl_live_overlay = QLabel("LIVE PAUSED (Sequence Running)", self.lbl_live)
        self.lbl_live_overlay.setStyleSheet("color: yellow; font-size: 24px; font-weight: bold; background: rgba(0,0,0,150);")
        self.lbl_live_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_live_overlay.setGeometry(0, 200, 640, 80)
        self.lbl_live_overlay.hide()
        
        controls = QHBoxLayout()

        controls.addWidget(QLabel("Filename:"))
        self.edt_snapshot_name = QLineEdit("snapshot")
        self.edt_snapshot_name.setFixedWidth(160)
        controls.addWidget(self.edt_snapshot_name)

        controls.addWidget(QLabel("Save Dir:"))
        self.edt_snapshot_dir = QLineEdit(os.path.join(os.getcwd(), "data"))
        controls.addWidget(self.edt_snapshot_dir)
        self.btn_snapshot_browse = QPushButton("...")
        self.btn_snapshot_browse.setFixedWidth(28)
        self.btn_snapshot_browse.clicked.connect(self.on_snapshot_browse)
        controls.addWidget(self.btn_snapshot_browse)

        controls.addStretch()

        self.btn_snap = QPushButton("Snapshot")
        self.btn_snap.setFixedWidth(110)
        self.btn_snap.clicked.connect(self.on_snapshot)
        controls.addWidget(self.btn_snap)

        layout.addLayout(controls)  # Attach controls to main layout
        
        grp.setLayout(layout)  # CRITICAL: Set layout on group!
        grp.setEnabled(False) # Disabled until camera connects
        self.grp_live = grp
        return grp

    def create_sequence_group(self):
        grp = QGroupBox("Sequence Control")
        layout = QGridLayout()
        
        layout.addWidget(QLabel("Save Directory:"), 0, 0)
        self.edt_save_dir = QLineEdit(os.path.join(os.getcwd(), "data"))
        layout.addWidget(self.edt_save_dir, 0, 1)
        self.btn_browse = QPushButton("...")
        self.btn_browse.clicked.connect(self.on_browse)
        layout.addWidget(self.btn_browse, 0, 2)
        
        layout.addWidget(QLabel("Sample ID:"), 1, 0)
        self.edt_sample_id = QLineEdit("TestSample")
        layout.addWidget(self.edt_sample_id, 1, 1, 1, 2)
        
        layout.addWidget(QLabel("Modes:"), 2, 0)
        modes_box = QHBoxLayout()
        self.chk_crosspol = QCheckBox("Crosspol")
        self.chk_crosspol.setChecked(True)
        self.chk_normal = QCheckBox("Normal")
        self.chk_normal.setChecked(True)
        self.chk_crosspol.toggled.connect(self.on_seq_mode_toggle)
        self.chk_normal.toggled.connect(self.on_seq_mode_toggle)
        modes_box.addWidget(self.chk_crosspol)
        modes_box.addWidget(self.chk_normal)
        modes_widget = QWidget()
        modes_widget.setLayout(modes_box)
        layout.addWidget(modes_widget, 2, 1, 1, 2)
        
        layout.addWidget(QLabel("Crosspol Exposure (us):"), 3, 0)
        self.spin_exp_cross = QSpinBox()
        self.spin_exp_cross.setRange(100, 1000000)
        self.spin_exp_cross.setValue(50000)
        self.spin_exp_cross.setSingleStep(1000)
        layout.addWidget(self.spin_exp_cross, 3, 1, 1, 2)
        
        layout.addWidget(QLabel("Normal Exposure (us):"), 4, 0)
        self.spin_exp_normal = QSpinBox()
        self.spin_exp_normal.setRange(100, 1000000)
        self.spin_exp_normal.setValue(12000)
        self.spin_exp_normal.setSingleStep(1000)
        layout.addWidget(self.spin_exp_normal, 4, 1, 1, 2)
        
        layout.addWidget(QLabel("Angles (deg):"), 5, 0)
        self.edt_angles = QLineEdit("90,60,45,30,0")
        self.edt_angles.setToolTip("List or range. Examples: 0,30,60 or 0:180:15")
        layout.addWidget(self.edt_angles, 5, 1, 1, 2)
        
        layout.addWidget(QLabel("Settling Time (s, motor settle):"), 6, 0)
        self.spin_settling = QDoubleSpinBox()
        self.spin_settling.setRange(0.1, 10.0)
        self.spin_settling.setValue(config.SETTLING_TIME_S)
        layout.addWidget(self.spin_settling, 6, 1)

        self.btn_start = QPushButton("START SEQUENCE")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_start.clicked.connect(self.on_start_sequence)
        layout.addWidget(self.btn_start, 7, 0, 1, 3)
        
        self.progress = QProgressBar()
        layout.addWidget(self.progress, 8, 0, 1, 3)
        
        self.lbl_seq_status = QLabel("Idle")
        layout.addWidget(self.lbl_seq_status, 9, 0, 1, 3)
        
        grp.setLayout(layout)
        return grp

    # --- LOGIC SLOTS ---

    def on_refresh_ports(self):
        self.cmb_port.clear()
        import serial.tools.list_ports
        ports = [p.device for p in serial.tools.list_ports.comports()]
        def port_key(name):
            m = re.search(r"COM(\d+)", name, re.IGNORECASE)
            return (int(m.group(1)) if m else 10**9, name)
        for dev in sorted(ports, key=port_key):
            self.cmb_port.addItem(dev)
        self.log("COM ports refreshed.")
    
    def on_toggle_connect(self):
        """Arduino Connection Toggle"""
        if self.ctrl.is_connected:
            # Disconnect
            self.ctrl.disconnect()
            self.update_state_ui(STATE_DISCONNECTED)
            self.btn_connect.setText("Connect Controller")
            self.log("Disconnected from Arduino.")
        else:
            # Connect
            port = self.cmb_port.currentText()
            if not port:
                QMessageBox.warning(self, "No Port", "Please select a COM port.")
                return
            try:
                self.ctrl.connect(port)
                # Successful connect logic
                init_state = self.ctrl.get_state() # Should be LATCHED or ARMED (if we reset)
                self.update_state_ui(init_state)
                self.btn_connect.setText("Disconnect Controller")
                self.log(f"Connected to {port}. State: {init_state}")
            except Exception as e:
                QMessageBox.critical(self, "Connection Failed", str(e))
                self.log(f"Connection Error: {e}", "ERROR")


    def on_toggle_camera(self):
        """Camera Connection Toggle"""
        if self.cam_thread:
            # Disconnect
            self.cam_thread.stop()
            self.cam_thread = None
            self.btn_cam_connect.setText("Connect Camera")
            self.grp_camera = self.findChild(QGroupBox, "Camera Settings")
            if self.grp_camera:
                self.grp_camera.setEnabled(False)
            if self.grp_live:
                self.grp_live.setEnabled(False)
            self.log("Camera Disconnected.")
            self.lbl_live.setText("Camera Disconnected")
            
            self.lbl_cam_status.setText(" | Camera: DISCONNECTED")
            self.lbl_cam_status.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
        else:
            # Connect
            try:
                self.cam_thread = CameraThread(self.cam)
                self.cam_thread.new_frame.connect(self.on_new_frame)
                self.cam_thread.error_occurred.connect(self.on_cam_error) # Connect Error Signal
                self.cam_thread.start()
                
                self.btn_cam_connect.setText("Disconnect Camera")
                self.grp_camera = self.findChild(QGroupBox, "Camera Settings")
                if self.grp_camera:
                    self.grp_camera.setEnabled(True)
                if self.grp_live:
                    self.grp_live.setEnabled(True)
                self.log("Camera Connected.")
                
                self.lbl_cam_status.setText(" | Camera: CONNECTED")
                self.lbl_cam_status.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
            except Exception as e:
                 QMessageBox.critical(self, "Camera Error", str(e))

    def on_estop(self):
        self.log(">>> EMERGENCY STOP PRESSED <<<", "ERROR")
        
        # 1. Hardware ESTOP
        if self.ctrl.is_connected:
            self.ctrl.emergency_stop()
        
        # 2. Logic ESTOP
        if self.seq_thread and self.seq_thread.isRunning():
            self.seq_thread.abort()
            self.seq_thread.terminate() # Forceful term if needed, but abort flag preferred
            self.seq_thread = None
            
        # 3. UI Latch
        self.update_state_ui(STATE_LATCHED)

    def on_reset(self):
        if not self.ctrl.is_connected:
            return

        # If Running Sequence, Ask User
        if self.current_state == STATE_RUNNING:
            ans = QMessageBox.warning(self, "Abort?", "Sequence is running. Abort and Reset?", 
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans == QMessageBox.StandardButton.No:
                return
            # If Yes, Abort logic first
            if self.seq_thread:
                self.seq_thread.abort()
                
        # Send Reset
        if self.ctrl.reset():
            self.log("System RESET / ARMED.")
            self.update_state_ui(STATE_ARMED)
        else:
            self.log("RESET Failed.", "ERROR")

    def on_home(self):
        if self.ctrl.home():
            self.log("CMD: HOME sent.")
            self.spin_pol.setValue(0)
            self.spin_samp.setValue(0)
            self.update_status_info()
        else:
            self.log("HOME Failed (Check if ARMED).", "WARN")

    def on_manual_move(self, pin):
        if self.current_state not in [STATE_ARMED]:
            self.log("Cannot move: System not ARMED.", "WARN")
            return
            
        if pin == 10:
            val = self.spin_pol.value()
            if self.ctrl.rotate_polarizer(val):
                self.log(f"Polarizer -> {val}")
                self.update_status_info()
        elif pin == 11:
            val = self.spin_samp.value()
            if self.ctrl.rotate_sample(val):
                self.log(f"Sample -> {val}")
                self.update_status_info()

    def on_add_angle(self, spinbox, deg):
        val = spinbox.value() + deg
        if val > 180: val = 180
        spinbox.setValue(val)

    def on_start_sequence(self):
        # Validation
        if self.current_state != STATE_ARMED:
             QMessageBox.warning(self, "Not Armed", "System must be ARMED to start sequence.")
             return
        
        do_crosspol = self.chk_crosspol.isChecked()
        do_normal = self.chk_normal.isChecked()
        if not (do_crosspol or do_normal):
            QMessageBox.warning(self, "No Modes", "Enable at least one mode (Crosspol or Normal).")
            return
             
        save_dir = self.edt_save_dir.text()
        sid = self.edt_sample_id.text()
        settling = self.spin_settling.value()
        exp_cross = self.spin_exp_cross.value()
        exp_normal = self.spin_exp_normal.value()
        angles, angle_err = self.parse_angles(self.edt_angles.text())
        if not angles:
            msg = "Enter angles as comma/space list or range.\nExamples: 0,30,60 or 0:180:15"
            if angle_err:
                msg = f"{angle_err}\n\n{msg}"
            QMessageBox.warning(self, "Invalid Angles", msg)
            return
        
        # Update config
        config.SETTLING_TIME_S = settling
        
        # UI -> RUNNING
        self.update_state_ui(STATE_RUNNING)
        self.lbl_seq_status.setText("Running...")
        self.log(f"Starting Sequence for {sid}...")
        
        # Pause Live View
        if self.cam_thread:
            self.cam_thread.set_pause(True)
        self.lbl_live_overlay.show()

        self.update_status_info()
        
        # Start Thread
        self.seq_thread = SequenceThread(
            self.sequence_logic, 
            save_dir, 
            sid, 
            exp_cross,
            exp_normal,
            angles,
            do_crosspol,
            do_normal
        )
        self.seq_thread.progress_update.connect(self.on_seq_progress_msg)
        self.seq_thread.progress_val.connect(self.progress.setValue)
        self.seq_thread.finished_ok.connect(self.on_seq_finished)
        self.seq_thread.error_occurred.connect(self.on_seq_error)
        self.seq_thread.start()

    def on_seq_progress_msg(self, msg):
        self.lbl_seq_status.setText(msg)
        self.log(msg)

    def on_seq_finished(self):
        self.log("Sequence Finished Successfully.")
        self.restore_ui_after_sequence()
        
    def on_seq_error(self, err_msg):
        self.log(err_msg, "ERROR")
        QMessageBox.critical(self, "Sequence Error", err_msg)
        self.update_state_ui(STATE_ERROR)
        self.restore_ui_after_sequence()
        
    def restore_ui_after_sequence(self):
        self.lbl_live_overlay.hide()
        if self.cam_thread:
            self.cam_thread.set_pause(False)
            
        # Check actual state logic
        if self.ctrl.is_connected:
             self.update_state_ui(self.ctrl.get_state())
        else:
             self.update_state_ui(STATE_DISCONNECTED)

    def on_cam_apply(self):
        if self.cam_thread:
            exp = self.spin_exp.value()
            gain = self.spin_gain.value()
            self.cam_thread.set_exposure(exp)
            self.cam_thread.set_gain(gain)
            self.log(f"Camera Params Applied: {exp}us, {gain}dB")
            self.update_status_info()

    def on_snapshot(self):
        if self._last_frame_rgb is not None:
            base = self.edt_snapshot_name.text().strip() or "snapshot"
            fname = f"{base}_{int(time.time())}.tif"
            save_dir = self.edt_snapshot_dir.text()
            path = os.path.join(save_dir, fname)
            io.save_image(path, self._last_frame_rgb, color_mode="rgb")
            io.append_to_log(os.path.join(save_dir, "snapshot_log.csv"), {
                "timestamp": utils.get_timestamp_iso(),
                "mode": "snapshot",
                "exposure_us": self.spin_exp.value(),
                "gain": self.spin_gain.value(),
                "filepath": path,
            })
            self.log(f"Snapshot saved: {path}")
            return

        if self.cam_thread:
            img = self.cam_thread.capture_frame()
            if img is not None:
                if img.ndim == 2:
                    img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
                elif img.ndim == 3 and img.shape[2] == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
                elif img.ndim == 3 and img.shape[2] == 3 and self._force_bgr_swap:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                base = self.edt_snapshot_name.text().strip() or "snapshot"
                fname = f"{base}_{int(time.time())}.tif"
                save_dir = self.edt_snapshot_dir.text()
                path = os.path.join(save_dir, fname)
                io.save_image(path, img, color_mode="rgb")
                io.append_to_log(os.path.join(save_dir, "snapshot_log.csv"), {
                    "timestamp": utils.get_timestamp_iso(),
                    "mode": "snapshot",
                    "exposure_us": self.spin_exp.value(),
                    "gain": self.spin_gain.value(),
                    "filepath": path,
                })
                self.log(f"Snapshot saved: {path}")

    def on_browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Save Directory")
        if d:
            self.edt_save_dir.setText(d)

    def on_snapshot_browse(self):
        d = QFileDialog.getExistingDirectory(self, "Select Snapshot Directory")
        if d:
            self.edt_snapshot_dir.setText(d)

    def on_new_frame(self, frame):
        try:
            if not self._logged_frame_info:
                self.log(f"Frame info: shape={getattr(frame, 'shape', None)}, dtype={getattr(frame, 'dtype', None)}")
                self._logged_frame_info = True

            # Normalize to RGB for display
            if frame is None:
                return
            if frame.ndim == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            elif frame.ndim == 3 and frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
            elif frame.ndim == 3 and frame.shape[2] == 3 and self._force_bgr_swap:
                # Ximea may deliver BGR; swap to RGB if colors look off
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Ensure array is C-contiguous (REQUIRED for QImage)
            frame = np.ascontiguousarray(frame)
            
            if not self._logged_channel_stats and frame.ndim == 3 and frame.shape[2] == 3:
                # Simple diagnostics to see if color channels are actually distinct
                means = frame.reshape(-1, 3).mean(axis=0)
                self.log(f"Frame channel means (RGB): {means[0]:.1f}, {means[1]:.1f}, {means[2]:.1f}")
                self._logged_channel_stats = True
            
            # Cache the display frame (RGB) for snapshot consistency
            self._last_frame_rgb = frame.copy()

            # Use frame for display
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            
            pixmap = QPixmap.fromImage(qt_img).scaled(
                self.lbl_live.size(), Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.lbl_live.setPixmap(pixmap)
            
        except Exception as e:
            print(f"DEBUG: Display Error: {e}")

    def update_status_info(self):
        pol = self.spin_pol.value() if hasattr(self, "spin_pol") else "--"
        samp = self.spin_samp.value() if hasattr(self, "spin_samp") else "--"
        exp = self.spin_exp.value() if hasattr(self, "spin_exp") else "--"
        gain = self.spin_gain.value() if hasattr(self, "spin_gain") else "--"
        self.lbl_info.setText(f" | Pol: {pol} | Samp: {samp} | Exp: {exp} us | Gain: {gain} dB")

    def on_seq_mode_toggle(self):
        if self.chk_crosspol.isChecked():
            self.spin_exp_cross.setEnabled(True)
            self.spin_exp_cross.setValue(self._exp_cross_last)
        else:
            self._exp_cross_last = self.spin_exp_cross.value()
            self.spin_exp_cross.setEnabled(False)

        if self.chk_normal.isChecked():
            self.spin_exp_normal.setEnabled(True)
            self.spin_exp_normal.setValue(self._exp_normal_last)
        else:
            self._exp_normal_last = self.spin_exp_normal.value()
            self.spin_exp_normal.setEnabled(False)

    def parse_angles(self, text):
        raw = text.strip()
        if not raw:
            return [], "Angles are empty."
        parts = [p for p in re.split(r"[,\s]+", raw) if p]
        angles = []
        for p in parts:
            if ":" in p:
                nums = p.split(":")
                if len(nums) not in (2, 3):
                    return [], f"Invalid range token: '{p}'"
                try:
                    start = int(nums[0])
                    end = int(nums[1])
                    step = int(nums[2]) if len(nums) == 3 else 1
                except ValueError:
                    return [], f"Invalid range token: '{p}'"
                if step == 0:
                    return [], f"Step cannot be 0 in '{p}'"
                if start < 0 or start > 180 or end < 0 or end > 180:
                    return [], f"Range out of bounds (0-180): '{p}'"
                if step > 0:
                    rng = range(start, end + 1, step)
                else:
                    rng = range(start, end - 1, step)
                angles.extend(list(rng))
            else:
                try:
                    val = int(p)
                except ValueError:
                    return [], f"Invalid angle token: '{p}'"
                if val < 0 or val > 180:
                    return [], f"Angle out of bounds (0-180): '{p}'"
                angles.append(val)
        if not angles:
            return [], "No valid angles found."
        return angles, ""

    # --- STATE MACHINE UI UPDATE ---
    def update_state_ui(self, state):
        self.current_state = state
        self.lbl_status.setText(f"Controller: {state}")
        
        # Colors
        if state == STATE_DISCONNECTED:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: gray;")
            enable_manual = False
            enable_start = False
        elif state == STATE_LATCHED:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
            enable_manual = False
            enable_start = False
        elif state == STATE_ARMED:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: green;")
            enable_manual = True
            enable_start = True
        elif state == STATE_RUNNING:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: blue;")
            enable_manual = False
            enable_start = False
        elif state == STATE_ERROR:
            self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: darkred;")
            enable_manual = False
            enable_start = False
        else:
            enable_manual = False
            enable_start = False
            
        # Widgets Enable/Disable
        self.btn_estop.setEnabled(True) # Always
        self.btn_reset.setEnabled(state != STATE_DISCONNECTED)
        self.btn_home.setEnabled(state == STATE_ARMED)
        
        self.btn_move_pol.setEnabled(enable_manual)
        self.btn_move_samp.setEnabled(enable_manual)
        self.btn_pol_p45.setEnabled(enable_manual)
        self.btn_samp_p45.setEnabled(enable_manual)
        
        self.btn_start.setEnabled(enable_start)
        self.grp_camera = self.findChild(QGroupBox, "Camera Settings")
        if self.grp_camera:
            self.grp_camera.setEnabled(state != STATE_RUNNING and self.cam_thread is not None)

    def on_cam_error(self, err_msg):
        self.log(err_msg, "ERROR")
        QMessageBox.critical(self, "Camera Error", err_msg)
        self.update_state_ui(STATE_ERROR)
        # Force disconnect UI
        if self.cam_thread:
            self.cam_thread.stop()
            self.cam_thread = None
        self.btn_cam_connect.setText("Connect Camera")
        self.lbl_cam_status.setText(" | Camera: ERROR")
        self.lbl_cam_status.setStyleSheet("font-size: 16px; font-weight: bold; color: red;")
        self.lbl_live.setText("Camera Error")

    def on_log_copy(self):
        QApplication.clipboard().setText(self.log_text.toPlainText())
        self.log("Log copied to clipboard.")

    def on_log_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "apis_log.txt", "Text Files (*.txt);;All Files (*)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())
            self.log(f"Log saved: {path}")

    def closeEvent(self, event):
        """Cleanup on Close"""
        self.log("Closing application...", "WARN")
        
        # Stop Camera Thread
        if self.cam_thread:
            self.cam_thread.stop()
        
        # Close Camera Logic
        if hasattr(self.cam, 'close'):
            self.cam.close()

        # Stop Sequence Thread
        if self.seq_thread:
            self.seq_thread.abort()
            self.seq_thread.wait()
            
        # Close Serial
        if self.ctrl:
            self.ctrl.disconnect()
            
        event.accept()

if __name__ == "__main__":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("APIS.AutomatedPolarizationImagingSystem")
    except Exception:
        pass
    app = QApplication(sys.argv)
    icon_candidates = [
        os.path.join(os.path.dirname(__file__), "assets", "apis_logo.png"),
        os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"),
        os.path.join(os.path.dirname(__file__), "assets", "icon.ico"),
    ]
    for icon_path in icon_candidates:
        if os.path.isfile(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            break
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
