#include <WiFi.h>
#include <WiFiManager.h>          // by tzapu
#include <Firebase_ESP_Client.h>
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"

// ===================== Wi-Fi Status LED & BOOT button ======================
const int WIFI_LED_PIN     = 2;    // built-in LED on most ESP32 dev boards
const bool LED_ACTIVE_LOW  = false;// set true if LOW turns LED ON on your board
const int  BTN_PIN         = 0;    // BOOT button (GPIO0)
const uint32_t LONGPRESS_MS = 3000;

WiFiManager wm;
bool portalActive = false;

void wifiLedWrite(bool on) {
  int level = on
      ? (LED_ACTIVE_LOW ? LOW : HIGH)
      : (LED_ACTIVE_LOW ? HIGH : LOW);
  pinMode(WIFI_LED_PIN, OUTPUT);
  digitalWrite(WIFI_LED_PIN, level);
}

void setWifiLedConnected(bool connected) {
  wifiLedWrite(connected); // ON when connected, OFF otherwise
}

// ===================== Your original config ================================
#define API_KEY      "AIzaSyBCg3n1wtcmBncNHEfxjL7PT5hXlEJB4TE"
#define DATABASE_URL "https://park-19f5b-default-rtdb.europe-west1.firebasedatabase.app"
const char* SPOT_PATH = "/SondosPark/SPOTS/0,0";

// LED pins (RGB)
const int LED_R = 23;
const int LED_G = 22;
const int LED_B = 21;
const bool LED_COMMON_ANODE = false;

// Ultrasonic pins
const int TRIG_PIN = 5;
const int ECHO_PIN = 18;

// Distance thresholds
const int THRESH_ENTER = 12;
const int THRESH_EXIT  = 18;

// Firebase globals
FirebaseData fbdo;
FirebaseData fbStream;
FirebaseAuth auth;
FirebaseConfig config;
String currentStatus = "UNKNOWN";  // Real status from DB

// ===================== LED (spot status) ===================================
void setRgb(bool r, bool g, bool b) {
  auto drive = [&](int pin, bool on) {
    digitalWrite(pin, LED_COMMON_ANODE ? !on : on);
  };
  drive(LED_R, r);
  drive(LED_G, g);
  drive(LED_B, b);
}

void showStatusOnLed(const String& s) {
  if (s == "FREE")          setRgb(false, false, true);   // Blue
  else if (s == "WAITING")  setRgb(true,  true,  false);  // Orange (R+G)
  else if (s == "OCCUPIED") setRgb(true,  false, false);  // Red
  else                      setRgb(false, false, false);  // Off
}

// ===================== Sensor ==============================================
long readDistanceCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) return -1;
  return duration / 58;
}

// ===================== WiFi via WiFiManager ================================
void wifiInitWithPortal() {
  WiFi.mode(WIFI_STA);
  setWifiLedConnected(false);

  Serial.println("* WiFi: trying autoConnect()");
  bool ok = wm.autoConnect("Sondos-Parking-Setup", "12345678"); // opens portal if no saved Wi-Fi
  if (!ok) {
    Serial.println("⚠️  Portal cancelled/failed. Rebooting…");
    delay(1000);
    ESP.restart();
  }

  // Connected
  Serial.print("✅ WiFi connected. IP: ");
  Serial.println(WiFi.localIP());
  setWifiLedConnected(true);
}

// Long-press BOOT at runtime → reset creds + reopen portal
void handleLongPressToReconfigure() {
  static bool wasDown = false;
  static uint32_t downAt = 0;

  bool down = (digitalRead(BTN_PIN) == LOW);
  if (down && !wasDown) downAt = millis();

  if (down && (millis() - downAt > LONGPRESS_MS)) {
    Serial.println("🔁 Long-press → reset Wi-Fi & open portal");
    wm.resetSettings();
    WiFi.disconnect(true, true);
    delay(200);

    portalActive = true;
    setWifiLedConnected(false); // OFF while not connected

    // Blocking until user saves Wi-Fi in portal
    wm.startConfigPortal("Sondos-Parking-Setup", "12345678");

    // Reconnected
    portalActive = false;
    setWifiLedConnected(true);
    Serial.print("✅ Reconnected. IP: ");
    Serial.println(WiFi.localIP());
    Serial.println("👍 Saved again. Next reset will auto-connect.");

    while (digitalRead(BTN_PIN) == LOW) delay(10); // wait release
  }
  wasDown = down;

  // Blink Wi-Fi LED while portal is active
  if (portalActive) {
    static unsigned long t = 0;
    static bool on = false;
    if (millis() - t > 400) {
      t = millis();
      on = !on;
      wifiLedWrite(on);
    }
  }
}

// ===================== Firebase ============================================
void streamCallback(FirebaseStream data) {
  if (data.dataTypeEnum() == fb_esp_rtdb_data_type_string) {
    currentStatus = data.stringData();
    currentStatus.trim();
    Serial.print("[STREAM] status -> "); Serial.println(currentStatus);
    showStatusOnLed(currentStatus);
  }
}

void streamTimeoutCallback(bool timeout) {
  if (timeout) Serial.println("[STREAM] timeout, trying to resume...");
}

bool firebaseAuthInit() {
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  config.token_status_callback = tokenStatusCallback;

  bool ok = Firebase.signUp(&config, &auth, "", ""); // anonymous
  if (!ok) {
    Serial.print("Auth error: ");
    Serial.println(config.signer.signupError.message.c_str());
  } else {
    Serial.println("Anonymous sign-in success.");
  }

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);
  return ok;
}

bool startStream() {
  String statusPath = String(SPOT_PATH) + "/status";
  if (!Firebase.RTDB.beginStream(&fbStream, statusPath)) {
    Serial.print("Stream error: ");
    Serial.println(fbStream.errorReason());
    return false;
  }
  Firebase.RTDB.setStreamCallback(&fbStream, streamCallback, streamTimeoutCallback);
  return true;
}

void publishStatus(const String& s) {
  if (!Firebase.ready()) return;
  String base = String(SPOT_PATH);
  if (!Firebase.RTDB.setString(&fbdo, base + "/status", s)) {
    Serial.print("FB set(status) error: ");
    Serial.println(fbdo.errorReason());
  }
  Firebase.RTDB.setInt(&fbdo, base + "/lastUpdateMs", millis());
}

// ========== Poll DB (fallback if stream fails) ==========
unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL = 3000;

void pollStatusFromDB() {
  if (!Firebase.ready()) return;
  String path = String(SPOT_PATH) + "/status";
  if (Firebase.RTDB.getString(&fbdo, path)) {
    String newStatus = fbdo.stringData();
    newStatus.trim();
    if (newStatus != currentStatus) {
      currentStatus = newStatus;
      Serial.print("[POLL] status -> "); Serial.println(currentStatus);
      showStatusOnLed(currentStatus);
    }
  }
}

// ===================== Arduino Setup =======================================
String lastDesired = "UNKNOWN";
unsigned long lastChangeTime = 0;
const unsigned long STABLE_TIME = 3000; // 3 seconds

void setup() {
  Serial.begin(115200);

  // IO
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  pinMode(BTN_PIN, INPUT_PULLUP);
  pinMode(WIFI_LED_PIN, OUTPUT);

  showStatusOnLed("UNKNOWN");
  setWifiLedConnected(false);

  // Wi-Fi via WiFiManager (no hardcoded SSID/PASS)
  wifiInitWithPortal();

  // Firebase
  firebaseAuthInit();
  while (!Firebase.ready()) delay(50);
  startStream();

  Serial.println("ℹ️  Hold BOOT button ~3s to re-open the Wi-Fi portal.");
}

// ===================== Loop ================================================
void loop() {
  // BOOT long-press handler + portal blink
  handleLongPressToReconfigure();

  // 1. Sensor reading
  long d = readDistanceCM();
  Serial.print("Distance: "); Serial.println(d);

  // 2. Determine desired status
  String desired = currentStatus;

  if (currentStatus == "WAITING") {
    if (d > 0 && d < THRESH_ENTER) {
      desired = "OCCUPIED";
    } else {
      desired = currentStatus; // stay WAITING
    }
  } else {
    if (d > 0 && d < THRESH_ENTER) {
      desired = "OCCUPIED";
    } else if (d > THRESH_EXIT) {
      desired = "FREE";
    }
  }

  // 3. Debounce/stabilize for 3 seconds
  if (desired != lastDesired) {
    lastDesired = desired;
    lastChangeTime = millis();
  }

  // 4. Update Firebase if stable and changed
  if ((millis() - lastChangeTime > STABLE_TIME) && desired != currentStatus && Firebase.ready()) {
    currentStatus = desired;
    publishStatus(currentStatus);
    showStatusOnLed(currentStatus);
  }

  // 5. Poll DB every 3 sec (fallback)
  if (millis() - lastPoll > POLL_INTERVAL) {
    pollStatusFromDB();
    lastPoll = millis();
  }

  delay(400);
}
