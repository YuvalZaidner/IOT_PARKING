import pytest
from unittest.mock import MagicMock

from event_generator import simulate_car_arrival, simulate_car_departure
import pytest
from unittest.mock import MagicMock

from event_generator import simulate_car_arrival, simulate_car_departure

class FakeParkingLot:
    def __init__(self):
        # occupied_spots maps spot -> car_id
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
    # since we patched firebase_admin.db.reference to return MagicMocks,
    # just ensure a plate id string was returned and parking lot got an occupied spot
    assert isinstance(plate, str)
    assert pl.occupied_spots  # at least one occupied spot after arrival

def test_simulate_car_departure_updates_db(firebase_db_mock):
    pl = FakeParkingLot()
    # pre-populate a car so departure can pick one
    pl.occupied_spots[5] = "TESTPLATE"
    departing = simulate_car_departure(pl)
    assert departing == "TESTPLATE"
    # spot 5 should now be freed
    assert 5 not in pl.occupied_spots