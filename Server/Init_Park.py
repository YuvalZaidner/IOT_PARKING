import time
from firebase_admin import db
from firebase_init import db as _db_init  # ensures app is initialized
from constants import ROOT_BRANCH, STAT_FREE


# Parking-lot size (adjust as needed)
ROWS = 10
COLS = 5

# configurable entry location (row, col) used to compute distanceFromEntry
ENTRY_ROW = 3
ENTRY_COL = 0


def _spot_id(r, c):
    # use canonical key format 'row,col' to match other modules
    return f"{r},{c}"


def distance_from_entry(r, c):
    """Manhattan distance from the configured entry point."""
    return abs(r - ENTRY_ROW) + abs(c - ENTRY_COL)


def main():
    base = db.reference(ROOT_BRANCH)
    spots_ref = base.child("SPOTS")

    # create metadata
    meta = {
        "_meta": {
            "rows": ROWS,
            "cols": COLS,
            "lastInit": int(time.time()),
        },
       
    }
    base.update(meta)

    payload = {}
    now_ms = int(time.time() * 1000)
    for r in range(ROWS):
        for c in range(COLS):
            sid = _spot_id(r, c)
            payload[sid] = {
                "row": r,
                "col": c,
                "status": STAT_FREE,
                "distanceFromEntry": distance_from_entry(r, c),
                "lastUpdateMs": now_ms,
                "seenCarId": "-",      # initialized as null
                "waitingCarId": "-",   # initialized as null
            }

    spots_ref.set(payload)
    print(f"[WRITE] Initialized {ROWS*COLS} spots under /{ROOT_BRANCH}/SPOTS (keys as 'row,col')")

    # sanity read
    data = spots_ref.get() or {}
    print(f"[READ] Spots in DB: {len(data)}")



if __name__ == "__main__":
    main()