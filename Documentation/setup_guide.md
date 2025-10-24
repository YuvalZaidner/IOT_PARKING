# 🚀 Setup Guide - מדריך התקנה מלא

מדריך זה ילווה אותך בהתקנה מלאה של מערכת החניה החכמה.

---

## 📋 דרישות מקדימות

### חומרה:
- ✅ 3× ESP32 DevKit v1 (30-pin)
- ✅ 3× HC-SR04 Ultrasonic Sensor
- ✅ 3× RGB LED (Common Cathode)
- ✅ 9× Resistors 220Ω
- ✅ 3× Breadboard (Half-size)
- ✅ 30× Jumper Wires (M-M)
- ✅ 3× USB Micro Cable (data-capable)
- ✅ מחשב עם Python 3.9+ ו-Arduino IDE

### תוכנה:
- ✅ Python 3.9 ומעלה
- ✅ Arduino IDE 1.8.19+ או PlatformIO
- ✅ חשבון Firebase (חינמי)
- ✅ דפדפן מודרני (Chrome, Firefox, Safari)

---

## 🔥 שלב 1: הכנת Firebase

### 1.1 יצירת פרויקט Firebase

1. **גש ל-Firebase Console**:
   - פתח: https://console.firebase.google.com
   - לחץ **"Add project"** או **"הוסף פרויקט"**

2. **הגדר שם לפרויקט**:
   ```
   שם מומלץ: smart-parking-iot
   ```

3. **השבת Google Analytics** (לא חובה):
   - אפשר לכבות למען פשטות

4. **לחץ "Create project"** והמתן להשלמה

---

### 1.2 הפעלת Realtime Database

1. **מהתפריט הצדדי** → **Build** → **Realtime Database**

2. **לחץ "Create Database"**

3. **בחר מיקום (Location)**:
   ```
   מומלץ: europe-west1 (בלגיה)
   ```

4. **Security Rules** - בחר **"Start in test mode"**:
   ```json
   {
     "rules": {
       ".read": true,
       ".write": true
     }
   }
   ```
   
  
   
5. **העתק את ה-Database URL**:
   
   דוגמה: https://smart-parking-iot-default-rtdb.europe-west1.firebasedatabase.app
   ```
   שמור את זה - תצטרך אותו בהמשך!

---

### 1.3 יצירת Service Account (מפתחות גישה)

1. **מהתפריט** → **Project Settings** (⚙️) → **Service accounts**

2. **לחץ "Generate new private key"**

3. **אשר** → קובץ JSON יורד למחשב שלך

4. **שנה שם לקובץ**:
   ```bash
   mv ~/Downloads/smart-parking-iot-*.json ~/Desktop/IOT\ F/Server/secret.json
   ```

5. ⚠️ **חשוב:** אל תשתף קובץ זה עם אף אחד!

---

### 1.4 קבלת API Key

1. **מהתפריט** → **Project Settings** → **General**

2. **בחלק "Your apps"** → לחץ **Web App** (</> icon)

3. **תן שם לאפליקציה**:
   ```
   שם: ESP32-Parking
   ```

4. **העתק את `apiKey`**:
   ```javascript
   const firebaseConfig = {
     apiKey: "AIzaSyBCg3n1wtcmBncNHEfxjL7PT5hXlEJB4TE", // ← זה!
     ...
   };
   ```

5. שמור את ה-API Key - תצטרך אותו לקוד ESP32!

---

## 🐍 שלב 2: התקנת Python Backend

### 2.1 בדיקת גרסת Python

```bash
# בדוק שיש לך Python 3.9+
python3 --version
# צריך להציג: Python 3.9.x או גבוה יותר

# אם אין לך Python 3.9+, התקן מ:
# https://www.python.org/downloads/
```

---

### 2.2 התקנת ספריות Python

```bash
cd "/Users/sondostaha/Desktop/IOT F/Server"

# צור סביבה וירטואלית (מומלץ)
python3 -m venv .venv

# הפעל את הסביבה
source .venv/bin/activate  # macOS/Linux
# או (Windows PowerShell)
# .\.venv\Scripts\Activate.ps1

# התקן את הספריות
pip install -r requirements.txt

# בדוק שההתקנה עברה בהצלחה
pip list | grep firebase
# צריך להציג: firebase-admin X.Y.Z
```

---

### 2.3 בדיקת חיבור ל-Firebase

```bash
# הרץ את כלי הבדיקה
cd "/Users/sondostaha/Desktop/IOT F/Tools"
python setup_simulation.py --test

# פלט מצופה:
# [Firebase Test] OK - root data preview: None
# או
# [Firebase Test] OK - root data preview: {...}
```

**אם יש שגיאה:**
```
[Firebase Test] FAILED: No such file or directory: 'secret.json'
→ הקובץ secret.json לא נמצא. ודא שהוא ב-Server/secret.json

[Firebase Test] FAILED: Invalid credentials
→ הקובץ secret.json פגום או לא נכון. הורד מחדש מ-Firebase Console
```

---

### 2.4 אתחול מבנה החניון (פעם אחת בלבד!)

```bash
cd "/Users/sondostaha/Desktop/IOT F/Server"
python Init_Park.py
```

**פלט מצופה:**
```
Initializing parking lot: 10 rows × 5 cols
Entry point: (3, 0)
BFS: Computing distances...
✅ Created 50 spots in Firebase under /SondosPark/SPOTS
✅ Parking lot initialized successfully!
```

⚠️ **זהירות:** הרצה נוספת של `Init_Park.py` תמחק את כל הנתונים ותאתחל מחדש!

---

### 2.5 בדיקת Dashboard

```bash
cd "/Users/sondostaha/Desktop/IOT F/Server"
python dashboard.py
```

**פלט מצופה:**
```
 * Serving Flask app 'dashboard'
 * Running on http://0.0.0.0:8000
 * Running on http://192.168.1.123:8000  ← הכתובת שלך
```

**פתח דפדפן:**
```
http://localhost:8000
```

אמור להיראות רשת של 10×5 חניות, הכל בצבע כחול (FREE).

---

## 📡 שלב 3: התקנת Arduino IDE + ספריות

### 3.1 התקנת Arduino IDE

1. **הורד מ-** https://www.arduino.cc/en/software
2. **התקן** (גרסה 1.8.19 ומעלה)
3. **פתח Arduino IDE**

---

### 3.2 הוספת ESP32 Boards

1. **File** → **Preferences**

2. **Additional Board Manager URLs** - הוסף:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```

3. **Tools** → **Board** → **Boards Manager**

4. **חפש:** `esp32`

5. **התקן:** `esp32 by Espressif Systems` גרסה 2.0.14

---

### 3.3 התקנת ספריות נדרשות

#### שיטה 1: דרך Library Manager (מומלץ)

1. **Sketch** → **Include Library** → **Manage Libraries**

2. **התקן את הספריות הבאות:**

   | ספרייה | גרסה | חיפוש |
   |--------|------|-------|
   | **WiFiManager** | 2.0.16-rc.2 | `tzapu wifimanager` |
   | **Firebase ESP Client** | 4.3.14 | `mobizt firebase` |
   | **ArduinoJson** | 6.21.3 | `arduinojson` |

3. **לחץ "Install"** על כל אחת

---

#### שיטה 2: PlatformIO (חלופה)

אם אתה משתמש ב-PlatformIO:

```bash
cd "/Users/sondostaha/Desktop/IOT F/ESP32"
pio lib install "tzapu/WiFiManager@^2.0.16-rc.2"
pio lib install "mobizt/Firebase ESP Client@^4.3.14"
pio lib install "bblanchon/ArduinoJson@^6.21.3"
```

---

### 3.4 בדיקת התקנה

```bash
# Arduino IDE → File → Examples → WiFiManager → AutoConnect
# אם רואה את הדוגמה - ההתקנה הצליחה!
```

---

## 🔌 שלב 4: חיווט ESP32

### 4.1 חיבור HC-SR04 (חיישן מרחק)

```
HC-SR04          →  ESP32
─────────────────────────────
VCC              →  5V
GND              →  GND
TRIG             →  GPIO 5
ECHO             →  GPIO 18
```

**טיפ:** השתמש בכבלים קצרים (10-15 ס"מ) למניעת רעש.

---

### 4.2 חיבור RGB LED (Common Cathode)

```
RGB LED          →  ESP32         →  Resistor
───────────────────────────────────────────────
Red (R)          →  GPIO 23       →  220Ω → R pin
Green (G)        →  GPIO 22       →  220Ω → G pin
Blue (B)         →  GPIO 21       →  220Ω → B pin
Cathode (-)      →  GND           →  ישירות ל-GND
```

**זיהוי רגליים:**
```
   ┌─────┐
   │ RGB │
   └─┬┬┬┬┘
     ││││
     RGBC  ← R=Red, G=Green, B=Blue, C=Cathode (הארוכה)
```

**⚠️ Common Anode?** אם יש לך LED Common Anode, שנה בקוד:
```cpp
const bool LED_COMMON_ANODE = true;
```

---

### 4.3 תרשים מלא (Breadboard Layout)

```
           ESP32 DevKit v1
    ┌───────────────────────┐
    │                       │
5V  │●                     ●│ GPIO 23 ──[220Ω]── LED Red
GND │●                     ●│ GPIO 22 ──[220Ω]── LED Green
    │                       │ GPIO 21 ──[220Ω]── LED Blue
    │                       │
    │                     ●│ GPIO 5  ── HC-SR04 TRIG
    │                     ●│ GPIO 18 ── HC-SR04 ECHO
    │                       │
GND │●─────────────────────●│ LED GND
    └───────────────────────┘
```

**תמונה:** ראה `Assets/diagrams/wiring_diagram.png`

---

## 💻 שלב 5: תכנות ESP32

### 5.1 עריכת הקוד

1. **פתח את הקובץ:**
   ```
   ESP32/SpotNode/SpotNode.ino
   ```

2. **ערוך את הפרמטרים הבאים:**

   ```cpp
   // שורות 24-25 - Firebase credentials
   #define API_KEY      "YOUR_API_KEY_HERE"  // ← מ-Firebase Console
   #define DATABASE_URL "https://YOUR_PROJECT.firebaseio.com"  // ← מ-RTDB
   
   // שורה 26 - נתיב החנייה (שונה לכל ESP32!)
   const char* SPOT_PATH = "/SondosPark/SPOTS/0,0";  // ← Node 1
   ```

3. **שמור את הקובץ** (Ctrl+S / Cmd+S)

---

### 5.2 העלאה ל-ESP32

1. **חבר ESP32 למחשב** דרך USB Micro

2. **Arduino IDE** → **Tools**:
   - **Board:** "ESP32 Dev Module"
   - **Upload Speed:** 921600
   - **Flash Frequency:** 80MHz
   - **Partition Scheme:** "Default 4MB"
   - **Port:** בחר את הפורט (macOS: `/dev/cu.usbserial-*`, Windows: `COM3`)

3. **לחץ "Upload"** (→ כפתור)

4. **המתן** (כ-30 שניות)

5. **פלט מצופה:**
   ```
   Connecting.....
   Writing at 0x00001000... (100%)
   Hash of data verified.
   Leaving...
   Hard resetting via RTS pin...
   ```

---

### 5.3 הגדרת Wi-Fi (פעם אחת לכל ESP32)

1. **פתח Serial Monitor:**
   - **Tools** → **Serial Monitor**
   - **Baud Rate:** `115200`

2. **ESP32 יציג:**
   ```
   * WiFi: trying autoConnect()
   *WM: No saved credentials. Opening portal...
   *WM: Access Point: Sondos-Parking-Setup
   ```

3. **מהטלפון/מחשב:**
   - חבר ל-Wi-Fi: **"Sondos-Parking-Setup"**
   - סיסמה: **"12345678"**

4. **פורטל נפתח אוטומטית** (או גש ל-`192.168.4.1`):
   - בחר את רשת ה-Wi-Fi שלך
   - הזן סיסמה
   - לחץ **"Save"**

5. **ESP32 מתחבר:**
   ```
   ✅ WiFi connected. IP: 192.168.1.105
   Anonymous sign-in success.
   [STREAM] status -> FREE
   ```

---

### 5.4 תכנות ESP32 נוספים (Nodes 2 & 3)

**חזור על התהליך**, אבל **שנה רק את `SPOT_PATH`**:

```cpp
// ESP32 #2:
const char* SPOT_PATH = "/SondosPark/SPOTS/0,1";

// ESP32 #3:
const char* SPOT_PATH = "/SondosPark/SPOTS/0,2";
```

---

## 🧪 שלב 6: בדיקת המערכת

### 6.1 בדיקת ESP32 בודד

1. **Serial Monitor פתוח** (baud 115200)

2. **העבר יד** מול החיישן (קרוב מ-12 ס"מ):
   ```
   Distance: 8
   Distance: 7
   Distance: 6
   [Publish] status -> OCCUPIED
   ```

3. **LED צריך להפוך לאדום** 🔴

4. **הרחק את היד** (מעל 18 ס"מ):
   ```
   Distance: 25
   Distance: 30
   [Publish] status -> FREE
   ```

5. **LED צריך להפוך לכחול** 🔵

---

### 6.2 בדיקת Dashboard

1. **Dashboard רץ** (אם לא: `python dashboard.py`)

2. **רענן את הדפדפן** (`http://localhost:8000`)

3. **העבר יד מול חיישן:**
   - **Dashboard צריך להראות** את החנייה מתחלפת לאדום

4. **הרחק יד:**
   - **Dashboard צריך להראות** כחול שוב

---

### 6.3 בדיקת סימולציה

```bash
# טרמינל 1: Dashboard
cd Server
python dashboard.py

# טרמינל 2: Simulation
cd Server
export N_ARRIVALS=5
export ARRIVAL_INTERVAL_SECONDS=3
python simulation_sondos.py
```

**תראה:**
- רכבים מגיעים כל 3 שניות
- חניות הופכות לכתום (WAITING) ואז לאדום (OCCUPIED)
- ב-Dashboard: עדכון חי של הצבעים

---

## 🎉 שלב 7: פריסה מלאה

### 7.1 פריסת 3 ESP32 Nodes

1. **ESP32 #1** → חנייה `(0,0)` - `SPOT_PATH = "/SondosPark/SPOTS/0,0"`
2. **ESP32 #2** → חנייה `(0,1)` - `SPOT_PATH = "/SondosPark/SPOTS/0,1"`
3. **ESP32 #3** → חנייה `(0,2)` - `SPOT_PATH = "/SondosPark/SPOTS/0,2"`

---

### 7.2 הרצת המערכת המלאה

**טרמינל 1:**
```bash
cd Server
python dashboard.py
# Dashboard: http://localhost:8000
```

**טרמינל 2 (אופציונלי - סימולציה):**
```bash
cd Server
export N_ARRIVALS=0  # אינסוף
python simulation_sondos.py
```

**3 ESP32 פעילים** - מחוברים לחשמל ו-Wi-Fi

---

### 7.3 גישה מטאבלט/טלפון

1. **מצא את ה-IP** של המחשב:
   ```bash
   ifconfig | grep "inet "
   # macOS: 192.168.1.123
   
   # או
   ipconfig  # Windows
   ```

2. **מהטאבלט/טלפון** (באותה רשת):
   ```
   http://192.168.1.123:8000
   ```

3. **Dashboard צריך להיפתח** עם עדכון חי!

---

## ⚠️ פתרון בעיות נפוצות

### ESP32 לא מתחבר ל-Wi-Fi
```bash
# פתרון: החזק BOOT button 3 שניות → Portal נפתח מחדש
```

### Firebase: "Permission Denied"
```bash
# פתרון: שנה Security Rules ב-Firebase Console ל-test mode
```

### Dashboard לא מראה עדכונים
```bash
# פתרון 1: רענן דפדפן (Ctrl+Shift+R)
# פתרון 2: בדוק Console (F12) לשגיאות JavaScript
```

### LED לא נדלק
```bash
# פתרון: בדוק שה-resistors מחוברים נכון (220Ω)
# אם LED Common Anode - שנה: LED_COMMON_ANODE = true
```

**לפתרון בעיות מפורט:** ראה [troubleshooting.md](troubleshooting.md)

---

## 📚 משאבים נוספים

- **[calibration.md](calibration.md)** - כיול חיישני מרחק
- **[troubleshooting.md](troubleshooting.md)** - פתרון בעיות מתקדם
- **[error_messages.md](error_messages.md)** - הסבר על הודעות שגיאה

---

## ✅ Checklist - רשימת ביקורת

- [ ] Firebase פרויקט נוצר
- [ ] Realtime Database פעיל
- [ ] Service Account (secret.json) הורד
- [ ] Python 3.9+ מותקן
- [ ] ספריות Python מותקנות (`pip install -r requirements.txt`)
- [ ] `Init_Park.py` הורץ בהצלחה
- [ ] Dashboard עולה ב-`http://localhost:8000`
- [ ] Arduino IDE + ESP32 boards מותקנים
- [ ] ספריות (WiFiManager, Firebase, ArduinoJson) מותקנות
- [ ] 3 ESP32 מחווטים נכון (HC-SR04 + RGB LED)
- [ ] כל ESP32 מתוכנת עם `SPOT_PATH` שונה
- [ ] כל ESP32 מחובר ל-Wi-Fi
- [ ] Serial Monitor מראה "status -> FREE/OCCUPIED"
- [ ] Dashboard מראה עדכונים חיים
- [ ] סימולציה פועלת (אופציונלי)

---

**בהצלחה! 🚀**

אם נתקלת בבעיות, פנה ל-[troubleshooting.md](troubleshooting.md) או פתח issue ב-GitHub.
