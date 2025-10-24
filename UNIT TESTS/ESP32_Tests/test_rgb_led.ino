const int LED_R = 23;
const int LED_G = 22;
const int LED_B = 21;
const bool COMMON_ANODE = false; // change to true if using common anode

void setColor(int r, int g, int b) {
  if (COMMON_ANODE) {
    r = 255 - r;
    g = 255 - g;
    b = 255 - b;
  }
  analogWrite(LED_R, r);
  analogWrite(LED_G, g);
  analogWrite(LED_B, b);
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_R, OUTPUT);
  pinMode(LED_G, OUTPUT);
  pinMode(LED_B, OUTPUT);
  Serial.println("💡 RGB LED Test Started");
}

void loop() {
  Serial.println("Red");
  setColor(255, 0, 0);
  delay(1000);

  Serial.println("Green");
  setColor(0, 255, 0);
  delay(1000);

  Serial.println("Blue");
  setColor(0, 0, 255);
  delay(1000);

  Serial.println("White");
  setColor(255, 255, 255);
  delay(1000);

  Serial.println("Off");
  setColor(0, 0, 0);
  delay(1000);
}
