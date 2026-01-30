/*
 * APIS: Automated Polarization Imaging System Firmware
 * 
 * Protocol: 9600 baud, "PPAAA\n" line-based.
 * Safety: 
 *   - Boot: LATCHED (Servos detached), prints "READY"
 *   - 99 (ESTOP): Detach all, set LATCHED. Always accepted.
 *   - 98 (RESET): Attach all, set ARMED. Always accepted.
 *   - 10 (Polarizer), 11 (Sample), 96 (HOME): Only accepted if ARMED.
 * 
 * Pins:
 *   - 10: Polarizer Axis (SG90)
 *   - 11: Sample Rotation Axis (HS-318)
 */

#include <Servo.h>

// --- Configuration ---
const int PIN_POLARIZER = 10;
const int PIN_SAMPLE    = 11;
const long BAUDRATE     = 9600;

// --- State Definitions ---
// Safety State Machine:
// LATCHED = true  -> Servos detached, motion blocked. (Boot default, ESTOP state)
// LATCHED = false -> Servos attached, motion allowed. (RESET/ARMED state)
bool isLatched = true; 

Servo servoPolarizer;
Servo servoSample;

// --- Serial Buffer ---
const int MAX_BUF = 32;
char buf[MAX_BUF];
int bufPos = 0;

void setup() {
  Serial.begin(BAUDRATE);
  
  // Power-on safety: Do NOT attach servos yet.
  // Ensure internal state matches "Detached".
  isLatched = true;

  // Boot message
  Serial.println("READY");
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    // Ignore carriage return
    if (c == '\r') continue;

    // Line terminator -> Process Command
    if (c == '\n') {
      buf[bufPos] = '\0'; // Null-terminate
      processCommand(buf);
      bufPos = 0; // Reset buffer
    } 
    else {
      // Buffer overflow protection
      if (bufPos < MAX_BUF - 1) {
        buf[bufPos++] = c;
      } else {
        // Buffer full, discard command but keep reading until \n to clear line
        // We will catch the format error at processCommand or we could flush here.
        // Simple strategy: Set a flag or just let it fail parsing.
        // Let's just consume until \n, then error.
        // For robustness, we'll keep filling the lat slot to force a parse error.
        buf[MAX_BUF - 1] = 'X'; 
      }
    }
  }
}

void processCommand(char* input) {
  // 1. Trim whitespace (simple approach: assuming standard "PPAAA" sans leading spaces, 
  //    but let's be safe against leading/trailing spaces if needed. 
  //    The spec says "exactly 5 digits", so if length != 5, it's FORMAT error.)
  
  // Measure length excluding null terminator
  int len = strlen(input);
  
  // strict "exactly 5 digits" check
  if (len != 5) {
    Serial.println("ERR FORMAT LEN");
    return;
  }

  // Check all are digits
  for (int i = 0; i < 5; i++) {
    if (!isdigit(input[i])) {
      Serial.println("ERR FORMAT DIGIT");
      return;
    }
  }

  // Parse PP and AAA
  char ppStr[3];
  ppStr[0] = input[0];
  ppStr[1] = input[1];
  ppStr[2] = '\0';
  
  char aaaStr[4];
  aaaStr[0] = input[2];
  aaaStr[1] = input[3];
  aaaStr[2] = input[4];
  aaaStr[3] = '\0';

  int pp = atoi(ppStr);
  int aaa = atoi(aaaStr);

  // --- Command Handler ---

  // Priority 1: ESTOP (PP=99) - Always accepted
  if (pp == 99) {
    performEstop();
    Serial.println("OK ESTOP");
    return;
  }

  // Priority 2: RESET (PP=98) - Always accepted
  if (pp == 98) {
    performReset();
    Serial.println("OK RESET");
    return;
  }

  // All other commands require ARMED state (isLatched == false)
  if (isLatched) {
    Serial.println("ERR ESTOP_LATCHED");
    return;
  }

  // Priority 3: HOME (PP=96)
  if (pp == 96) {
    servoPolarizer.write(0);
    servoSample.write(0);
    // IMMEDIATE ACK
    Serial.println("OK HOME");
    return;
  }

  // Axis Move Commands
  if (pp == 10) { // Polarizer
    if (aaa < 0 || aaa > 180) {
      Serial.println("ERR RANGE");
      return;
    }
    servoPolarizer.write(aaa);
    // IMMEDIATE ACK
    Serial.print("OK 10 ");
    printAngle3(aaa);
    Serial.println();
    return;
  }

  if (pp == 11) { // Sample
    if (aaa < 0 || aaa > 180) {
      Serial.println("ERR RANGE");
      return;
    }
    servoSample.write(aaa);
    // IMMEDIATE ACK
    Serial.print("OK 11 ");
    printAngle3(aaa);
    Serial.println();
    return;
  }

  // Unknown PP
  Serial.print("ERR PIN ");
  Serial.println(pp);
}

void performEstop() {
  // Detach immediately to release torque
  servoPolarizer.detach();
  servoSample.detach();
  isLatched = true;
}

void performReset() {
  // Re-attach servos
  if (!servoPolarizer.attached()) servoPolarizer.attach(PIN_POLARIZER);
  if (!servoSample.attached())    servoSample.attach(PIN_SAMPLE);
  
  isLatched = false;
}

// Helper to print angle as 3 digits (e.g. 090)
void printAngle3(int val) {
  if (val < 10) Serial.print("00");
  else if (val < 100) Serial.print("0");
  Serial.print(val);
}
