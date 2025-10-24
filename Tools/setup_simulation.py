import threading
import time
from firebase_admin import db
from firebase_init import db as _db_init
from constants import ROOT_BRANCH, STAT_WAIT, STAT_OCC
import argparse
import sys

BASE = db.reference(ROOT_BRANCH)
SPOTS = BASE.child("SPOTS")
CARS = BASE.child("CARS")

def _on_spots(event):
    print("[SPOTS EVENT]", event.event_type, event.path, "->", str(event.data)[:120])

def _on_cars(event):
    print("[CARS EVENT]", event.event_type, event.path, "->", str(event.data)[:120])

def start_listener(block_forever=True):
    s_stream = SPOTS.listen(_on_spots)
    c_stream = CARS.listen(_on_cars)

    print("[Listener] Attached to:")
    print(f"  /{ROOT_BRANCH}/SPOTS")
    print(f"  /{ROOT_BRANCH}/CARS")

    try:
        if block_forever:
            threading.Event().wait()
    finally:
        s_stream.close()
        c_stream.close()

def check_firebase_connection(timeout=5):
    """Attempt a single read of the ROOT_BRANCH with a timeout.
    Returns (True, data) on success or (False, error_message) on failure/timeout.
    """
    evt = threading.Event()
    result = {"ok": False, "data": None, "error": None}

    def target():
        try:
            data = BASE.get()
            result["ok"] = True
            result["data"] = data
        except Exception as e:
            result["error"] = str(e)
        finally:
            evt.set()

    t = threading.Thread(target=target, daemon=True)
    t.start()
    if not evt.wait(timeout):
        return False, f"Timeout after {timeout}s while reading /{ROOT_BRANCH}"
    if result["ok"]:
        return True, result["data"]
    return False, result["error"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup simulation listener / connectivity check")
    parser.add_argument("--test", action="store_true", help="Only run connectivity test and exit")
    parser.add_argument("--listen", action="store_true", help="Start the listener (will block)")
    args = parser.parse_args()

    ok, info = check_firebase_connection(timeout=5)
    if not ok:
        print("[Firebase Test] FAILED:", info)
        # If user only wanted to test, exit with non-zero
        if args.test or not args.listen:
            sys.exit(1)
        # otherwise proceed to try attaching listener (may still fail)
        print("[Firebase Test] Proceeding to attach listener despite test failure...")
    else:
        print("[Firebase Test] OK - root data preview:", str(info)[:200])

    if args.test and not args.listen:
        # test only requested
        sys.exit(0)

    # default behavior: start listener (after test)
    start_listener(block_forever=True)
