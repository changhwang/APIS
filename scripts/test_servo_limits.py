import argparse
import sys
import time

# Add project root to path
sys.path.append(".")

from apis.controller import PicsController
from apis import config


AXIS_MAP = {
    "polarizer": config.CMD_POLARIZER,
    "sample": config.CMD_SAMPLE,
}


def parse_angles(text: str) -> list[int]:
    angles = []
    for token in text.split(","):
        token = token.strip()
        if not token:
            continue
        value = int(token)
        if value < config.SERVO_MIN_ANGLE or value > config.SERVO_MAX_ANGLE:
            raise ValueError(
                f"Angle {value} is outside firmware-supported servo range "
                f"{config.SERVO_MIN_ANGLE}-{config.SERVO_MAX_ANGLE}."
            )
        angles.append(value)
    if not angles:
        raise ValueError("No valid angles provided.")
    return angles


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Raw servo endpoint test within the firmware-supported 0-180 degree range."
    )
    parser.add_argument("--port", required=True, help="Arduino COM port, e.g. COM3")
    parser.add_argument(
        "--axis",
        required=True,
        choices=sorted(AXIS_MAP.keys()),
        help="Which axis to test",
    )
    parser.add_argument(
        "--angles",
        default="150,160,170,175,180,175,170,160,150,120,90,60,30,0",
        help="Comma-separated raw servo angles to test",
    )
    parser.add_argument(
        "--dwell",
        type=float,
        default=1.5,
        help="Seconds to wait at each angle",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt before each move",
    )
    args = parser.parse_args()

    angles = parse_angles(args.angles)
    axis_cmd = AXIS_MAP[args.axis]

    ctrl = PicsController()

    print("=== APIS Raw Servo Limit Test ===")
    print(f"Port: {args.port}")
    print(f"Axis: {args.axis}")
    print(f"Raw servo angles: {angles}")
    print()
    print("This test sends raw servo commands directly.")
    print("It bypasses the stage-angle calibration layer.")
    print("Firmware does not allow commands above 180 degrees.")
    print()
    print("Stop immediately if you hear binding, stalling, or excessive vibration.")
    print()

    try:
        ctrl.connect(args.port)
        if not ctrl.reset():
            print("Failed to arm the controller.")
            return 1

        for angle in angles:
            if args.interactive:
                answer = input(f"Move {args.axis} to raw servo angle {angle}? [Enter/q] ").strip().lower()
                if answer == "q":
                    print("Aborted by user.")
                    break

            resp = ctrl._send_raw_command(axis_cmd, angle)
            print(f"CMD {axis_cmd:02d}{angle:03d} -> {resp}")
            time.sleep(args.dwell)

        print("Returning axis to 0...")
        resp = ctrl._send_raw_command(axis_cmd, 0)
        print(f"CMD {axis_cmd:02d}000 -> {resp}")
        return 0

    finally:
        try:
            ctrl.emergency_stop()
        except Exception:
            pass
        ctrl.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
