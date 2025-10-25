# Smart Parking – First-Time Run & Dashboard Guide

This quick guide shows how to:

1. **Prepare the project** on a fresh machine
2. **Run the web dashboard** (default: port `8000`)
3. **Run the parking simulator** (`simulation_sondos.py`)
4. **Troubleshoot** common issues

> Tested on macOS/Linux shells. (Windows equivalents are included where helpful.)

---

## 0) Prerequisites

* **Python 3.10+**
* **pip** (latest)
* **Firebase Admin** access:

  * A **service account JSON** with Database Admin permissions
  * Your Firebase **Realtime Database URL** (e.g. `https://<project-id>.firebaseio.com/`)
* Network access to Firebase RTDB

> The repository should include a `firebase_init.py` that loads the service account and initializes the Admin SDK. Ensure it points to your JSON and Database URL.

---

## 1) One-Time Setup

From the repository root:

```bash
# 1) Create and activate a local virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2) Install dependencies
pip install --upgrade pip
pip install -r requirements.txt            # Root-level helpers (linting, docs, etc.)
pip install -r Server/requirements.txt     # Core server + dashboard stack (Flask, firebase-admin, etc.)
pip install -r requirements.txt  # Make sure requirements.txt exists and includes firebase-admin, flask/fastapi (dashboard), etc.

# 3) Configure Firebase (example)
# Option A: via environment variables (example)
export GOOGLE_APPLICATION_CREDENTIALS="/absolute/path/to/serviceAccount.json"
# Option B: inside firebase_init.py point to the JSON and databaseURL
```

**Project files to verify**

* `firebase_init.py` initializes Firebase Admin (`firebase_admin.initialize_app(...)`).
* `constants.py` defines `ROOT_BRANCH` (e.g., `ROOT_BRANCH = "SONDOS_LOTS"`).

* `dashboard.py` is the web UI entry point (listens on `localhost:8000` by default).
* `Server/simulation_sondos.py` (or your actual path) is the simulator entry point.

---

## 2) Environment Knobs (optional but useful)

The simulator reads timing from environment variables (all optional):

| Variable                   | Meaning                                           | Default |
| -------------------------- | ------------------------------------------------- | ------- |
| `KEEP_CHANGES`             | If `1`, **don’t** restore DB at the end/interrupt | `0`     |
| `WAIT_SECONDS`             | Short sleeps between state flips                  | `1`     |
| `N_ARRIVALS`               | If `0`, run **forever**; else run N cars          | `0`     |
| `ARRIVAL_INTERVAL_SECONDS` | Time between **arrivals**                         | `5`     |
| `DEPART_INTERVAL_SECONDS`  | Periodic auto-departure cadence                   | `30`    |
| `DEPART_WHEN_FULL_SECONDS` | When full, how often to force departures          | `10`    |
| `WRONG_PARK_SECONDS`       | Inject a wrong-park every X seconds               | `45`    |
| `REFRESH_INTERVAL_SECONDS` | DB→memory resync interval                         | `3`     |

Example:

```bash
export KEEP_CHANGES=0
export ARRIVAL_INTERVAL_SECONDS=7
export WRONG_PARK_SECONDS=60
```

---

## 3) Start the Dashboard (port 8000)

Before starting, check if port **8000** is free:

```bash
lsof -iTCP:8000 -sTCP:LISTEN -n -P || true
ps aux | grep -E "dashboard.py|python" | grep -v grep | head -n 60
```

Run the dashboard using the project’s **virtualenv** Python:

```bash
./.venv/bin/python dashboard.py
```

> If your dashboard lives elsewhere or uses another framework (Flask/FastAPI), adjust the command accordingly (e.g., `uvicorn app:app --port 8000 --reload`).

**Stopping**: hit `Ctrl+C` in the terminal that runs the dashboard.

---

## 4) Run the Simulator

You can run with the system Python **or** your venv Python. Prefer the venv for consistent deps.

**Option A – venv Python (recommended):**

```bash
./.venv/bin/python Server/simulation_sondos.py
```

**Option B – absolute system Python path (as you shared):**

```bash
/usr/local/bin/python3 \
  "/Users/sondostaha/Desktop/IOT F/Server/simulation_sondos.py"
```

> On start, the simulator **clears cars** and sets **all spots to FREE**, then runs either **continuous** or **finite** arrivals depending on `N_ARRIVALS`.

**Examples**

```bash
# Run forever, arrivals every 5s (default), don’t keep changes after stop
export KEEP_CHANGES=0; export N_ARRIVALS=0
./.venv/bin/python Server/simulation_sondos.py

# Run exactly 10 cars, 7s between arrivals, keep DB state afterwards
export N_ARRIVALS=10; export ARRIVAL_INTERVAL_SECONDS=7; export KEEP_CHANGES=1
./.venv/bin/python Server/simulation_sondos.py
```

**Stopping**: hit `Ctrl+C`. If `KEEP_CHANGES=0`, the script restores the `SPOTS` backup and removes created `CARS`.

---

## 5) Typical Workflow

1. **Activate venv**: `source .venv/bin/activate`
2. **Start dashboard** (leave it running in its own terminal):

   ```bash
   ./.venv/bin/python dashboard.py
   ```
3. **Run simulator** in another terminal:

   ```bash
   ./.venv/bin/python Server/simulation_sondos.py
   ```
4. Watch the dashboard: spots flip **FREE → WAITING → OCCUPIED**, occasional **WRONG_PARK** (purple), and **departures**.

---

## 6) Troubleshooting

**Port 8000 already in use**

```bash
lsof -iTCP:8000 -sTCP:LISTEN -n -P
# Note PID, then kill it:
kill -9 <PID>
```

**Firebase auth / key errors**

* Ensure `firebase_init.py` loads the correct service account and `databaseURL`.
* Check `GOOGLE_APPLICATION_CREDENTIALS` path points to a valid JSON.
* Verify the service account has RTDB Admin permissions.

**Module not found / imports fail**

* Activate venv and reinstall deps: `source .venv/bin/activate && pip install -r requirements.txt`
* Confirm your working directory is the repo root (relative imports match).

**UI not updating**

* The simulator writes to `/{ROOT_BRANCH}/SPOTS` and `/{ROOT_BRANCH}/CARS`.
* Confirm the dashboard is reading the same `ROOT_BRANCH`.
* Network latency: the simulator includes short sleeps to allow RTDB listeners to catch up.

**Reset everything**

* Run the simulator once; it calls `clear_cars_and_reset_spots()` at startup.
* Or implement a quick admin script that calls `clear_cars_and_reset_spots()` directly.

---

## 7) Notes for Windows Users

* Activate venv: `.venv\Scripts\activate`
* Replace `./.venv/bin/python` with `.venv\Scripts\python.exe`
* Replace `lsof` with: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`

---

## 8) File Paths Recap (as shared)

```bash
# Check & list potential port conflicts (safe to run)
lsof -iTCP:8000 -sTCP:LISTEN -n -P || true; \
ps aux | grep -E "dashboard.py|python" | grep -v grep | head -n 60

# Run dashboard from venv
./.venv/bin/python dashboard.py

# Run simulator (absolute path example)
/usr/local/bin/python3 \
  "/Users/sondostaha/Desktop/IOT F/Server/simulation_sondos.py"
```

---

## 9) Success Checklist

* Dashboard reachable at **[http://localhost:8000/](http://localhost:8000/)**
* RTDB shows updates under `/{ROOT_BRANCH}/SPOTS` and `/{ROOT_BRANCH}/CARS`
* Spots change color: **FREE → WAITING → OCCUPIED**, occasional **WRONG_PARK** (purple)
* Departures free spots over time

You’re all set! 🚦 If you want, we can tailor a Makefile or `justfile` to simplify all commands into `just up`, `just sim`, `just reset`.
