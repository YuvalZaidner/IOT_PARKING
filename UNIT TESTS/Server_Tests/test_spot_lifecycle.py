from event_generator import simulate_car_arrival, simulate_car_departure


class SimplePL:
    """A tiny ParkingLot that always allocates spot '(0,0)' and tracks occupancy."""
    def __init__(self):
        self.occupied_spots = {}

    def allocate_spot(self, car_id):
        spot = '(0,0)'
        self.occupied_spots[spot] = car_id
        return spot

    def get_random_occupied_spot(self):
        if not self.occupied_spots:
            return None
        # return the only occupied spot
        spot = next(iter(self.occupied_spots))
        return (spot, self.occupied_spots[spot])

    def remove_car(self, spot):
        self.occupied_spots.pop(spot, None)


def test_spot_lifecycle(firebase_db_mock):
    # firebase_db_mock is the fake_reference factory with _registry attached
    pl = SimplePL()

    # ARRIVAL: simulate a car arriving and being allocated to '(0,0)'
    plate = simulate_car_arrival(pl)

    # assert CARS.{plate}.set called with status waiting
    cars_ref = firebase_db_mock._registry.get('CARS')
    assert cars_ref is not None, 'CARS ref should be created'
    car_child = cars_ref['children'].get(plate)
    assert car_child is not None, f'CARS.child({plate}) should be created'
    # initial set should have been called with status waiting
    car_child.set.assert_called()
    set_args = car_child.set.call_args[0][0]
    assert set_args.get('status') == 'waiting'

    # assert SPOTS.'(0,0)'.update called to OCCUPIED with carId
    spots_ref = firebase_db_mock._registry.get('SPOTS')
    assert spots_ref is not None, 'SPOTS ref should be created'
    spot_child = spots_ref['children'].get('(0,0)')
    assert spot_child is not None, "SPOTS.child('(0,0)') should be created"
    # update should be called with OCCUPIED and carId
    spot_child.update.assert_called()
    update_args = spot_child.update.call_args[0][0]
    assert update_args.get('status') == 'OCCUPIED'
    assert update_args.get('carId') == plate

    # DEPARTURE: simulate the car leaving
    departing = simulate_car_departure(pl)
    assert departing == plate

    # after departure, SPOTS.'(0,0)'.update should be called with status FREE and carId None
    # there may be multiple update calls, check the last call
    calls = spot_child.update.call_args_list
    assert calls, 'SPOT.update should have been called at least once'
    last_update = calls[-1].args[0]
    assert last_update.get('status') == 'FREE'
    assert last_update.get('carId') is None

    # and CARS.{plate}.update should have been called with status departed and allocatedSpot '-'
    assert car_child.update.called, 'CARS.child(...).update should have been called on departure'
    car_update_args = car_child.update.call_args[0][0]
    assert car_update_args.get('status') == 'departed'
    assert car_update_args.get('allocatedSpot') == '-'
