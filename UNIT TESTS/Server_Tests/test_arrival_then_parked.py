from event_generator import simulate_car_arrival, simulate_car_parked
from constants import ROOT_BRANCH


class ClosestPL:
    """ParkingLot stub that selects the closest free spot (by numeric distance)."""
    def __init__(self):
        # mapping spot_id -> distance
        self.free_spots = {'0,1': 3, '0,0': 1, '1,0': 5}
        self.occupied_spots = {}

    def allocate_spot(self, car_id):
        # choose spot with minimal distance
        spot = min(self.free_spots.items(), key=lambda kv: kv[1])[0]
        self.free_spots.pop(spot)
        # store with same key format as generator uses (string)
        self.occupied_spots[spot] = car_id
        return spot

    def get_random_occupied_spot(self):
        if not self.occupied_spots:
            return None
        spot = next(iter(self.occupied_spots))
        return (spot, self.occupied_spots[spot])

    def remove_car(self, spot):
        self.occupied_spots.pop(spot, None)


def test_arrival_then_parked(firebase_db_mock):
    # firebase_db_mock is the fake_reference factory with a _registry dict
    registry = firebase_db_mock._registry

    pl = ClosestPL()

    # ARRIVAL -> should assign closest spot '0,0' and mark it WAITING
    plate = simulate_car_arrival(pl)
    assert plate

    # locate the car child mock
    cars_entry = registry.get('CARS')
    assert cars_entry is not None
    car_child = cars_entry['children'].get(plate)
    assert car_child is not None

    # initial set called with waiting status
    assert car_child.set.called
    set_payload = car_child.set.call_args[0][0]
    assert set_payload.get('status') == 'waiting'

    # allocation should have triggered an update with ClosestSpot/allocatedSpot
    assert car_child.update.called
    update_payload = car_child.update.call_args_list[0][0][0]
    # verify ClosestSpot and allocatedSpot set to the closest spot
    assert update_payload.get('ClosestSpot') == '0,0'

    # spot should be set to WAITING under the UI branch
    spots_key = f"{ROOT_BRANCH}/SPOTS"
    spots_entry = registry.get(spots_key)
    assert spots_entry is not None
    spot_child = spots_entry['children'].get('0,0')
    assert spot_child is not None
    # verify that waiting update occurred
    assert spot_child.update.called
    spot_update_payload = spot_child.update.call_args[0][0]
    assert spot_update_payload.get('status') == 'WAITING'
    assert spot_update_payload.get('waitingCarId') == plate

    # Now simulate that the car physically parked
    parked_spot = simulate_car_parked(pl, plate)
    assert parked_spot == '0,0'

    # After parking, car record should be updated to SpotIn.Arrievied True and status 'parked'
    last_car_update = car_child.update.call_args_list[-1][0][0]
    assert last_car_update.get('SpotIn', {}).get('Arrievied') is True
    assert last_car_update.get('status') == 'parked'

    # Spot should be OCCUPIED and show carId/seenCarId
    last_spot_update = spot_child.update.call_args_list[-1][0][0]
    assert last_spot_update.get('status') == 'OCCUPIED'
    assert last_spot_update.get('carId') == plate
    assert last_spot_update.get('seenCarId') == plate
