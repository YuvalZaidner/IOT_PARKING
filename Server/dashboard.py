from flask import Flask, jsonify, render_template
import firebase_init  # ensures firebase_admin is initialized
from firebase_admin import db
from data_structures import ParkingLot, Spot
import time

# Note: the repository contains a `template/` directory (singular). Keep the
# value in sync so Jinja can find `index.html`.
app = Flask(__name__, static_folder='static', template_folder='template')
ROOT = '/SondosPark/SPOTS'


def build_parkinglot_from_db(snapshot):
    pl = ParkingLot()
    for sid, s in (snapshot or {}).items():
        if not isinstance(s, dict):
            continue
        try:
            row_str, col_str = sid.replace('(', '').replace(')', '').split(',')
            row, col = int(row_str), int(col_str)
        except Exception:
            # if malformed key, skip
            continue
        dist = s.get('distanceFromEntry', 0) or 0
        spot = Spot(row, col, dist)
        spot.status = s.get('status', 'FREE')
        spot.waiting_car_id = s.get('waitingCarId', '-')
        spot.seen_car_id = s.get('seenCarId', '-')
        # use plain id format 'row,col'
        spot.spot_id = f"{row},{col}"
        pl.spot_lookup[spot.spot_id] = spot
        if spot.status == 'FREE':
            pl.free_spots.add(spot)
    return pl


@app.route('/')
def index():
    # pass a timestamp to template so static assets can be cache-busted
    import time
    return render_template('index.html', ts=int(time.time()))


@app.route('/api/status')
def api_status():
    ref = db.reference(ROOT)
    data = ref.get() or {}

    # compute closest free using ParkingLot BFS
    pl = build_parkinglot_from_db(data)
    # gate configuration - default gate coordinates (row=0, col=2)
    import os
    gate_row = int(os.environ.get('GATE_ROW', '0'))
    gate_col = int(os.environ.get('GATE_COL', '2'))
    closest = pl.find_closest(gate_row, gate_col)
    closest_str = f"{closest[0]},{closest[1]}" if closest else None

    # Determine waiting car at the gate (if any)
    # gate position may be present in pl.spot_lookup as 'row,col'
    gate_key = f"{gate_row},{gate_col}"
    gate_spot = pl.get_spot(gate_key)
    waiting_car = None
    if gate_spot:
        waiting_car = getattr(gate_spot, 'waiting_car_id', None)

    # If no car is waiting exactly at the gate, fall back to any WAITING spot
    # and prefer the one nearest the gate (Manhattan distance). This ensures
    # the arriving box shows the car assigned even if it's not placed exactly
    # on the gate cell.
    if not waiting_car or waiting_car == '-':
        best = None
        best_dist = None
        for sid, s in (data or {}).items():
            if not isinstance(s, dict):
                continue
            if s.get('status') == 'WAITING':
                try:
                    rstr, cstr = sid.replace('(', '').replace(')', '').split(',')
                    r, c = int(rstr), int(cstr)
                except Exception:
                    continue
                dist = abs(r - gate_row) + abs(c - gate_col)
                if best is None or dist < best_dist:
                    best = s.get('waitingCarId')
                    best_dist = dist
        if best:
            waiting_car = best

    # normalize keys for the client: strip parentheses so keys are 'row,col'
    normalized = {}
    for sid, s in (data or {}).items():
        if not isinstance(s, dict):
            continue
        # strip parentheses and whitespace
        key = sid.replace('(', '').replace(')', '').strip()
        normalized[key] = s

    # compute free count for UI
    free_count = sum(1 for s in normalized.values() if isinstance(s, dict) and (s.get('status') or '').upper() == 'FREE')
    is_full = free_count == 0

    # include timestamp
    now = int(time.time() * 1000)
    return jsonify({
        'spots': normalized,
        'closest_free': closest_str,
        'ts': now,
        'gate': {'row': gate_row, 'col': gate_col},
        'gate_waiting_car': waiting_car or '-',
        'free_count': free_count,
        'is_full': is_full,
    })


if __name__ == '__main__':
    # Listen on all interfaces so tablet can connect; use port 8000
    app.run(host='0.0.0.0', port=8000, debug=False)
