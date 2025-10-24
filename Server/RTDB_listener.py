import threading
import time
from firebase_admin import db
from firebase_init import db as _db_init  # ensures firebase is initialized
from constants import ROOT_BRANCH, STAT_WAIT, STAT_OCC

BASE = db.reference(ROOT_BRANCH)
SPOTS = BASE.child("SPOTS")
CARS = BASE.child("CARS")


def _on_spots(event):
    # event: {event_type, path, data}
    try:
        print(f"[SPOTS EVENT] {event.event_type} {event.path} -> {str(event.data)[:120]}")
    except Exception:
        print("[SPOTS EVENT] (print failed)")

    # Example: auto-confirm WAITING -> OCCUPIED when 'arrivalConfirmed' flag appears
    # (You can delete this if your flow is different.)
    try:
        if isinstance(event.data, dict) and event.data.get("arrivalConfirmed"):
            # path like '/(r,c)'
            spot_id = event.path.strip("/")
            if spot_id:
                SPOTS.child(spot_id).update({
                    "status": STAT_OCC,
                    "arrivalConfirmed": None,
                    "lastUpdate": int(time.time()),
                })
                print(f"[AUTO] {spot_id}: WAITING→OCCUPIED by listener")
    except Exception as e:
        print("[SPOTS HANDLER ERROR]", e)


def _on_cars(event):
    try:
        print(f"[CARS EVENT] {event.event_type} {event.path} -> {str(event.data)[:120]}")
    except Exception:
        print("[CARS EVENT] (print failed)")


def start_listener(block_forever: bool = True):
    s_stream = SPOTS.listen(_on_spots)
    c_stream = CARS.listen(_on_cars)

    print("[Listener] Attached to:")
    print(f" /{ROOT_BRANCH}/SPOTS")
    print(f" /{ROOT_BRANCH}/CARS")

    try:
        if block_forever:
            threading.Event().wait()
    finally:
        try:
            s_stream.close()
        except Exception:
            pass
        try:
            c_stream.close()
        except Exception:
            pass


if __name__ == "__main__":
    start_listener()
