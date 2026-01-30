# APIS: Automated Polarization Imaging System

A control system for an automated 2-axis polarization imaging setup using Arduino, Python (PyQt6), and XIMEA cameras.

## 1. Installation

### Hardware Requirements
- Polarizer motor (Axis 1): SG90 Servo @ Pin 10
- Sample motor (Axis 2): HS-318 Servo @ Pin 11
- Camera: XIMEA USB 3.0/3.1 camera
- Power: External 5V (>=2A) for servos. Shared ground with Arduino is mandatory.

### Software Prerequisites
1. Python 3.9+
2. Arduino IDE (for flashing firmware)
3. XIMEA Software Package (drivers and API)

### Python Environment Setup
```bash
# Create venv
python -m venv venv

# Activate venv (Windows)
venv\Scriptsctivate

# Install dependencies
pip install -r requirements.txt
```

---

## 2. XIMEA Camera Setup (Critical)

The XIMEA Python API (xiapi) is not available on PyPI. You must install the drivers and then link the API into your virtual environment.

### Step A: Driver Installation
1. Download the XIMEA Software Package for Windows from the XIMEA support site.
2. Run the installer and select API -> Python.
3. Complete the installation for your interface (USB3).

### Step B: Link Python API (for virtual environments)
If `pip install ximea` fails (common), manually copy the API into your venv.

1. Locate the installed API folder (default):
   - `C:\XIMEA\API\Python3`
2. Copy the `ximea` folder inside it.
3. Paste into your venv:
   - `APISenv\Lib\site-packages\`

Verification:
```bash
python -c "import ximea; print('Success')"
```

Warning:
- The XIMEA API is proprietary software.
- Do not commit `venv/Lib/site-packages/ximea` to a public repo.

---

## 3. Quick Start

### 1) Flash Firmware
Open `firmware/APIS_Firmware/APIS_Firmware.ino` in Arduino IDE and upload to your board.

### 2) Run GUI
```bash
python app/main.py
```

---

## 4. App Usage Guide

### Safety Bar (Top)
- Controller and camera connection state are shown.
- Current polarizer angle, sample angle, exposure, and gain are shown.
- ESTOP (Red): Immediately cuts power/torque to motors.
- RESET / ARM (Green): Re-engages motors. Required to start sequence.
- HOME: Moves both motors to 0 degrees.

### Device Connections
- Select COM port -> Connect Controller.
- Connect Camera.
- If the XIMEA SDK is missing, it falls back to DummyCamera (simulation).
  - DummyCamera generates a synthetic live view so you can build UI/logic without hardware.
  - This is useful for development when XIMEA cameras are unavailable.

### Manual Motor Control (Absolute Movement)
- Set absolute angle (0-180) and click Move for each axis.
- +45 buttons increment the current value by 45 degrees.
- Manual moves are only enabled while ARMED.

### Camera Settings
- Set exposure (us) and gain (dB) and click Apply Settings.
- These values are shown in the top status bar.

### Live View and Snapshot
- Live view shows the current camera stream.
- Snapshot:
  - Set Filename and Save Dir.
  - Click Snapshot to save a TIFF.
  - Metadata is logged to `snapshot_log.csv` in the same folder.

### Sequence Control
- Save Directory and Sample ID are required.
- Modes: enable Crosspol, Normal, or both.
- Exposure defaults:
  - Crosspol: 50000 us
  - Normal: 12000 us
- Angles input:
  - List: `90,60,45,30,0`
  - Range: `0:180:15`
- Settling Time (s): motor settle delay after each movement.

### Polarizer Angles (Sequence)
- Crosspol mode: polarizer moves to 90 degrees.
- Normal mode: polarizer moves to 0 degrees.

### Outputs
- Images are saved under:
  - `{SaveDir}/{SampleID}/crosspol` and/or `{SaveDir}/{SampleID}/normal`
- Log file:
  - `{SaveDir}/{SampleID}_log.csv`
- Snapshot log:
  - `{SaveDir}/snapshot_log.csv`

---

## 5. Safety Logic
- LATCHED: default on boot or ESTOP. Motors detached (no torque).
- ARMED: motors attached (holding torque). Required for motion.
- Protocol: 2-way handshake. Commands are rejected if LATCHED.

---

## 6. Verification
- Automated tests: `tests/test_mock_serial.py` (controller logic)
- Manual hardware check: `scripts/check_hardware.py` (motion limits, ESTOP)

---

## 7. Repository Notes
- `data/` and `venv/` are ignored by git.
- `.vscode/` is ignored by git.
