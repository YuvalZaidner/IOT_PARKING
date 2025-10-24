# 🔧 Troubleshooting Guide - פתרון בעיות

מדריך זה מכסה בעיות נפוצות ופתרונות עבור מערכת החניה החכמה.

---

## 🔥 Firebase Issues

### ❌ Firebase: "Permission Denied"

**תסמינים:**
```python
firebase_admin.exceptions.PermissionDeniedError: Permission denied
```

**גורמים אפשריים:**
1. Security Rules חוסמים גישה
2. Service Account לא תקין
3. נתיב שגוי ב-Database

**פתרון:**

```bash
# 1. בדוק Security Rules ב-Firebase Console
# Firebase Console → Realtime Database → Rules

# שנה ל (זמנית לבדיקה):
{
  "rules": {
    ".read": true,
    ".write": true
  }
}

# 2. בדוק שקובץ secret.json תקין:
cat Server/secret.json
# אמור להכיל: "project_id", "private_key", "client_email"

# 3. בדוק שה-DATABASE_URL נכון:
grep DATABASE_URL Server/firebase_init.py
# צריך להיות: https://YOUR-PROJECT.firebaseio.com
```

**✅ אחרי תיקון:**
```python
# הרץ מחדש:
python Server/Init_Park.py
# צריך להיות: ✅ Created 50 spots...
```

---

### ❌ Firebase: "Failed to initialize"

**תסמינים:**
```python
ValueError: Could not load the default credentials
```

**פתרון:**

```bash
# בדוק ש-secret.json קיים:
ls -la Server/secret.json

# אם לא קיים:
# 1. Firebase Console → Project Settings → Service Accounts
# 2. Generate new private key
# 3. שמור כ-Server/secret.json

# אם קיים אבל לא עובד:
# בדוק JSON syntax:
python3 -c "import json; json.load(open('Server/secret.json'))"
# אם יש שגיאה → הקובץ פגום, הורד מחדש
```

---

### ❌ Firebase: "Database URL not found"

**תסמינים:**
```python
firebase_admin._utils.FirebaseError: Database URL not found
```

**פתרון:**

```bash
# ודא ש-DATABASE_URL מוגדר ב-firebase_init.py:
grep -n "DATABASE_URL" Server/firebase_init.py

# צריך להיות משהו כמו:
# databaseURL="https://park-19f5b-default-rtdb.europe-west1.firebasedatabase.app"

# אם חסר - הוסף:
nano Server/firebase_init.py
# הוסף לאחר initialize_app():
# cred = credentials.Certificate("secret.json")
# firebase_admin.initialize_app(cred, {
#     'databaseURL': 'https://YOUR-PROJECT.firebaseio.com'
# })
```

---

### ❌ Firebase: "Quota Exceeded"

**תסמינים:**
```
QuotaExceededError: Exceeded quota for reads/writes
```

**גורם:** חרגת ממכסת החינם של Firebase (50k reads/day).

**פתרון:**

```bash
# 1. בדוק שימוש:
# Firebase Console → Usage and Billing

# 2. הפחת תדירות polling:
export REFRESH_INTERVAL_SECONDS=10  # במקום 3
export POLL_INTERVAL=5000  # ESP32

# 3. הפסק סימולציות ממושכות:
# Ctrl+C על simulation_sondos.py
```

---

## 📡 ESP32 Issues

### ❌ ESP32: "Connecting........____....____"

**תסמינים:**
- ESP32 לא נכנס למצב upload
- Arduino IDE תקוע על "Connecting..."

**פתרון:**

```bash
# שיטה 1: Manual Boot Mode
# 1. החזק BOOT button
# 2. לחץ RESET button (רגע)
# 3. שחרר RESET
# 4. שחרר BOOT
# 5. לחץ Upload בשנית

# שיטה 2: בדוק Port
# Tools → Port → ודא שהפורט נכון
# macOS: /dev/cu.usbserial-*
# Linux: /dev/ttyUSB0
# Windows: COM3, COM4, etc.

# שיטה 3: בדוק כבל USB
# כבלים "charging only" לא יעבדו!
# נסה כבל אחר שתומך ב-data
```

---

### ❌ ESP32: "A fatal error occurred: Failed to connect"

**תסמינים:**
```
A fatal error occurred: Failed to connect to ESP32: Timed out
```

**פתרון:**

```bash
# 1. בדוק שה-driver מותקן:
# macOS: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
# Windows: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

# 2. בדוק Upload Speed:
# Tools → Upload Speed → נסה 115200 (במקום 921600)

# 3. Reset ESP32:
# נתק USB למשך 5 שניות → חבר שוב
```

---

### ❌ ESP32: לא מתחבר ל-Wi-Fi

**תסמינים:**
```
* WiFi: trying autoConnect()
*WM: No saved credentials
*WM: Access Point: Sondos-Parking-Setup
```

**פתרון:**

```bash
# 1. חבר ל-hotspot:
# Wi-Fi → Sondos-Parking-Setup
# Password: 12345678

# 2. אם הפורטל לא נפתח אוטומטית:
# דפדפן → http://192.168.4.1

# 3. בחר רשת Wi-Fi והזן סיסמה

# 4. לחץ "Save"

# 5. Serial Monitor צריך להראות:
# ✅ WiFi connected. IP: 192.168.1.xxx
```

**אם נכשל:**
```cpp
// בדוק ב-Serial Monitor:
// *WM: WiFi connect failed
// → סיסמת Wi-Fi שגויה!

// או:
// *WM: Connection timeout
// → ESP32 רחוק מדי מה-Router, קרב אותו
```

---

### ❌ ESP32: Portal לא נפתח

**תסמינים:**
- התחברת ל-"Sondos-Parking-Setup"
- דפדפן לא פותח פורטל אוטומטית

**פתרון:**

```bash
# ידני:
# 1. פתח דפדפן
# 2. גש ל: http://192.168.4.1
# 3. אמור לראות רשימת Wi-Fi networks

# אם עדיין לא עובד:
# נסה דפדפן אחר (Chrome במקום Safari)
```

---

### ❌ ESP32: Wi-Fi מתנתק כל הזמן

**תסמינים:**
```
WiFi connected
WiFi disconnected
WiFi connected
WiFi disconnected
```

**גורמים:**
1. אות Wi-Fi חלש
2. Router עמוס
3. הפרעות (Bluetooth, Microwave)

**פתרון:**

```bash
# 1. קרב ESP32 ל-Router
# 2. החלף ל-Wi-Fi 2.4GHz (לא 5GHz!)
# 3. בדוק הפרעות:
#    - כבה Bluetooth על המחשב
#    - הרחק ממיקרוגל
#    - נסה ערוץ Wi-Fi אחר (Router settings)

# 4. הוסף reconnect logic (כבר קיים בקוד):
Firebase.reconnectWiFi(true);
```

---

### ❌ ESP32: "Anonymous sign-in failed"

**תסמינים:**
```
Auth error: FIREBASE_ERROR_TOKEN_SIGNING_FAILED
```

**פתרון:**

```bash
# 1. בדוק API_KEY נכון:
# ESP32/SpotNode/SpotNode.ino - שורה 24
#define API_KEY "YOUR_API_KEY"  # ← מ-Firebase Console

# 2. בדוק DATABASE_URL:
#define DATABASE_URL "https://YOUR-PROJECT.firebaseio.com"

# 3. אם עדיין נכשל:
# Firebase Console → Authentication → Sign-in method
# ודא ש-"Anonymous" enabled
```

---

## 🌈 LED Issues

### ❌ LED לא נדלק בכלל

**פתרון:**

```bash
# 1. בדוק חיווט:
# LED Red   → GPIO 23 → Resistor 220Ω
# LED Green → GPIO 22 → Resistor 220Ω
# LED Blue  → GPIO 21 → Resistor 220Ω
# LED GND   → GND (ישירות)

# 2. בדוק polarity (קוטביות):
# רגל ארוכה = Anode (+) או Cathode (-) תלוי בסוג
# Common Cathode: רגל ארוכה = GND
# Common Anode: רגל ארוכה = VCC

# 3. בדוק resistors:
# השתמש ב-multimeter: צריך להיות ~220Ω
# אם אין resistor → LED עלול להישרף!

# 4. נסה LED אחר (ייתכן פגום)
```

---

### ❌ LED בצבע הלא נכון

**תסמינים:**
- צריך להיות כחול (FREE) אבל אדום
- או צהוב במקום כתום

**פתרון:**

```bash
# 1. בדוק Common Anode vs Cathode:
# ESP32/SpotNode.ino - שורה 31
const bool LED_COMMON_ANODE = false;  # ← שנה ל-true אם Common Anode

# 1. בדוק חיווט RGB:
# ייתכן שהחיבורים מעורבבים!
# נסה להחליף R ↔ B

# 3. בדוק קוד setRgb():
# ESP32/SpotNode/SpotNode.ino
# "FREE" → setRgb(false, false, true);  // Blue
# אם רואה אדום → הפוך true/false
```

---

### ❌ LED מהבהב במהירות

**תסמינים:**
- LED מהבהב מהר מאוד
- קשה לראות את הצבע

**גורם:** "רפרוף" בין סטטוסים.

**פתרון:**

```bash
# הגדל STABLE_TIME:
const unsigned long STABLE_TIME = 5000;  # מ-3000 ל-5000

# ראה: calibration.md - Hysteresis
```

---

## 📏 Sensor Issues

### ❌ חיישן מחזיר -1 כל הזמן

**תסמינים:**
```
Distance: -1
Distance: -1
Distance: -1
```

**גורם:** אין תגובה מהחיישן.

**פתרון:**

```bash
# 1. בדוק חיווט:
# VCC  → 5V (לא 3.3V!)
# GND  → GND
# TRIG → GPIO 5
# ECHO → GPIO 18

# 2. בדוק קשרים רופפים (loose connections)

# 3. נסה חיישן אחר (ייתכן פגום)

# 4. נסה GPIOs אחרים:
const int TRIG_PIN = 13;  # במקום 5
const int ECHO_PIN = 12;  # במקום 18
```

---

### ❌ מרחקים לא הגיוניים (200, 300, etc.)

**תסמינים:**
```
Distance: 8
Distance: 245
Distance: 7
Distance: 312
```

**גורם:** רעש חשמלי או משטח מחזיר.

**פתרון:**

```bash
# 1. הוסף קבל 100nF בין VCC-GND של החיישן
# זה מסנן רעשים חשמליים

# 2. השתמש בכבלים קצרים (<15 ס"מ)

# 3. הוסף בדיקה בקוד:
long d = readDistanceCM();
if (d > 200) d = -1;  // התעלם מקריאות לא סבירות

# 4. הרחק ממקורות הפרעות (Bluetooth, מנועים)
```

---

### ❌ חיישן קורא תמיד אותו מספר

**תסמינים:**
```
Distance: 47
Distance: 47
Distance: 47
```

**גורם:** החיישן "קפוא" או מצביע למכשול קבוע.

**פתרון:**

```bash
# 1. נתק והפעל מחדש (power cycle):
# נתק USB → המתן 5 שניות → חבר שוב

# 2. בדוק שהחיישן לא מצביע לקיר/שולחן קבוע

# 3. נסה לזוז עם החיישן - המספר משתנה?
# לא → חיישן פגום

# 4. בדוק TRIG pin:
# האם שולח פולסים?
# pinMode(TRIG_PIN, OUTPUT);
# digitalWrite(TRIG_PIN, HIGH); delay(10);
# digitalWrite(TRIG_PIN, LOW);
```

---

## 🖥️ Dashboard Issues

### ❌ Dashboard לא נטען (404 Not Found)

**תסמינים:**
- דפדפן: "404 Not Found" או "Cannot connect"

**פתרון:**

```bash
# 1. בדוק ש-dashboard.py רץ:
ps aux | grep dashboard.py

# אם לא רץ:
cd Server
python dashboard.py

# 2. בדוק את הכתובת:
# http://localhost:8000  ✅
# http://localhost:5000  ❌ (פורט שגוי)

# 3. בדוק מחסום אש (Firewall):
# macOS: System Preferences → Security → Firewall → Allow Python

# 4. נסה IP במקום localhost:
# http://127.0.0.1:8000
```

---

### ❌ Dashboard לא מראה עדכונים

**תסמינים:**
- Dashboard נטען, אבל חניות לא משתנות צבע

**פתרון:**

```bash
# 1. רענן דפדפן:
# Ctrl+Shift+R (macOS: Cmd+Shift+R)

# 2. בדוק Console לשגיאות:
# F12 → Console
# אם רואה שגיאות JavaScript → העתק ושתף

# 3. בדוק ש-Firebase עובד:
# Tools/setup_simulation.py --test

# 4. בדוק ש-static/js/app.js קיים:
ls -la Server/static/js/app.js

# 5. נסה מצב incognito (private browsing)
```

---

### ❌ Dashboard מראה חניות אבל לא BFS/path

**תסמינים:**
- רשת החניות מוצגת
- אין קו כתום (path) לחנייה הקרובה

**פתרון:**

```bash
# 1. בדוק ש-Init_Park.py הרץ:
# צריך ליצור distanceFromEntry לכל חנייה

# 2. בדוק ב-Firebase Console:
# SondosPark/SPOTS/0,0/distanceFromEntry → צריך להיות מספר

# 3. אם חסר:
cd Server
python Init_Park.py  # הרץ מחדש

# 4. רענן Dashboard
```

---

## 🐍 Python Issues

### ❌ "ModuleNotFoundError: No module named 'firebase_admin'"

**פתרון:**

```bash
# 1. ודא שהסביבה הוירטואלית פעילה:
which python3
# צריך להראות: /path/to/venv/bin/python3

# אם לא:
source venv/bin/activate  # macOS/Linux
# או
venv\Scripts\activate  # Windows

# 2. התקן מחדש:
pip install firebase-admin==6.2.0

# 3. בדוק:
pip list | grep firebase
```

---

### ❌ Python: "SyntaxError" או "IndentationError"

**פתרון:**

```bash
# 1. בדוק גרסת Python:
python3 --version
# צריך להיות 3.9+

# 2. אם השתמשת ב-Python 2:
# החלף את כל הקריאות ל:
python3 simulation_sondos.py  # במקום python

# 3. בדוק encoding:
file Server/simulation_sondos.py
# צריך להיות: UTF-8
```

---

### ❌ "ImportError: cannot import name 'ParkingLot'"

**פתרון:**

```bash
# 1. בדוק שהקובץ קיים:
ls -la Server/data_structures.py

# 2. בדוק syntax errors:
python3 -m py_compile Server/data_structures.py

# 3. בדוק import path:
cd Server
python3 -c "from data_structures import ParkingLot"
# אם יש שגיאה → הקובץ פגום
```

---

## 🔄 Simulation Issues

### ❌ Simulation: "No free spots" מיד בהתחלה

**תסמינים:**
```
🚗 Car ABC-123 arriving...
❌ No free spots!
```

**גורם:** כל החניות כבר תפוסות ב-Firebase.

**פתרון:**

```bash
# אתחל את החניון:
cd Server
python Init_Park.py

# זה יאתחל את כל 50 החניות ל-FREE
```

---

### ❌ Simulation: רכבים לא יוצאים

**תסמינים:**
- רכבים נכנסים
- החניון מתמלא
- אף רכב לא יוצא

**פתרון:**

```bash
# בדוק משתני סביבה:
echo $DEPART_INTERVAL_SECONDS
# אם ריק או גדול מדי (>100):

export DEPART_INTERVAL_SECONDS=30
python simulation_sondos.py
```

---

## 🌐 Network Issues

### ❌ לא יכול לגשת ל-Dashboard מטאבלט

**תסמינים:**
- מהמחשב: http://localhost:8000 עובד ✅
- מהטאבלט: http://192.168.1.123:8000 לא עובד ❌

**פתרון:**

```bash
# 1. בדוק ש-HOST = '0.0.0.0':
grep "app.run" Server/dashboard.py
# צריך להיות: app.run(host='0.0.0.0', port=8000)

# 2. בדוק שהטאבלט באותה רשת Wi-Fi

# 3. בדוק מחסום אש:
# macOS:
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/bin/python3

# 4. מצא את ה-IP הנכון:
ifconfig | grep "inet "
# השתמש ב-IP הראשון (לא 127.0.0.1)
```

---

## 🔒 Security Issues

### ⚠️ "Your Firebase is publicly accessible!"

**תסמינים:**
- הודעה ב-Firebase Console על Security Rules פתוחות

**פתרון:**

```bash
# Firebase Console → Realtime Database → Rules
# שנה מ:
{
  "rules": {
    ".read": true,
    ".write": true
  }
}

# ל:
{
  "rules": {
    "SondosPark": {
      ".read": "auth != null",
      ".write": "auth != null"
    }
  }
}

# ⚠️ זה ידרוש authentication מה-ESP32/Python
```

---

## 📊 Performance Issues

### 🐌 Dashboard איטי / lag

**פתרון:**

```bash
# 1. הפחת תדירות עדכונים:
# static/js/app.js - שנה:
setInterval(updateStatus, 2000);  # מ-1000 ל-2000

# 2. הפחת polling בסימולציה:
export REFRESH_INTERVAL_SECONDS=5  # במקום 3

# 3. סגור טאבים/חלונות מיותרים
```

---

## 🧰 Debugging Tools

### Serial Monitor להודעות ESP32

```bash
# Arduino IDE → Tools → Serial Monitor
# Baud: 115200

# פלט טיפוסי:
Distance: 25
[STREAM] status -> FREE
Distance: 8
[Publish] status -> OCCUPIED
```

---

### Firebase Console - Real-time Data

```bash
# פתח:
# Firebase Console → Realtime Database → Data

# תראה:
SondosPark
  ├─ SPOTS
  │   ├─ 0,0
  │   │   ├─ status: "FREE"
  │   │   ├─ distanceFromEntry: 3
  │   │   └─ ...
  │   └─ ...
  └─ CARS
      └─ ...

# רענן (F5) כדי לראות שינויים חיים
```

---

### Python Print Debug

```python
# Server/simulation_sondos.py - הוסף:
print(f"[DEBUG] ParkingLot state: {pl.spot_lookup}")
print(f"[DEBUG] Free spots: {pl.free_spots}")
```

---

## 📞 Getting Help

### כאשר כלום לא עובד:

1. **אסוף מידע:**
   ```bash
   # גרסת Python:
   python3 --version
   
   # ספריות מותקנות:
   pip list
   
   # Serial Monitor output (5 שורות אחרונות)
   
   # Firebase Console screenshot
   
   # Console errors (F12) מה-Dashboard
   ```

2. **בדוק רשימות:**
   - [ ] Firebase RTDB פעיל?
   - [ ] secret.json קיים ותקין?
   - [ ] ESP32 מחובר ל-Wi-Fi?
   - [ ] LED נדלק?
   - [ ] Serial Monitor מראה "Distance"?
   - [ ] Dashboard נטען?

3. **חזור על Setup:**
   - [setup_guide.md](setup_guide.md) - עבור שלב-אחר-שלב

4. **פנה לעזרה:**
   - GitHub Issues
   - sondos@campus.technion.ac.il

---

## 📝 Common Error Messages

### Error: "ECONNREFUSED"
**משמעות:** השרת לא רץ  
**פתרון:** `python dashboard.py`

### Error: "CERT_HAS_EXPIRED"
**משמעות:** Certificate של Firebase פג תוקף  
**פתרון:** הורד `secret.json` מחדש

### Error: "GPIO busy"
**משמעות:** GPIO כבר בשימוש  
**פתרון:** Reset ESP32 (RESET button)

### Error: "Out of memory"
**משמעות:** ESP32 אזל זיכרון  
**פתרון:** הפחת `STABLE_TIME` או הקטן buffers

---

**לפרטים נוספים על שגיאות:** [error_messages.md](error_messages.md)
