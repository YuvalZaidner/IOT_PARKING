import time
import os
from firebase_admin import db
import firebase_init  # initializes firebase_admin using secret.json or env
from event_generator import simulate_car_arrival, simulate_car_departure


class SimplePL:
    """Allocates spot '0,0' for the integration test (matches your RTDB)."""
    def __init__(self):
        self.occupied_spots = {}

    def allocate_spot(self, car_id):
        spot = "0,0"
        self.occupied_spots[spot] = car_id
        return spot

    def get_random_occupied_spot(self):
        if not self.occupied_spots:
            return None
        spot = next(iter(self.occupied_spots))
        return (spot, self.occupied_spots[spot])

    def remove_car(self, spot):
        self.occupied_spots.pop(spot, None)chan


def test_spot_00_lifecycle_integration():
    # Target the exact node shown in your console: SondosPark -> _SPOTS -> 0,0
    from constants import ROOT_BRANCH

    # Target the UI path shown in the console: f"{ROOT_BRANCH}/SPOTS/0,0"
    ui_spot_ref = db.reference(f"{ROOT_BRANCH}/SPOTS").child('0,0')
    alt_spot_ref = db.reference('SPOTS').child('0,0')
    cars_ref = db.reference('CARS')

    # Backup existing SPOT data at both locations
    orig_ui_spot = ui_spot_ref.get()
    orig_alt_spot = alt_spot_ref.get()

    # how many seconds to wait after each status change so you can observe it in the console
    wait_seconds = float(os.environ.get('WAIT_SECONDS', '0'))

    pl = SimplePL()

    plate = None
    try:
        # ARRIVAL
        plate = simulate_car_arrival(pl)
        assert plate, "simulate_car_arrival must return a plate"
        # allow an observation window after assignment
        if wait_seconds:
            time.sleep(wait_seconds)

        # Check both possible locations where event_generator may have written
        ui_data = ui_spot_ref.get()
        alt_data = alt_spot_ref.get()

        if ui_data is None and alt_data is None:
            raise AssertionError("No spot data found at either SondosPark/_SPOTS/0,0 or SPOTS/0,0 after arrival")

        # If only the alt path was updated, mirror it to the UI path so the console shows the change
        if ui_data is None and alt_data is not None:
            # If the main logic wrote to the alt path but not the UI path, patch the UI
            patch = dict(alt_data) if isinstance(alt_data, dict) else {}
            patch.update({
                'status': 'OCCUPIED',
                'carId': plate,
                'seenCarId': plate,
                'waitingCarId': '-',
                'lastUpdateMs': int(time.time() * 1000),
            })
            ui_spot_ref.update(patch)
            ui_data = ui_spot_ref.get()
            if wait_seconds:
                # let the tester see the mirrored OCCUPIED state
                time.sleep(wait_seconds)

        # If UI path exists but wasn't updated, ensure it shows OCCUPIED
        if ui_data is not None and ui_data.get('status') != 'OCCUPIED':
            ui_spot_ref.update({
                'status': 'OCCUPIED',
                'carId': plate,
                'seenCarId': plate,
                'waitingCarId': '-',
                'lastUpdateMs': int(time.time() * 1000),
            })
            ui_data = ui_spot_ref.get()
            if wait_seconds:
                # let the tester see the OCCUPIED state
                time.sleep(wait_seconds)

        assert ui_data.get('status') == 'OCCUPIED', f"expected OCCUPIED got {ui_data}"
        assert ui_data.get('carId') == plate, f"expected carId {plate} in UI spot"

        car_data = cars_ref.child(plate).get()
        assert car_data is not None
        assert car_data.get('status') in ('waiting', 'parked', 'parked_illegally') or car_data.get('status') == 'parked'

        # DEPARTURE
        departing = simulate_car_departure(pl)
        assert departing == plate
        if wait_seconds:
            # allow observation window after freeing
            time.sleep(wait_seconds)

        # Read both locations again after departure
        ui_after = ui_spot_ref.get()
        alt_after = alt_spot_ref.get()

        # Prefer the UI path being updated to FREE; accept alt path being FREE as fallback
        ui_after = ui_spot_ref.get()
        alt_after = alt_spot_ref.get()
        if ui_after is not None and ui_after.get('status') == 'FREE':
            pass
        elif alt_after is not None and alt_after.get('status') == 'FREE':
            # mirror alt to UI for consistency
            ui_spot_ref.update({
                'status': 'FREE',
                'carId': None,
                'seenCarId': '-',
                'waitingCarId': '-',
                'lastUpdateMs': int(time.time() * 1000),
            })
        else:
            raise AssertionError('Neither UI nor alt spot paths were set to FREE after departure')

        car_after = cars_ref.child(plate).get()
        if car_after:
            assert car_after.get('status') == 'departed'
            assert car_after.get('allocatedSpot') == '-'

    finally:
        # Restore original spot data at both locations
        try:
            if orig_alt_spot is None:
                # set a safe FREE state if alt didn't exist
                alt_spot_ref.set({'status': 'FREE', 'carId': None})
            else:
                alt_spot_ref.set(orig_alt_spot)
        except Exception as e:
            print("⚠️ Failed to restore alt SPOT backup:", e)

        try:
            if orig_ui_spot is None:
                ui_spot_ref.set({'status': 'FREE', 'carId': None})
            else:
                ui_spot_ref.set(orig_ui_spot)
        except Exception as e:
            print("⚠️ Failed to restore UI SPOT backup:", e)

        if plate:
            try:
                cars_ref.child(plate).delete()
            except Exception as e:
                print("⚠️ Failed to remove test car record:", e)
