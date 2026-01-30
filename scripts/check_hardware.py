import sys
import time
# Add project root to path
sys.path.append(".") 

from apis.controller import PicsController

def main():
    print("=== APIS Hardware Check ===")
    port = input("Enter COM port (e.g. COM3): ").strip()
    if not port:
        print("No port entered. Exiting.")
        return

    ctrl = PicsController()
    
    print(f"Connecting to {port}...")
    try:
        ctrl.connect(port)
        print(f"Connected! State: {ctrl.get_state()}")
    except Exception as e:
        print(f"Connection Failed: {e}")
        return

    while True:
        print("\n--- MENU ---")
        print("[1] Move Polarizer (0-180)")
        print("[2] Move Sample (0-180)")
        print("[3] HOME (96)")
        print("[4] RESET / ARM (98)")
        print("[5] ESTOP (99)")
        print(f"[s] Status (Local State: {ctrl.get_state()})")
        print("[q] Quit")
        
        choice = input("Select: ").strip().lower()
        
        if choice == 'q':
            ctrl.disconnect()
            break
            
        elif choice == '1':
            try:
                ang = int(input("Angle: "))
                if ctrl.rotate_polarizer(ang):
                    print(">> OK")
                else:
                    print(">> FAILED (Check log/console)")
            except ValueError:
                print("Invalid integer")
                
        elif choice == '2':
            try:
                ang = int(input("Angle: "))
                if ctrl.rotate_sample(ang):
                    print(">> OK")
                else:
                    print(">> FAILED (Check log/console)")
            except ValueError:
                print("Invalid integer")
                
        elif choice == '3':
            if ctrl.home():
                print(">> OK HOME")
            else:
                print(">> FAILED HOME")
                
        elif choice == '4':
            if ctrl.reset():
                print(">> OK RESET. System ARMED.")
            else:
                print(">> FAILED RESET")
                
        elif choice == '5':
            if ctrl.emergency_stop():
                print(">> OK ESTOP. System LATCHED.")
            else:
                print(">> FAILED ESTOP")
        
        elif choice == 's':
            pass # just reprints menu
            
        else:
            print("Unknown command")

if __name__ == "__main__":
    main()
