# APIS Configuration Constants

# Serial Settings
SERIAL_BAUDRATE = 9600
SERIAL_TIMEOUT_S = 0.5  # Readline timeout for fast non-blocking feel

# Connection & Logic
MAX_RETRIES = 3
CONNECTION_WAIT_S = 2.0  # Max wait for READY handshake
SETTLING_TIME_S = 1.5    # Default physical settling time (software enforced)
COMMAND_DELAY_S = 0.05   # Min delay between commands to avoid flooding

# Command Codes (Protocol PPAAA)
CMD_POLARIZER = 10
CMD_SAMPLE    = 11
CMD_HOME      = 96
CMD_RESET     = 98
CMD_ESTOP     = 99

# Safety States
STATE_LATCHED = "LATCHED"  # Detached, Boot/Estop
STATE_ARMED   = "ARMED"    # Attached, Normal Operation
