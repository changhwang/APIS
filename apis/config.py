# APIS Configuration Constants

# Serial Settings
SERIAL_BAUDRATE = 9600
SERIAL_TIMEOUT_S = 0.5  # Readline timeout for fast non-blocking feel

# Connection & Logic
MAX_RETRIES = 3
CONNECTION_WAIT_S = 2.0  # Max wait for READY handshake
SETTLING_TIME_S = 1.5    # Default physical settling time (software enforced)
COMMAND_DELAY_S = 0.05   # Min delay between commands to avoid flooding

# Servo Motion Limits
SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180

# XIMEA Acquisition Defaults
XIMEA_USE_FIXED_WB = True
XIMEA_WB_KR = 1.40
XIMEA_WB_KG = 1.00
XIMEA_WB_KB = 1.20
XIMEA_DEFAULT_NORMAL_EXPOSURE_US = 18000
XIMEA_DEFAULT_CROSSPOL_EXPOSURE_US = 50000

# Mechanical Transmission
SERVO_GEAR_TEETH = 70
STAGE_GEAR_TEETH = 80

# Convert requested stage angle into servo angle.
# servo_angle = zero_offset + direction * stage_angle * ratio
# Both axes currently use image-derived calibration from data/calibrationsample/normal.
POLARIZER_STAGE_TO_SERVO_RATIO = 1.059
SAMPLE_STAGE_TO_SERVO_RATIO = 1.059
POLARIZER_STAGE_DIRECTION = 1
SAMPLE_STAGE_DIRECTION = 1
POLARIZER_SERVO_ZERO_DEG = 0
SAMPLE_SERVO_ZERO_DEG = 0
POLARIZER_STAGE_MIN_ANGLE = 0
SAMPLE_STAGE_MIN_ANGLE = 0
POLARIZER_STAGE_MAX_ANGLE = int((SERVO_MAX_ANGLE - POLARIZER_SERVO_ZERO_DEG) / POLARIZER_STAGE_TO_SERVO_RATIO)
SAMPLE_STAGE_MAX_ANGLE = int((SERVO_MAX_ANGLE - SAMPLE_SERVO_ZERO_DEG) / SAMPLE_STAGE_TO_SERVO_RATIO)

# Command Codes (Protocol PPAAA)
CMD_POLARIZER = 10
CMD_SAMPLE    = 11
CMD_HOME      = 96
CMD_RESET     = 98
CMD_ESTOP     = 99

# Safety States
STATE_LATCHED = "LATCHED"  # Detached, Boot/Estop
STATE_ARMED   = "ARMED"    # Attached, Normal Operation
