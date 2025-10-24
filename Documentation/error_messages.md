# 📢 Error Messages - הסבר על הודעות שגיאה

מדריך מקיף להבנת הודעות השגיאה במערכת החניה החכמה.

---

## 🔥 Firebase Errors

### `FirebaseError: Permission denied`

**הודעה מלאה:**
```
firebase_admin.exceptions.PermissionDeniedError: Permission denied
```

**מה זה אומר:**
- אין הרשאות לקרוא/לכתוב ל-Firebase Realtime Database
- Security Rules חוסמים את הגישה

**למה זה קורה:**
1. Security Rules מוגדרים ל-production (דורשים authentication)
2. Service Account לא תקין
3. נתיב Database שגוי

**פתרון:**
```bash
# Firebase Console → Realtime Database → Rules
# שנה ל-test mode (זמנית):
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```

**ראה גם:** [troubleshooting.md - Firebase Issues](troubleshooting.md#firebase-issues)

---

### `ValueError: Could not load the default credentials`

**הודעה מלאה:**
```python
ValueError: Could not load the default credentials. Check the environment variable GOOGLE_APPLICATION_CREDENTIALS or explicitly create credentials and re-run.
```

**מה זה אומר:**
- קובץ `secret.json` לא נמצא או לא תקין
- Firebase Admin SDK לא יכול לאתחל

**למה זה קורה:**
1. `secret.json` לא קיים ב-`Server/`
2. הנתיב לקובץ שגוי
3. הקובץ פגום (JSON לא תקין)

**פתרון:**
```bash
# 1. בדוק שהקובץ קיים:
ls -la Server/secret.json

# 2. בדוק JSON syntax:
python3 -c "import json; json.load(open('Server/secret.json'))"

# 3. אם פגום - הורד מחדש:
# Firebase Console → Project Settings → Service Accounts
# → Generate new private key
```

---

### `FirebaseError: Invalid Firebase app name`

**הודעה מלאה:**
```
ValueError: The default Firebase app already exists
```

**מה זה אומר:**
- ניסית לאתחל את Firebase פעמיים

**למה זה קורה:**
- הרצת `firebase_init.py` פעמיים באותה session
- import מרובה של `firebase_init`

**פתרון:**
```python
# השתמש ב-try/except:
try:
    firebase_admin.initialize_app(cred, {'databaseURL': DATABASE_URL})
except ValueError:
    pass  # App already initialized
```

---

### `requests.exceptions.HTTPError: 401 Client Error: Unauthorized`

**הודעה מלאה:**
```
requests.exceptions.HTTPError: 401 Client Error: Unauthorized for url
```

**מה זה אומר:**
- API Key שגוי או DATABASE_URL לא נכון

**למה זה קורה:**
1. `API_KEY` ב-ESP32 לא תואם לפרויקט Firebase
2. `DATABASE_URL` מצביע לפרויקט אחר

**פתרון:**
```cpp
// ESP32/SpotNode/SpotNode.ino - בדוק שורות 24-25:
#define API_KEY "YOUR_API_KEY"  // ← מ-Firebase Console
#define DATABASE_URL "https://YOUR-PROJECT.firebaseio.com"
```

---

### `FirebaseError: Quota exceeded`

**הודעה מלאה:**
```
firebase_admin._utils.FirebaseError: Quota exceeded for service 'firebasedatabase.googleapis.com'
```

**מה זה אומר:**
- חרגת ממכסת החינם של Firebase (50,000 reads/day)

**למה זה קורה:**
- סימולציה רצה זמן רב עם polling תכוף
- הרבה ESP32 nodes עם `POLL_INTERVAL` נמוך

**פתרון:**
```bash
# הפחת תדירות:
export REFRESH_INTERVAL_SECONDS=10  # במקום 3

# ESP32:
const unsigned long POLL_INTERVAL = 5000;  // במקום 3000

# או שדרג ל-Blaze Plan (pay-as-you-go)
```

---

## 📡 ESP32 Errors

### `A fatal error occurred: Failed to connect to ESP32`

**הודעה מלאה:**
```
A fatal error occurred: Failed to connect to ESP32: Timed out waiting for packet header
```

**מה זה אומר:**
- Arduino IDE לא יכול לתקשר עם ESP32

**למה זה קורה:**
1. ESP32 לא במצב boot
2. Port שגוי
3. כבל USB לא תומך ב-data
4. Driver לא מותקן

**פתרון:**
```bash
# 1. Manual boot:
# החזק BOOT → לחץ RESET → שחרר RESET → שחרר BOOT

# 2. בדוק Port:
# Tools → Port → בחר /dev/cu.usbserial-* (macOS)

# 3. התקן driver:
# https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
```

---

### `Brownout detector was triggered`

**הודעה מלאה:**
```
Brownout detector was triggered
ets Jun  8 2016 00:22:57
```

**מה זה אומר:**
- מתח החשמל ירד מתחת ל-3.3V
- ESP32 עשה reset אוטומטי

**למה זה קורה:**
1. הזנת USB חלשה
2. כבל USB רע
3. פורט USB חלש
4. צריכת זרם גבוהה (Wi-Fi + חיישן)

**פתרון:**
```bash
# 1. נסה פורט USB אחר (USB 3.0 עדיף)
# 2. השתמש בכבל קצר (<50 ס"מ)
# 3. נסה hub USB מוזן (powered hub)
# 4. השתמש ב-power supply 5V 2A חיצוני
```

---

### `Guru Meditation Error: Core 1 panic'ed`

**הודעה מלאה:**
```
Guru Meditation Error: Core  1 panic'ed (LoadProhibited). Exception was unhandled.
```

**מה זה אומר:**
- ESP32 קרס (crash) בגלל גישה לזיכרון לא חוקי

**למה זה קורה:**
1. Stack overflow (משתנים גדולים מדי)
2. Pointer לא מאותחל
3. String corruption

**פתרון:**
```cpp
// 1. הקטן משתנים גלובליים:
// במקום:
char buffer[10000];  // ❌ גדול מדי!

// השתמש ב:
char buffer[256];    // ✅

// 2. בדוק pointers:
String* myStr = nullptr;
if (myStr != nullptr) {  // ✅ בדיקה
    myStr->c_str();
}

// 3. הגדל Stack Size (platformio.ini):
board_build.arduino.memory_type = qio_qspi
```

---

### `WiFiManager: AP IP address: 0.0.0.0`

**הודעה מלאה:**
```
*WM: AP IP address: 0.0.0.0
```

**מה זה אומר:**
- WiFiManager לא הצליח ליצור Access Point

**למה זה קורה:**
- Wi-Fi module לא מופעל
- חומרה פגומה

**פתרון:**
```cpp
// הוסף reset ל-Wi-Fi:
WiFi.disconnect(true);
WiFi.mode(WIFI_OFF);
delay(1000);
WiFi.mode(WIFI_STA);

// אז:
wm.autoConnect("Sondos-Parking-Setup");
```

---

### `Failed to configure Firebase`

**הודעה מלאה (Serial Monitor):**
```
[Firebase] Failed to configure Firebase
Auth error: FIREBASE_ERROR_TOKEN_SIGNING_FAILED
```

**מה זה אומר:**
- ESP32 לא הצליח להתחבר ל-Firebase

**למה זה קורה:**
1. `API_KEY` שגוי
2. `DATABASE_URL` שגוי
3. Wi-Fi מנותק
4. Firewall חוסם

**פתרון:**
```cpp
// בדוק credentials:
#define API_KEY "AIzaSyB..."  // ← מ-Firebase Console
#define DATABASE_URL "https://park-xxxx.firebaseio.com"

// וודא Wi-Fi מחובר:
if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi OK");
}
```

---

## 🐍 Python Errors

### `ModuleNotFoundError: No module named 'firebase_admin'`

**הודעה מלאה:**
```python
ModuleNotFoundError: No module named 'firebase_admin'
```

**מה זה אומר:**
- ספריית `firebase-admin` לא מותקנת

**למה זה קורה:**
1. לא הרצת `pip install -r requirements.txt`
2. סביבה וירטואלית לא פעילה
3. התקנה נכשלה

**פתרון:**
```bash
# 1. הפעל venv:
source venv/bin/activate  # macOS/Linux

# 2. התקן:
pip install firebase-admin==6.2.0

# 3. בדוק:
pip list | grep firebase
# צריך להראות: firebase-admin 6.2.0
```

---

### `ImportError: cannot import name 'ParkingLot'`

**הודעה מלאה:**
```python
ImportError: cannot import name 'ParkingLot' from 'data_structures'
```

**מה זה אומר:**
- הקובץ `data_structures.py` פגום או לא קיים

**למה זה קורה:**
1. Syntax error ב-`data_structures.py`
2. הקובץ נמחק
3. שם מחלקה שגוי

**פתרון:**
```bash
# 1. בדוק שהקובץ קיים:
ls -la Server/data_structures.py

# 2. בדוק syntax:
python3 -m py_compile Server/data_structures.py

# 3. נסה import:
cd Server
python3 -c "from data_structures import ParkingLot"
```

---

### `KeyError: 'status'`

**הודעה מלאה:**
```python
KeyError: 'status'
Traceback (most recent call last):
  File "simulation_sondos.py", line 123
    spot_status = spot_data['status']
```

**מה זה אומר:**
- חנייה ב-Firebase חסר שדה `status`

**למה זה קורה:**
- `Init_Park.py` לא הורץ
- נתונים ב-Firebase פגומים

**פתרון:**
```bash
# הרץ אתחול מחדש:
cd Server
python Init_Park.py

# זה יצור את כל השדות הנדרשים
```

---

### `json.decoder.JSONDecodeError`

**הודעה מלאה:**
```python
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**מה זה אומר:**
- קובץ JSON לא תקין

**למה זה קורה:**
1. `secret.json` פגום
2. קומה/תו לא חוקי
3. קובץ ריק

**פתרון:**
```bash
# בדוק את הקובץ:
cat Server/secret.json
# צריך להתחיל ב: {
# ולהסתיים ב: }

# אם פגום - הורד מחדש מ-Firebase Console
```

---

## 🌐 Network Errors

### `requests.exceptions.ConnectionError`

**הודעה מלאה:**
```python
requests.exceptions.ConnectionError: HTTPSConnectionPool(host='firebase.com', port=443)
```

**מה זה אומר:**
- אין חיבור לאינטרנט או Firebase לא זמין

**למה זה קורה:**
1. אין חיבור לאינטרנט
2. Firewall חוסם
3. Firebase down (נדיר)

**פתרון:**
```bash
# 1. בדוק אינטרנט:
ping google.com

# 2. בדוק Firebase:
ping firebase.google.com

# 3. בדוק proxy/firewall
```

---

### `OSError: [Errno 48] Address already in use`

**הודעה מלאה:**
```python
OSError: [Errno 48] Address already in use
```

**מה זה אומר:**
- הפורט 8000 כבר בשימוש

**למה זה קורה:**
- `dashboard.py` כבר רץ
- תהליך אחר תופס את הפורט

**פתרון:**
```bash
# 1. מצא את התהליך:
lsof -i :8000
# או
netstat -an | grep 8000

# 2. עצור אותו:
kill -9 <PID>

# 3. או שנה פורט:
# dashboard.py:
app.run(host='0.0.0.0', port=5000)  # במקום 8000
```

---

## 🖥️ Dashboard Errors (Browser Console)

### `Failed to load resource: net::ERR_CONNECTION_REFUSED`

**הודעה ב-Console (F12):**
```
Failed to load resource: net::ERR_CONNECTION_REFUSED
http://localhost:8000/api/status
```

**מה זה אומר:**
- `dashboard.py` לא רץ

**פתרון:**
```bash
cd Server
python dashboard.py
```

---

### `Uncaught TypeError: Cannot read property 'status' of undefined`

**הודעה ב-Console:**
```javascript
Uncaught TypeError: Cannot read property 'status' of undefined
```

**מה זה אומר:**
- JavaScript מנסה לגשת לנתונים שלא קיימים

**למה זה קורה:**
- Firebase מחזיר `null` או אובייקט ריק

**פתרון:**
```javascript
// static/js/app.js - הוסף בדיקה:
if (spot && spot.status) {
    updateSpotColor(spot.status);
}
```

---

### `CORS policy: No 'Access-Control-Allow-Origin' header`

**הודעה מלאה:**
```
Access to fetch at 'http://localhost:8000/api/status' from origin 'http://192.168.1.100:8000' has been blocked by CORS policy
```

**מה זה אומר:**
- בעיית CORS (Cross-Origin Resource Sharing)

**למה זה קורה:**
- גישה מ-IP שונה ל-localhost

**פתרון:**
```python
# Server/dashboard.py - הוסף:
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # ← הוסף שורה זו

# התקן flask-cors:
pip install flask-cors
```

---

## 📏 Sensor Errors (Serial Monitor)

### `Distance: -1`

**הודעה ב-Serial Monitor:**
```
Distance: -1
Distance: -1
Distance: -1
```

**מה זה אומר:**
- החיישן לא מחזיר תגובה

**למה זה קורה:**
1. חיווט שגוי (TRIG/ECHO)
2. חיישן פגום
3. VCC לא מחובר ל-5V
4. Timeout קצר מדי

**פתרון:**
```cpp
// בדוק חיווט:
// TRIG → GPIO 5
// ECHO → GPIO 18
// VCC  → 5V (לא 3.3V!)

// הגדל timeout:
long duration = pulseIn(ECHO_PIN, HIGH, 50000);  // מ-30000 ל-50000
```

---

### `Distance: 0`

**הודעה ב-Serial Monitor:**
```
Distance: 0
Distance: 0
```

**מה זה אומר:**
- החיישן מחזיר 0 (משהו צמוד אליו)

**למה זה קורה:**
- אובייקט צמוד לחיישן (<2 ס"מ)
- החיישן מכוון למטה (לשולחן/רצפה)

**פתרון:**
```bash
# הרם את החיישן או הטה אותו מעלה
```

---

## 🔋 Power Errors

### `rst:0x10 (RTCWDT_RTC_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)`

**הודעה מלאה:**
```
rst:0x10 (RTCWDT_RTC_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
```

**מה זה אומר:**
- Watchdog Timer reset (ESP32 קרס ואתחל)

**למה זה קורה:**
1. Loop() תקוע (infinite loop)
2. עומס CPU גבוה
3. brownout (מתח נמוך)

**פתרון:**
```cpp
// הוסף yield() או delay():
void loop() {
    // ... קוד ...
    yield();  // תן זמן ל-watchdog
    delay(10);
}

// או השבת watchdog (לא מומלץ):
#include "esp_task_wdt.h"
esp_task_wdt_init(30, false);  // 30 שניות, לא reset
```

---

## 📝 Common Warning Messages

### ⚠️ `*WM: No saved credentials`

**משמעות:** ESP32 לא שמר Wi-Fi credentials  
**פעולה:** רגיל - Portal ייפתח אוטומטית

---

### ⚠️ `[STREAM] timeout, trying to resume...`

**משמעות:** Firebase Stream timeout  
**פעולה:** רגיל - ינסה reconnect אוטומטית

---

### ⚠️ `WARNING:root:Token refresh failed`

**משמעות:** Firebase token לא רענן  
**פעולה:** בדרך כלל לא בעיה - ינסה שוב

---

## 🆘 Critical Errors (דורש פעולה מיידית)

### 🔴 `FIREBASE_ERROR_INVALID_CREDENTIAL`

**פעולה:** הורד `secret.json` מחדש מ-Firebase Console

---

### 🔴 `ESP32 stuck in boot loop`

**פעולה:**  
1. Upload blank sketch (File → Examples → Basics → BareMinimum)
2. אז upload את הקוד המלא

---

### 🔴 `Database deleted / Permission denied permanently`

**פעולה:**  
1. הרץ `python Init_Park.py`
2. שנה Security Rules ב-Firebase Console

---

## 📞 כשכלום לא עוזר

אם ראית שגיאה שלא מופיעה כאן:

1. **העתק את ההודעה המלאה** (כולל Stack Trace)
2. **צלם Serial Monitor** (אם ESP32)
3. **צלם Browser Console** (F12 אם Dashboard)
4. **פתח issue ב-GitHub** או שלח ל:
   - sondos@campus.technion.ac.il

---

**ראה גם:**
- [troubleshooting.md](troubleshooting.md) - פתרון בעיות מפורט
- [setup_guide.md](setup_guide.md) - מדריך התקנה
- [calibration.md](calibration.md) - כיול חיישנים
