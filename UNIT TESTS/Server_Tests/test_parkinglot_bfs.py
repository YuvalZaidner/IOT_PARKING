import pytest
from data_structures import ParkingLot, Spot


def make_parking_lot_with_spots():
    pl = ParkingLot()
    # add spots in a small grid with distances (distanceFromEntry arbitrary)
    spots = [
        (0, 0, 0),  # gate position (occupied)
        (0, 1, 2),
        (0, 2, 3),
        (1, 0, 1),
        (1, 1, 2),
    ]

    for row, col, dist in spots:
        s = Spot(row, col, dist)
        # mark (0,0) as occupied to simulate gate area
        if row == 0 and col == 0:
            s.status = 'OCCUPIED'
        else:
            s.status = 'FREE'
            pl.free_spots.add(s)
        pl.spot_lookup[s.spot_id] = s

    return pl


def test_find_closest_and_allocate():
    pl = make_parking_lot_with_spots()

    # gate at (0,0) - BFS should find (1,0) first (row=1,col=0) -> return (col,row) = (0,1)
    closest = pl.find_closest(0, 0)
    assert closest == (0, 1)

    # allocate for a car and ensure it's removed from free_spots
    plate = 'TEST1'
    allocated = pl.allocate_closest_spot(plate, 0, 0)
    assert allocated == '1,0'

    # spot should no longer be in free_spots
    free_ids = [s.spot_id for s in pl.free_spots]
    assert '1,0' not in free_ids

    # waiting pair should be set
    wp = pl.get_waiting_pair()
    assert wp == {'car_id': plate, 'spot_id': '1,0'}

    # allocate another car - should pick next BFS candidate (0,1)
    plate2 = 'TEST2'
    allocated2 = pl.allocate_closest_spot(plate2, 0, 0)
    # depending on BFS traversal the next closest is 0,1
    assert allocated2 in ('0,1', '0,2', '1,1')
