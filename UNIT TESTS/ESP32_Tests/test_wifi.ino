#include <WiFi.h>

const char* WIFI_SSID = "Sondos";
const char* WIFI_PASS = "sondos2911";

void setup() {
  Serial.begin(115200);
  Serial.println("📶 WiFi Test Started");
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ Lost connection!");
  } else {
    Serial.println("✅ Still connected");
  }
  delay(5000);
}
