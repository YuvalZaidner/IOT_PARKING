#include <WiFi.h>
#include <Firebase_ESP_Client.h>
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"

// WiFi
const char* WIFI_SSID = "Sondos";
const char* WIFI_PASS = "sondos2911";

// Firebase
#define API_KEY      "AIzaSyBCg3n1wtcmBncNHEfxjL7PT5hXlEJB4TE"
#define DATABASE_URL "https://park-19f5b-default-rtdb.europe-west1.firebasedatabase.app"

FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;

void setup() {
  Serial.begin(115200);
  Serial.println("🔥 Firebase Test Started");

  // Connect WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi Connected");

  // Firebase setup
  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;
  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  // Test write
  if (Firebase.RTDB.setString(&fbdo, "/test/path", "Hello from ESP32")) {
    Serial.println("✅ Data written successfully!");
  } else {
    Serial.println("❌ Write failed:");
    Serial.println(fbdo.errorReason());
  }

  // Test read
  if (Firebase.RTDB.getString(&fbdo, "/test/path")) {
    Serial.print("✅ Read value: ");
    Serial.println(fbdo.stringData());
  } else {
    Serial.println("❌ Read failed:");
    Serial.println(fbdo.errorReason());
  }
}

void loop() {
  // Nothing to do
}
