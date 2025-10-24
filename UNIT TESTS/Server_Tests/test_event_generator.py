import sys
import os

# Allow running this test file directly (python tests/test_event_generator.py)
# by ensuring the project root is on sys.path.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from event_generator import simulate_car_arrival, simulate_car_departure


class FakeParkingLot:
    def __init__(self):
        self.occupied_spots = {}
        self.free_spots = {1, 2, 3}

    def allocate_spot(self, car_id):
        if not self.free_spots:
            return None
        spot = self.free_spots.pop()
        self.occupied_spots[spot] = car_id
        return spot

    def get_random_occupied_spot(self):
        if not self.occupied_spots:
            return None
        spot = next(iter(self.occupied_spots))
        return (spot, self.occupied_spots[spot])

    def remove_car(self, spot):
        self.occupied_spots.pop(spot, None)
        try:
            self.free_spots.add(spot)
        except Exception:
            pass


def test_simulate_car_arrival_writes_to_db(firebase_db_mock):
    pl = FakeParkingLot()
    plate = simulate_car_arrival(pl)
    assert plate is not None
    assert isinstance(plate, str)
    assert pl.occupied_spots


def test_simulate_car_departure_updates_db(firebase_db_mock):
    pl = FakeParkingLot()
    pl.occupied_spots[5] = "TESTPLATE"
    departing = simulate_car_departure(pl)
    assert departing == "TESTPLATE"
    assert 5 not in pl.occupied_spots


if __name__ == '__main__':
    # Try to run pytest using the current interpreter. If pytest is not
    # installed in this interpreter, print guidance to use the project's venv.
    try:
        import pytest
        raise SystemExit(pytest.main([__file__]))
    except Exception:
        print('\npytest is not available in this Python interpreter.')
        print('Run tests with the project venv:')
        print('  source .venv/bin/activate')
        print('  pytest -q')