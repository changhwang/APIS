APIS (Automated Polarization Imaging System)

Package version: v0.1.1

Installation and Run (Windows)
1) Install prerequisites (see prereq_checklist.md)
2) Unzip the distribution package
3) Run APIS\APIS.exe

Recommended first-time checks
- Connect camera and confirm live view
- Connect Arduino, press RESET/ARM, and perform a manual move
- Use check_hardware.exe to validate COM port and ESTOP

Notes
- Do not move APIS.exe out of the APIS folder. Keep the whole folder.
- If the camera is not detected, verify XIMEA drivers are installed.
- Default acquisition baseline: Normal = polarizer 0 deg @ 12000 us, Crosspol = polarizer 90 deg @ 50000 us.
- Current XIMEA capture baseline uses fixed white balance: R=1.40, G=1.00, B=1.20.

Hardware check
- Run check_hardware.exe to validate Arduino COM port and ESTOP without launching the GUI.
