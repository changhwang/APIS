# APIS Prerequisite Checklist (Windows)

## 1) XIMEA Software Package
- Install XIMEA Windows Software Package (drivers + xiAPI)
- Reboot after driver installation
- Confirm camera shows in Device Manager or XIMEA tools

## 2) Run APIS
- Launch APIS.exe
- Click Connect Camera and confirm live view
- Confirm the camera stream looks reasonable with the fixed white-balance baseline used by the app

## 3) Arduino / Motor Check
- Run `check_hardware.exe` to validate the Arduino COM port (motor controller)
- Press RESET / ARM
- Move Polarizer and Sample manually
- Press ESTOP and confirm torque release, then RESET

## 4) Sequence Smoke Test
- Set Sample ID and Save Directory
- Run a short sequence
- Default sequence baseline: Normal `12000 us`, Crosspol `50000 us`
- Verify TIFF images and {SampleID}/{SampleID}_log.csv are created

Troubleshooting order
1) XIMEA drivers
2) Camera connection
3) Arduino COM/serial
4) APIS app
