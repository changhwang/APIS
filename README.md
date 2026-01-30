# APIS: Automated Polarization Imaging System

APIS is a control system for an automated 2-axis polarization imaging setup using Arduino, Python (PyQt6), and XIMEA cameras.

---

## 1. What You Get

- GUI application (live view, manual motor control, and sequence automation)
- Safety logic (LATCHED/ARMED, ESTOP, RESET)
- Image capture + CSV logging
- Hardware check tool for quick diagnostics

---

## 2. Requirements

### Hardware
- Polarizer motor (Axis 1): SG90 servo @ Pin 10
- Sample motor (Axis 2): HS-318 servo @ Pin 11
- Camera: XIMEA USB 3.0/3.1 camera
- Power: External 5V (>=2A) for servos
- Common ground between Arduino GND and servo PSU GND

### Software
- Python 3.9+
- Arduino IDE (for flashing firmware)
- XIMEA Windows Software Package (drivers + xiAPI)

---

## 3. Installation (Development)

### 3.1 Create venv and install deps
```bash
python -m venv venv
venv\Scriptsctivate
pip install -r requirements.txt
```

### 3.2 XIMEA Python API (xiAPI)
The XIMEA Python API is not on PyPI. Install the XIMEA Software Package first, then link the API into your venv.

1. Install the XIMEA Software Package (drivers + API)
2. Locate the API folder (default):
   - `C:\XIMEA\API\Python3`
3. Copy the `ximea` folder into:
   - `APISenv\Lib\site-packages\`

Verification:
```bash
python -c "import ximea; print('Success')"
```

---

## 4. Quick Start

### 4.1 Flash Firmware
Open `firmware/APIS_Firmware/APIS_Firmware.ino` and upload to your Arduino.

### 4.2 Run GUI
```bash
python app/main.py
```

---

## 5. App Usage Guide

### Safety Bar (Top)
- Shows controller/camera state and current angles/exposure/gain
- ESTOP: immediately cuts motor torque (LATCHED)
- RESET / ARM: re-engages motors (ARMED)
- HOME: moves both motors to 0 degrees

### Device Connections
- Select COM port -> Connect Controller
- Connect Camera
- If XIMEA is not available, the app falls back to DummyCamera

### Manual Motor Control (Absolute Movement)
- Set absolute angle (0-180) and click Move
- +45 buttons increment by 45 degrees

### Camera Settings
- Set exposure (us) and gain (dB)
- Click Apply Settings

### Live View and Snapshot
- Live view shows the camera stream
- Snapshot saves TIFF to the selected folder
- Snapshot metadata is logged to `snapshot_log.csv`

### Sequence Control
- Set Save Directory and Sample ID
- Choose modes: Crosspol / Normal
- Set exposures (defaults: Crosspol 50000 us, Normal 12000 us)
- Set angles (list or range)
  - List: `90,60,45,30,0`
  - Range: `0:180:15`
- Settling Time: motor settle delay after each move

### Polarizer Angles (Sequence)
- Crosspol: polarizer moves to 90 degrees
- Normal: polarizer moves to 0 degrees

---

## 6. Outputs

- Images:
  - `{SaveDir}/{SampleID}/crosspol`
  - `{SaveDir}/{SampleID}/normal`
- Log file:
  - `{SaveDir}/{SampleID}/{SampleID}_log.csv`
- Snapshot log:
  - `{SaveDir}/snapshot_log.csv`

---

## 7. Safety Logic

- LATCHED: default on boot or ESTOP, motors detached
- ARMED: motors attached, motion enabled
- Commands are rejected in LATCHED state

---

## 8. Verification

- Automated tests: `tests/test_mock_serial.py`
- Manual hardware check: `scripts/check_hardware.py`
- Distribution includes `check_hardware` for quick COM port and ESTOP validation

---

## 9. Build and Distribution (Windows)

Recommended flow:
1) PyInstaller onedir build
2) Zip the dist folder for distribution
3) (Later) Inno Setup for installer packaging

### Build prerequisites
- Use a clean build venv with PyQt6 only (do not install PySide6/PyQt5)
- Icon file: `assets/icon.ico` (already provided)

### Build (spec-based)
- Spec files: `build/apis.spec`, `build/check_hardware.spec`
- Build script: `build/build.ps1`

Example:
```powershell
.uilduild.ps1 -Version 0.1.0
```

### Distribution package
The build script produces:
- `dist/APIS/` (GUI app)
- `dist/check_hardware/` (console tool)
- `release/APIS-win64-vX.Y.Z.zip` containing:
  - `APIS/`
  - `check_hardware/`
  - `README.txt`
  - `prereq_checklist.md`

### XIMEA prerequisite
XIMEA drivers/xiAPI must be installed first. The EXE does not bundle the SDK.

---

## 10. Repository Notes

- `data/`, `dist/`, and `release/*.zip` are ignored by git
- `.vscode/` and `build_venv/` are ignored by git
