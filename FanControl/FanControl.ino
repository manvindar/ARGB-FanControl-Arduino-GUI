#include <FastLED.h>

/*
 * CPU Fan ARGB Control Sketch (Enhanced Edition)
 * This sketch controls addressable RGB LEDs in CPU fans using VDG-compatible pin configuration.
 * Supports multiple color effects, custom colors, and advanced serial control.
 * 
 * ============================================
 * PIN CONFIGURATION GUIDE
 * ============================================
 * Default: Pin 6 (VDG Header compatible with most motherboards)
 * 
 * To change the LED pin:
 * 1. Find the line: #define LED_PIN  6
 * 2. Change '6' to your desired pin (0-13)
 * 3. Recompile and upload to Arduino
 * 
 * Common pin choices:
 * - Pin 5: PWM-capable, on side of most boards
 * - Pin 6: DEFAULT - VDG header compatible
 * - Pin 9: PWM-capable, good for large LED strips
 * - Pin 10: PWM-capable alternative
 * 
 * ============================================
 * LED COUNT CONFIGURATION
 * ============================================
 * Default: 12 LEDs (typical for ARGB fans)
 * 
 * To change LED count:
 * 1. Find the line: #define NUM_LEDS  12
 * 2. Change '12' to your actual LED count
 * 3. Recompile and upload to Arduino
 * 
 * ============================================
 * QUICK REFERENCE
 * ============================================
 * Colors: 1=Red, 2=Green, 3=Blue, 4=White, 5=Cyan, 6=Magenta, 7=Yellow, 8=Orange, 9=Pink, 0=Purple
 * Modes: R(ainbow), P(ulse), S(tatic), W(ipe), T(heater), K(sparkle), N(inelon), B(PM), C(onfetti), F(ire), X(strobe), E(breathing)
 * Control: +(brightness), -(dim), >(faster), <(slower), G(custom RGB), H(hue shift), A(auto-cycle), L(status)
 * Speed Presets: Q(very fast), D(fast), V(medium), Z(slow), M(very slow)
 * 
 * ============================================
 * Hardware Requirements:
 * - Arduino Uno (or compatible)
 * - ARGB Fan (5V, 3-pin)
 * - VDG Header Connection: +5V, Data (Pin 6), GND
 * - FastLED Library (Install via Library Manager)
 * ============================================
 */

// ===== PIN & LED CONFIGURATION =====
#define LED_PIN     6          // Data pin for addressable LEDs (change this to your pin)
#define NUM_LEDS    12         // Number of LEDs on your device (change this to your count)
#define LED_TYPE    WS2812B    // ARGB fans typically use WS2812B or similar
#define COLOR_ORDER GRB

// Global variables
CRGB leds[NUM_LEDS];
uint8_t currentBrightness = 255;  // 0-255
uint8_t currentMode = 0;          // 0-11: effect modes
CRGB currentColor = CRGB::Red;
bool useMultiColor = false;       // Global rainbow color source toggle
uint8_t globalHue = 0;            // Shared hue for all multi-color effects
uint8_t effectSpeed = 10;         // general speed/wait (lower = faster)
uint8_t effectIntensity = 128;    // effect intensity/variation (0-255)
uint8_t colorSaturation = 255;    // color saturation (0-255, lower = more grayish)
uint8_t hueRotationSpeed = 1;     // rainbow rotation speed multiplier
bool autoCycleMode = false;       // automatically cycle through effects
uint16_t modeChangeTimer = 0;     // timer for auto-cycle
uint8_t autoModeIndex = 0;        // current mode in auto-cycle
unsigned long lastTelemetryTime = 0; // telemetry send timing
// Tipsy sync scaling factor (1x = 128). Adjusted from GUI via ~T<value> (32-255)
uint8_t tipsySyncScale = 128;

// LED Customization Variables
bool ledReverse = false;          // reverse LED direction
uint8_t ledStartIdx = 0;          // start LED index for partial effects
uint8_t ledEndIdx = NUM_LEDS - 1; // end LED index for partial effects
bool ledMirror = false;           // mirror effect (affect both directions)
uint8_t fadeCurve = 128;          // fade curve steepness (0-255)
bool waveDirection = false;       // wave direction (left to right vs right to left)
uint8_t rainbowMode = 0;          // 0=wavelength, 1=hue-only, 2=pastel, 3=saturated

// Preset colors matching common motherboard ARGB software + custom colors
const CRGB colorPresets[] = {
    CRGB::Red,        // 1
    CRGB::Green,      // 2
    CRGB::Blue,       // 3
    CRGB::White,      // 4
    CRGB::Cyan,       // 5
    CRGB::Magenta,    // 6
    CRGB::Yellow,     // 7
    CRGB::Orange,     // 8
    {255, 192, 203},  // 9 - Pink
    {128, 0, 128}     // 0 - Purple
};

// Function prototypes
void handleSerialCommand(char cmd);
void rainbowCycle(uint8_t wait);
void pulseEffect(uint8_t wait);
void setStaticColor(CRGB color);
void colorWipe(uint8_t wait);
void theaterChase(uint8_t wait);
void sparkle(uint8_t wait);
void sinelon(uint8_t wait);
void bpmEffect(uint8_t wait);
void confetti(uint8_t wait);
void fireEffect(uint8_t wait);
void strobeEffect(uint8_t wait);
void breathingEffect(uint8_t wait);
void tipsyEffect(uint8_t wait);
void multicolorEffect(uint8_t wait);
void displayStatus();
void displayLedSettings();
void displayPinInfo();
void clearAllLeds();
void reverseLeds();
CRGB getPixelColor(int index);

void setup() {
    delay(2000); // 2 second safety delay for power-up
    
    // Initialize FastLED
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS).setCorrection(TypicalLEDStrip);
    FastLED.setBrightness(currentBrightness);
    
    Serial.begin(9600);
    Serial.println(F("\n========================================"));
    Serial.println(F("    CPU Fan ARGB Controller ENHANCED"));
    Serial.println(F("========================================"));
    displayPinInfo();
    displayStatus();
    Serial.println(F("--- COLOR PRESETS (1-0, J) ---"));
    Serial.println(F("1=Red, 2=Green, 3=Blue, 4=White, 5=Cyan"));
    Serial.println(F("6=Magenta, 7=Yellow, 8=Orange, 9=Pink, 0=Purple, J=Multi"));
    Serial.println(F("\n--- EFFECTS ---"));
    Serial.println(F("R=Rainbow, P=Pulse, S=Static, W=Wipe, T=Theater"));
    Serial.println(F("K=Sparkle, N=Sinelon, B=BPM, C=Confetti, F=Fire"));
    Serial.println(F("X=Strobe, E=Breathing"));
    Serial.println(F("\n--- CONTROLS ---"));
    Serial.println(F("Brightness: + / -  Speed: > / <"));
    Serial.println(F("Presets: Q/D/V/Z/M  Auto: A  Status: L"));
    Serial.println(F("Pin Info: I"));
    Serial.println(F("\n--- CUSTOMIZATION ---"));
    Serial.println(F("!/@: Brightness Presets | #/$: Effect Intensity"));
    Serial.println(F("%/^: Color Saturation  | &/*: Hue Rotation Speed"));
    Serial.println(F("(: Reset All      | ): Show Custom Values"));
    Serial.println(F("\n--- LED CUSTOMIZATION ---"));
    Serial.println(F(";: Reverse LEDs | ': Mirror Effect | [: Wave Direction"));
    Serial.println(F("]: Rainbow Modes (0-3) | {: Clear LEDs | }: LED Settings"));
    Serial.println(F("========================================"));
    randomSeed(analogRead(A0));
}

void loop() {
    // Update global hue counter for multi-color effects
    static uint16_t hueCounter = 0;
    static unsigned long lastHueUpdate = 0;
    if (millis() - lastHueUpdate >= 20) {
        lastHueUpdate = millis();
        hueCounter += hueRotationSpeed;
        globalHue = (hueCounter & 0xFF);
    }

    // Handle serial input for color/mode changes
    if (Serial.available()) {
        String input = Serial.readStringUntil('\n');
        input.trim();

        if (input.length() > 0) {
            // If single character, keep backward compatibility
            if (input.length() == 1) {
                handleSerialCommand(input.charAt(0));
            } else {
                // Multi-byte commands: custom RGB (Gr,g,b) or numeric settings prefixed with '~'
                char first = input.charAt(0);
                if (first == 'G' || first == 'g') {
                    // Expect format: G255,128,64
                    String payload = input.substring(1);
                    int r = 0, g = 0, b = 0;
                    int idx1 = payload.indexOf(',');
                    int idx2 = payload.indexOf(',', idx1 + 1);
                    if (idx1 > 0 && idx2 > idx1) {
                        r = payload.substring(0, idx1).toInt();
                        g = payload.substring(idx1 + 1, idx2).toInt();
                        b = payload.substring(idx2 + 1).toInt();
                        currentColor = CRGB(constrain(r, 0, 255), constrain(g, 0, 255), constrain(b, 0, 255));
                        useMultiColor = false; // Disable multi-color when selecting specific RGB
                        currentMode = 2; // static
                        Serial.print(F(">> Custom RGB: "));
                        Serial.print(r);
                        Serial.print(F(","));
                        Serial.print(g);
                        Serial.print(F(","));
                        Serial.println(b);
                    }
                } else if (first == '~') {
                    // Numeric setting: ~<Type><Value> e.g. ~B128 for brightness
                    if (input.length() >= 3) {
                        char type = input.charAt(1);
                        String valstr = input.substring(2);
                        int v = valstr.toInt();
                        switch(type) {
                            case 'B': // Brightness 0-255
                                currentBrightness = constrain(v, 0, 255);
                                FastLED.setBrightness(currentBrightness);
                                Serial.print(F(">> Bright: "));
                                Serial.println(currentBrightness);
                                break;
                            case 'I': // Intensity
                                effectIntensity = constrain(v, 0, 255);
                                Serial.print(F(">> Intensity: "));
                                Serial.println(effectIntensity);
                                break;
                            case 'U': // Saturation (U used to avoid conflict)
                                colorSaturation = constrain(v, 0, 255);
                                Serial.print(F(">> Saturation: "));
                                Serial.println(colorSaturation);
                                break;
                            case 'H': // Hue rotation speed (1-5)
                                hueRotationSpeed = constrain(v, 1, 5);
                                Serial.print(F(">> Hue Speed: "));
                                Serial.println(hueRotationSpeed);
                                break;
                            case 'V': // Effect speed (ms)
                                effectSpeed = constrain(v, 1, 200);
                                Serial.print(F(">> Speed: "));
                                Serial.println(effectSpeed);
                                break;
                            case 'T': // Tipsy sync scaling (32-255)
                                tipsySyncScale = constrain(v, 32, 255);
                                Serial.print(F(">> Tipsy Scale: "));
                                Serial.println(tipsySyncScale);
                                break;
                            default:
                                // unknown type
                                break;
                        }
                    }
                } else {
                    // Fallback: apply only the first char as a command
                    handleSerialCommand(input.charAt(0));
                }
            }

            modeChangeTimer = 0; // Reset timer on user input
        }
    }
    
    // Auto-cycle mode
    if (autoCycleMode) {
        modeChangeTimer++;
        if (modeChangeTimer >= (5000 / effectSpeed)) {  // Change every 5 seconds
            modeChangeTimer = 0;
            autoModeIndex = (autoModeIndex + 1) % 10; // Cycle through 10 effects
            currentMode = autoModeIndex;
            Serial.print("Auto-cycle -> Mode ");
            Serial.println(currentMode);
        }
    }
    
    // Execute current mode
    switch(currentMode) {
        case 0:
            rainbowCycle(effectSpeed);
            break;
        case 1:
            pulseEffect(effectSpeed);
            break;
        case 2:
            setStaticColor(currentColor);
            break;
        case 3:
            colorWipe(effectSpeed);
            break;
        case 4:
            theaterChase(effectSpeed);
            break;
        case 5:
            sparkle(effectSpeed);
            break;
        case 6:
            sinelon(effectSpeed);
            break;
        case 7:
            bpmEffect(effectSpeed);
            break;
        case 8:
            confetti(effectSpeed);
            break;
        case 9:
            fireEffect(effectSpeed);
            break;
        case 10:
            strobeEffect(effectSpeed);
            break;
        case 11:
            breathingEffect(effectSpeed);
            break;
        case 12:
            tipsyEffect(effectSpeed);
            break;
        case 13:
            multicolorEffect(effectSpeed);
            break;
        default:
            rainbowCycle(effectSpeed);
    }
    
    // Send telemetry data periodically for oscilloscope visualization
    sendTelemetry();
}

void sendTelemetry() {
    /*
    Output multi-channel telemetry in JSON format for oscilloscope-style visualization.
    Format: {"B":brightness,"M":mode,"S":speed,"I":intensity,"SAT":saturation,"H":hueSpeed,"R":r,"G":g,"B":b}
    */
    unsigned long currentTime = millis();
    if (currentTime - lastTelemetryTime >= 50) {  // Send every 50ms for smooth visualization
        lastTelemetryTime = currentTime;
        
        Serial.print(F("{\"BR\":"));
        Serial.print(currentBrightness);
        Serial.print(F(",\"M\":"));
        Serial.print(currentMode);
        Serial.print(F(",\"S\":"));
        Serial.print(effectSpeed);
        Serial.print(F(",\"I\":"));
        Serial.print(effectIntensity);
        Serial.print(F(",\"SAT\":"));
        Serial.print(colorSaturation);
        Serial.print(F(",\"H\":"));
        Serial.print(hueRotationSpeed);
        Serial.print(F(",\"R\":"));
        Serial.print(currentColor.r);
        Serial.print(F(",\"G\":"));
        Serial.print(currentColor.g);
        Serial.print(F(",\"BL\":"));
        Serial.print(currentColor.b);
        Serial.print(F(",\"TS\":"));
        Serial.print(tipsySyncScale);
        Serial.println(F("}"));
    }
}

void handleSerialCommand(char cmd) {
    switch(cmd) {
        // ===== COLOR SELECTION (1-0) =====
        case '1':
            currentColor = colorPresets[0];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Red"));
            break;
        case '2':
            currentColor = colorPresets[1];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Green"));
            break;
        case '3':
            currentColor = colorPresets[2];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Blue"));
            break;
        case '4':
            currentColor = colorPresets[3];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> White"));
            break;
        case '5':
            currentColor = colorPresets[4];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Cyan"));
            break;
        case '6':
            currentColor = colorPresets[5];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Magenta"));
            break;
        case '7':
            currentColor = colorPresets[6];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Yellow"));
            break;
        case '8':
            currentColor = colorPresets[7];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Orange"));
            break;
        case '9':
            currentColor = colorPresets[8];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Pink"));
            break;
        case '0':
            currentColor = colorPresets[9];
            useMultiColor = false;
            currentMode = 2;
            Serial.println(F(">> Purple"));
            break;
        
        // ===== MODE SELECTION =====
        case 'R':
        case 'r':
            currentMode = 0;
            Serial.println(F(">> Rainbow"));
            break;
        case 'P':
        case 'p':
            currentMode = 1;
            Serial.println(F(">> Pulse"));
            break;
        case 'S':
        case 's':
            currentMode = 2;
            Serial.println(F(">> Static"));
            break;
        
        case 'W':
        case 'w':
            currentMode = 3;
            Serial.println(F(">> Wipe"));
            break;
        case 'T':
        case 't':
            currentMode = 4;
            Serial.println(F(">> Theater"));
            break;
        case 'K':
        case 'k':
            currentMode = 5;
            Serial.println(F(">> Sparkle"));
            break;
        case 'N':
        case 'n':
            currentMode = 6;
            Serial.println(F(">> Sinelon"));
            break;
        case 'B':
        case 'b':
            currentMode = 7;
            Serial.println(F(">> BPM"));
            break;
        case 'C':
        case 'c':
            currentMode = 8;
            Serial.println(F(">> Confetti"));
            break;
        case 'F':
        case 'f':
            currentMode = 9;
            Serial.println(F(">> Fire"));
            break;
        case 'X':
        case 'x':
            currentMode = 10;
            Serial.println(F(">> Strobe"));
            break;
        case 'E':
        case 'e':
            currentMode = 11;
            Serial.println(F(">> Breathing"));
            break;
        case 'Y':
        case 'y':
            currentMode = 12;
            Serial.println(F(">> Tipsy"));
            break;
        case 'J':
        case 'j':
            useMultiColor = true;
            currentMode = 13; // Set to multicolor effect, but now it acts as a global toggle too
            Serial.println(F(">> Color: Multi-Rainbow"));
            break;
        
        // ===== BRIGHTNESS CONTROL =====
        case '+':
            currentBrightness = constrain(currentBrightness + 15, 0, 255);
            FastLED.setBrightness(currentBrightness);
            Serial.print(F(">> Bright: "));
            Serial.println(currentBrightness);
            break;
        case '-':
            currentBrightness = constrain(currentBrightness - 15, 0, 255);
            FastLED.setBrightness(currentBrightness);
            Serial.print(F(">> Bright: "));
            Serial.println(currentBrightness);
            break;
        
        // ===== SPEED CONTROL =====
        case '>':
            effectSpeed = max((int)effectSpeed - 5, 1);
            Serial.print(F(">> Speed: "));
            Serial.println(effectSpeed);
            break;
        case '<':
            effectSpeed = min(effectSpeed + 5, 200);
            Serial.print(F(">> Speed: "));
            Serial.println(effectSpeed);
            break;
        
        // ===== SPEED PRESETS (Q, D, V, Z, M for quick speeds) =====
        case 'Q':
            effectSpeed = 5;
            Serial.println(F(">> Speed: Very Fast"));
            break;
        case 'D':
        case 'd':
            effectSpeed = 15;
            Serial.println(F(">> Speed: Fast"));
            break;
        case 'V':
        case 'v':
            effectSpeed = 30;
            Serial.println(F(">> Speed: Medium"));
            break;
        case 'Z':
        case 'z':
            effectSpeed = 50;
            Serial.println(F(">> Speed: Slow"));
            break;
        case 'M':
        case 'm':
            effectSpeed = 100;
            Serial.println(F(">> Speed: Very Slow"));
            break;
        
        // ===== CUSTOM COLOR RGB INPUT =====
        case 'G':
        case 'g':
            Serial.println(F("Enter RGB (e.g., 255,128,64)"));
            break;
        
        // ===== HUE SHIFT SPEED =====
        case 'H':
        case 'h':
            Serial.println(F("Use > / < for hue speed"));
            break;
        
        // ===== AUTO-CYCLE MODE =====
        case 'A':
        case 'a':
            autoCycleMode = !autoCycleMode;
            autoModeIndex = 0;
            modeChangeTimer = 0;
            if (autoCycleMode) {
                Serial.println(F(">> Auto-Cycle: ON"));
            } else {
                Serial.println(F(">> Auto-Cycle: OFF"));
            }
            break;
        
        // ===== PIN INFORMATION =====
        case 'I':
        case 'i':
            displayPinInfo();
            break;
        
        // ===== BRIGHTNESS PRESETS =====
        case '!':
            currentBrightness = 64;
            FastLED.setBrightness(currentBrightness);
            Serial.println(F(">> Bright: Low (25%)"));
            break;
        case '@':
            currentBrightness = 128;
            FastLED.setBrightness(currentBrightness);
            Serial.println(F(">> Bright: Medium (50%)"));
            break;
        
        // ===== EFFECT INTENSITY =====
        case '#':
            effectIntensity = max((int)effectIntensity - 30, 0);
            Serial.print(F(">> Intensity: "));
            Serial.println(effectIntensity);
            break;
        case '$':
            effectIntensity = min((int)effectIntensity + 30, 255);
            Serial.print(F(">> Intensity: "));
            Serial.println(effectIntensity);
            break;
        
        // ===== COLOR SATURATION =====
        case '%':
            colorSaturation = max((int)colorSaturation - 30, 0);
            Serial.print(F(">> Saturation: "));
            Serial.println(colorSaturation);
            break;
        case '^':
            colorSaturation = min((int)colorSaturation + 30, 255);
            Serial.print(F(">> Saturation: "));
            Serial.println(colorSaturation);
            break;
        
        // ===== HUE ROTATION SPEED =====
        case '&':
            hueRotationSpeed = max((int)hueRotationSpeed - 1, 1);
            Serial.print(F(">> Hue Speed: "));
            Serial.println(hueRotationSpeed);
            break;
        case '*':
            hueRotationSpeed = min((int)hueRotationSpeed + 1, 5);
            Serial.print(F(">> Hue Speed: "));
            Serial.println(hueRotationSpeed);
            break;
        
        // ===== RESET ALL DEFAULTS =====
        case '(':
            currentBrightness = 255;
            effectSpeed = 10;
            effectIntensity = 128;
            colorSaturation = 255;
            hueRotationSpeed = 1;
            FastLED.setBrightness(currentBrightness);
            Serial.println(F(">> All settings reset to default"));
            break;
        
        // ===== SHOW CUSTOMIZATION VALUES =====
        case ')':
            Serial.println(F("\n=== CUSTOMIZATION VALUES ==="));
            Serial.print(F("Brightness: "));
            Serial.println(currentBrightness);
            Serial.print(F("Effect Speed: "));
            Serial.println(effectSpeed);
            Serial.print(F("Intensity: "));
            Serial.println(effectIntensity);
            Serial.print(F("Saturation: "));
            Serial.println(colorSaturation);
            Serial.print(F("Hue Speed: "));
            Serial.println(hueRotationSpeed);
            Serial.println(F("==========================\n"));
            break;
        
        // ===== LED CUSTOMIZATION =====
        case ';':
            ledReverse = !ledReverse;
            Serial.print(F(">> LED Reverse: "));
            Serial.println(ledReverse ? F("ON") : F("OFF"));
            break;
        
        case '\'':
            ledMirror = !ledMirror;
            Serial.print(F(">> LED Mirror: "));
            Serial.println(ledMirror ? F("ON") : F("OFF"));
            break;
        
        case '[':
            waveDirection = !waveDirection;
            Serial.print(F(">> Wave Direction: "));
            Serial.println(waveDirection ? F("Right") : F("Left"));
            break;
        
        case ']':
            rainbowMode = (rainbowMode + 1) % 4;
            Serial.print(F(">> Rainbow Mode: "));
            switch(rainbowMode) {
                case 0: Serial.println(F("Wavelength")); break;
                case 1: Serial.println(F("Hue-Only")); break;
                case 2: Serial.println(F("Pastel")); break;
                case 3: Serial.println(F("Saturated")); break;
            }
            break;
        
        case '{':
            clearAllLeds();
            Serial.println(F(">> All LEDs cleared"));
            break;
        
        case '}':
            displayLedSettings();
            break;
        
        default:
            // Ignore unknown commands
            break;
    }
}

void rainbowCycle(uint8_t wait) {
    static uint8_t hue = 0;
    for(int i = 0; i < NUM_LEDS; i++) {
        uint8_t ledSat = colorSaturation;
        uint8_t ledVal = 255;
        
        // Apply different rainbow modes
        if (rainbowMode == 1) {
            // Hue-only mode
            ledSat = 255;
            ledVal = 200;
        } else if (rainbowMode == 2) {
            // Pastel mode
            ledSat = 100;
            ledVal = 255;
        } else if (rainbowMode == 3) {
            // Saturated mode
            ledSat = 255;
            ledVal = 255;
        }
        
        leds[i] = CHSV(hue + (i * 10), ledSat, ledVal);
    }
    
    reverseLeds();
    
    FastLED.show();
    hue += hueRotationSpeed;  // Use customizable hue rotation speed
    delay(wait);
}

void pulseEffect(uint8_t wait) {
    static uint8_t brightness = 0;
    static int8_t direction = 5;
    
    brightness += direction;
    if(brightness >= effectIntensity || brightness <= 0) {
        direction = -direction;
    }
    
    fill_solid(leds, NUM_LEDS, currentColor);
    FastLED.setBrightness(brightness);
    FastLED.show();
    delay(wait);
    FastLED.setBrightness(currentBrightness);  // Restore original brightness
}

// Fill LEDs one by one with the current color (Non-blocking)
void colorWipe(uint8_t wait) {
    static unsigned long lastUpdate = 0;
    static int currentLed = 0;
    static bool state = true;
    
    if (millis() - lastUpdate >= wait) {
        lastUpdate = millis();
        leds[currentLed] = state ? getPixelColor(currentLed) : CRGB::Black;
        currentLed++;
        if (currentLed >= NUM_LEDS) {
            currentLed = 0;
            state = !state;
        }
        reverseLeds();
        FastLED.show();
    }
}

// Classic theater chase (moving dots) - Non-blocking
void theaterChase(uint8_t wait) {
    static unsigned long lastUpdate = 0;
    static int q = 0;
    
    if (millis() - lastUpdate >= wait) {
        lastUpdate = millis();
        fill_solid(leds, NUM_LEDS, CRGB::Black);
        for(int i = 0; i < NUM_LEDS; i += 3) {
            int pos = (i + q) % NUM_LEDS;
            leds[pos] = getPixelColor(pos);
        }
        q = (q + 1) % 3;
        reverseLeds();
        FastLED.show();
    }
}

// Sparkle: randomly light a pixel briefly (Non-blocking)
void sparkle(uint8_t wait) {
    static unsigned long lastUpdate = 0;
    // Faster fading for high-speed sparkle
    uint8_t fadeRate = map(wait, 1, 200, 50, 5); 
    fadeToBlackBy(leds, NUM_LEDS, fadeRate);
    
    if (millis() - lastUpdate >= wait) {
        lastUpdate = millis();
        leds[random(NUM_LEDS)] = getPixelColor(0);
    }
    reverseLeds();
    FastLED.show();
}

void setStaticColor(CRGB color) {
    if (useMultiColor) {
        multicolorEffect(0); 
    } else {
        fill_solid(leds, NUM_LEDS, color);
        reverseLeds();
        FastLED.show();
    }
}

// --- Artistic / Euphoric Effects ---

// Sinelon: a moving dot with fading trails
void sinelon(uint8_t wait) {
    // Map wait (1-200) to BPM (240-10) for true speed range
    uint8_t bpm = map(wait, 1, 200, 240, 10);
    fadeToBlackBy(leds, NUM_LEDS, 20);
    int pos = beatsin16(bpm, 0, NUM_LEDS - 1);
    
    if (waveDirection) pos = (NUM_LEDS - 1) - pos;
    leds[pos] += getPixelColor(pos);
    
    reverseLeds();
    FastLED.show();
}

// BPM: pulse all LEDs by a beat
void bpmEffect(uint8_t wait) {
    uint8_t bpm = map(wait, 1, 200, 180, 20);
    uint8_t beat = beatsin8(bpm, 64, 255);
    uint8_t v = (uint16_t(beat) * currentBrightness) / 255;
    
    for (int i = 0; i < NUM_LEDS; i++) {
        CRGB c = getPixelColor(i);
        leds[i] = CRGB((c.r * v) / 255, (c.g * v) / 255, (c.b * v) / 255);
    }
    reverseLeds();
    FastLED.show();
}

// Confetti: random colored speckles
void confetti(uint8_t wait) {
    static unsigned long lastUpdate = 0;
    fadeToBlackBy(leds, NUM_LEDS, 10);
    
    if (millis() - lastUpdate >= wait) {
        lastUpdate = millis();
        int pos = random(NUM_LEDS);
        leds[pos] += getPixelColor(pos);
    }
    reverseLeds();
    FastLED.show();
}

// Simple Fire effect
void fireEffect(uint8_t wait) {
    static unsigned long lastUpdate = 0;
    if (millis() - lastUpdate < wait) return;
    lastUpdate = millis();

    static uint8_t heat[NUM_LEDS];
    for (int i = 0; i < NUM_LEDS; i++) {
        heat[i] = qsub8(heat[i], random8(0, ((55 * 10) / NUM_LEDS) + 2));
    }
    for (int k = NUM_LEDS - 1; k >= 2; k--) {
        heat[k] = (heat[k - 1] + heat[k - 2] + heat[k - 2]) / 3;
    }
    if (random8() < 120) {
        int y = random8(min(NUM_LEDS, 7));
        heat[y] = qadd8(heat[y], random8(160, 255));
    }
    for (int j = 0; j < NUM_LEDS; j++) {
        leds[j] = HeatColor(scale8(heat[j], 240));
    }
    reverseLeds();
    FastLED.show();
}

// Strobe effect: rapid on/off
void strobeEffect(uint8_t wait) {
    static unsigned long lastUpdate = 0;
    static bool isOn = false;
    
    // Strobe timing should be much tighter at fast speeds
    uint16_t interval = (isOn) ? max(5, (int)(wait * effectIntensity / 100)) : wait;
    
    if (millis() - lastUpdate >= interval) {
        lastUpdate = millis();
        isOn = !isOn;
        if (isOn) {
            for (int i = 0; i < NUM_LEDS; i++) leds[i] = getPixelColor(i);
        } else {
            fill_solid(leds, NUM_LEDS, CRGB::Black);
        }
        reverseLeds();
        FastLED.show();
    }
}

// Breathing effect: smooth fade
void breathingEffect(uint8_t wait) {
    // Map wait to BPM for the breathing cycle
    uint8_t bpm = map(wait, 1, 200, 100, 5);
    uint8_t val = beatsin8(bpm, 0, 255);
    
    // Smooth the curve
    uint8_t bright = (cubicwave8(val) * currentBrightness) / 255;
    
    for (int i = 0; i < NUM_LEDS; i++) leds[i] = getPixelColor(i);
    
    FastLED.setBrightness(bright);
    reverseLeds();
    FastLED.show();
    FastLED.setBrightness(currentBrightness);
}

// Tipsy effect: sync with fan speed
void tipsyEffect(uint8_t wait) {
    uint8_t bpm = map(wait, 1, 200, 220, 8); 
    bpm = max(1, (bpm * tipsySyncScale) / 128);

    uint8_t osc = beatsin8(bpm, 0, 255);
    for (int i = 0; i < NUM_LEDS; i++) {
        uint8_t local = beatsin8(bpm + (i * 8), 0, 255);
        uint8_t val = (local + osc) / 2;
        leds[i] = getPixelColor(i);
        leds[i].nscale8_video(val);
    }
    reverseLeds();
    FastLED.show();
}

// Multi-color effect
void multicolorEffect(uint8_t wait) {
    static unsigned long lastUpdate = 0;
    if (wait > 0 && millis() - lastUpdate < wait) return;
    lastUpdate = millis();

    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CHSV(globalHue + (i * (255 / NUM_LEDS)), colorSaturation, 255);
    }
    reverseLeds();
    FastLED.show();
}

// ===== UTILITY FUNCTIONS =====

void displayStatus() {
    Serial.println(F("\n========== STATUS =========="));
    Serial.print(F("Mode: "));
    const char* modeNames[] = {"Rainbow","Pulse","Static","Wipe","Theater","Sparkle","Sinelon","BPM","Confetti","Fire","Strobe","Breathing","Tipsy","Multi-Color"};
    if(currentMode < 14) Serial.println(modeNames[currentMode]);
    else Serial.println(F("?"));
    if (useMultiColor) {
        Serial.println(F("Color: Multi-Rainbow"));
    } else {
        Serial.print(F("RGB(")); Serial.print(currentColor.r); Serial.print(","); Serial.print(currentColor.g); Serial.print(","); Serial.print(currentColor.b); Serial.println(")");
    }
    Serial.println(F("=========================\n"));
}

void displayPinInfo() {
    Serial.println(F("\n========== PIN INFO =========="));
    Serial.print(F("LED Data Pin: ")); Serial.println(LED_PIN);
    Serial.print(F("Number of LEDs: ")); Serial.println(NUM_LEDS);
    Serial.println(F("==============================\n"));
}

void displayLedSettings() {
    Serial.println(F("\n=== LED SETTINGS ==="));
    Serial.print(F("Reverse: ")); Serial.println(ledReverse ? "ON" : "OFF");
    Serial.print(F("Mirror: ")); Serial.println(ledMirror ? "ON" : "OFF");
    Serial.println(F("==================\n"));
}

void clearAllLeds() {
    fill_solid(leds, NUM_LEDS, CRGB::Black);
    FastLED.show();
}

void reverseLeds() {
    if (ledReverse) {
        for (int i = 0; i < NUM_LEDS / 2; i++) {
            CRGB temp = leds[i];
            leds[i] = leds[NUM_LEDS - 1 - i];
            leds[NUM_LEDS - 1 - i] = temp;
        }
    }
}

// Helper: Get the intended color for a pixel based on settings
CRGB getPixelColor(int index) {
    if (useMultiColor) {
        // Return a color from the global rainbow palette
        return CHSV(globalHue + (index * (255 / NUM_LEDS)), colorSaturation, 255);
    }
    return currentColor;
}
