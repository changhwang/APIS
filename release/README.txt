APIS (Automated Polarization Imaging System)

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

Hardware check
- Run check_hardware.exe to validate Arduino COM port and ESTOP without launching the GUI.
