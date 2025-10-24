# Event Generator - Simulates car arrivals and departures
# This file generates events that write to Firebase RTDB, triggering the listener

import firebase_admin
from firebase_admin import credentials, db
import random
import time
import datetime
from data_structures import ParkingLot
import typing
from constants import ROOT_BRANCH


def refresh_spot_from_db(parking_lot: typing.Optional[ParkingLot], spot_id: str):
    """Refresh a single spot's status from RTDB into the in-memory ParkingLot.

    This reads /{ROOT_BRANCH}/SPOTS/{spot_id} and updates spot_lookup and free_spots
    so allocations use the latest external sensor updates (useful for sensor nodes).
    """
    if not parking_lot or not spot_id:
        return
    try:
        spots_ref = db.reference(f"/{ROOT_BRANCH}/SPOTS")
        node = spots_ref.child(str(spot_id)).get() or {}
        status = node.get('status')
        # ensure Spot object exists in parking_lot.spot_lookup
        sp = parking_lot.get_spot(spot_id)
        if not sp:
            # attempt to parse row,col and use distance if available
            try:
                row, col = spot_id.split(',')
                dist = node.get('distanceFromEntry') or node.get('distanceFromEntry', 0) or 0
                sp = type('SpotProxy', (), {})()
                sp.spot_id = spot_id
                sp.status = status or 'FREE'
                sp.distance_from_entry = int(dist) if dist is not None else 0
                # register in parking_lot
                parking_lot.spot_lookup[spot_id] = sp
                try:
                    parking_lot.add_spot(sp)
                except Exception:
                    try:
                        parking_lot.add_spot_to_free(sp)
                    except Exception:
                        pass
            except Exception:
                return
        else:
            # update existing Spot object status and free/occupied containers
            prev = getattr(sp, 'status', None)
            sp.status = status or prev or 'FREE'
            # reflect change in free_spots container
            try:
                if sp.status == 'FREE':
                    parking_lot.add_spot_to_free(sp)
                else:
                    parking_lot.remove_spot_from_free(sp)
            except Exception:
                pass
    except Exception as e:
        print(f"[WARN] refresh_spot_from_db({spot_id}) failed: {e}")

def generate_plate_id():
    """Generate a random 8-digit car plate ID"""
    return f"{random.randint(10000000, 99999999)}"

def simulate_car_arrival(parking_lot: typing.Optional[ParkingLot] = None):
    """Simulate a new car arriving - writes to Firebase RTDB and tries to allocate a spot using parking_lot"""
    plate_id = generate_plate_id()
    timestamp = datetime.datetime.now().isoformat()
    
    car_data = {
        'Id': plate_id,
        'ClosestSpot': '-',
        'SpotIn': {'Arrievied': False},
        'status': 'waiting',
        'allocatedSpot': '-',
        'timestamp': timestamp
    }
    
    cars_ref = db.reference(f"/{ROOT_BRANCH}/CARS")
    cars_ref.child(plate_id).set(car_data)

    # if this is a sensor-controlled spot (like 0,0) make sure we refresh it from DB
    try:
        refresh_spot_from_db(parking_lot, '0,0')
    except Exception:
        pass

    allocated_spot = None

    if parking_lot:
        # Try common allocation APIs on the provided ParkingLot
        try:
            # Prefer BFS-based allocator when available. Use explicit gate coords
            # so allocations are consistent with the UI. Gate defaults to (0,2)
            import os
            gate_row = int(os.environ.get('GATE_ROW', '0'))
            gate_col = int(os.environ.get('GATE_COL', '2'))
            if hasattr(parking_lot, 'allocate_closest_spot'):
                # compute BFS closest before allocator mutates free_spots
                try:
                    bfs_coord = parking_lot.find_closest(gate_row=gate_row, gate_col=gate_col)
                    bfs_key = f"{bfs_coord[0]},{bfs_coord[1]}" if bfs_coord else None
                except Exception:
                    bfs_key = None

                allocated_spot = parking_lot.allocate_closest_spot(plate_id, gate_row=gate_row, gate_col=gate_col)

                # defensive: if allocator result differs from precomputed BFS, prefer the BFS key
                if bfs_key and allocated_spot != bfs_key:
                    print(f"[WARN] allocator returned {allocated_spot} but BFS closest was {bfs_key} -> preferring BFS result")
                    # try to return allocated_spot to free_spots (if it was removed)
                    try:
                        if hasattr(parking_lot, 'get_spot') and allocated_spot:
                            spobj = parking_lot.get_spot(allocated_spot)
                            if spobj:
                                spobj.status = 'FREE'
                                if hasattr(parking_lot, 'add_spot_to_free'):
                                    parking_lot.add_spot_to_free(spobj)
                                else:
                                    try:
                                        parking_lot.free_spots.add(spobj)
                                    except Exception:
                                        pass
                    except Exception:
                        pass

                    # remove bfs_key from free list and set as waiting for this plate
                    allocated_spot = bfs_key
                    try:
                        if hasattr(parking_lot, 'get_spot'):
                            bsp = parking_lot.get_spot(bfs_key)
                            if bsp:
                                try:
                                    parking_lot.remove_spot_from_free(bsp)
                                except Exception:
                                    try:
                                        parking_lot.free_spots.remove(bsp)
                                    except Exception:
                                        pass
                                parking_lot.set_waiting_pair(plate_id, bfs_key)
                    except Exception:
                        pass
            else:
                # if no BFS allocator, fall back to a simple free_spots pop
                if hasattr(parking_lot, 'free_spots'):
                    try:
                        sp = parking_lot.free_spots.pop()
                        # if SortedList, pop() returns a Spot; if plain container, use it directly
                        allocated_spot = sp.spot_id if hasattr(sp, 'spot_id') else sp
                    except Exception:
                        allocated_spot = None
        except Exception as e:
            # allocation failed; leave as waiting
            print(f"⚠️ ParkingLot allocation error: {e}")

    if allocated_spot:
        # update RTDB to reflect allocation: assign closest spot and mark as waiting
        cars_ref.child(plate_id).update({'allocatedSpot': allocated_spot, 'ClosestSpot': allocated_spot, 'SpotIn': {'Arrievied': False}, 'status': 'waiting'})

        # write to UI branch so console reflects the waiting state
        spots_ref = db.reference(f"{ROOT_BRANCH}/SPOTS")
        spots_ref.child(str(allocated_spot)).update({'status': 'WAITING', 'waitingCarId': plate_id, 'seenCarId': '-'})
        print(f"🔔 Car {plate_id} assigned to spot {allocated_spot} (waiting)")
    else:
        print(f"⏳ Car {plate_id} added to queue (no spot allocated)")

    return plate_id

def simulate_car_departure(parking_lot: typing.Optional[ParkingLot]):
    """Simulate a car leaving using the parking lot structure and update RTDB"""
    if not parking_lot:
        print("❌ No ParkingLot provided!")
        return None

    spot_car_pair = None
    try:
        # Build a list of occupied (spot_id, car_id) tuples from available APIs
        occ_list = None
        if hasattr(parking_lot, 'get_occupied_spots'):
            occ_list = parking_lot.get_occupied_spots()
        elif hasattr(parking_lot, 'occupied_spots_with_cars'):
            occ_list = list(getattr(parking_lot, 'occupied_spots_with_cars').items())
        elif hasattr(parking_lot, 'occupied_spots'):
            occ_dict = getattr(parking_lot, 'occupied_spots') or {}
            occ_list = list(occ_dict.items())

        if occ_list:
            # Exclude the sensor-controlled spot '0,0' (and variant '(0,0)') per user request
            filtered = [(s, c) for (s, c) in occ_list if str(s) not in ('0,0', '(0,0)')]
            if not filtered:
                # No occupied spots available except the sensor-controlled one -> don't depart
                print("❌ No occupied spots found (excluding 0,0). Skipping departure.")
                return None
            spot_car_pair = random.choice(filtered)
        else:
            spot_car_pair = None
    except Exception as e:
        print(f"⚠️ Error querying ParkingLot: {e}")

    if not spot_car_pair:
        print("❌ No occupied spots found!")
        return None

    spot_id, departing_car_id = spot_car_pair
    print(f"🚗 Car {departing_car_id} leaving spot {spot_id}")

    # Update parking lot internal structures if possible so freed spot is visible to allocators
    try:
        if parking_lot:
            # Prefer modern API to remove occupied spot
            if hasattr(parking_lot, 'remove_occupied_spot'):
                try:
                    parking_lot.remove_occupied_spot(spot_id)
                except Exception:
                    # fallback to older dicts
                    if hasattr(parking_lot, 'occupied_spots_with_cars'):
                        parking_lot.occupied_spots_with_cars.pop(spot_id, None)
                    elif hasattr(parking_lot, 'occupied_spots'):
                        getattr(parking_lot, 'occupied_spots').pop(spot_id, None)
            else:
                # old API support
                try:
                    if hasattr(parking_lot, 'occupied_spots_with_cars'):
                        parking_lot.occupied_spots_with_cars.pop(spot_id, None)
                    elif hasattr(parking_lot, 'occupied_spots'):
                        getattr(parking_lot, 'occupied_spots').pop(spot_id, None)
                except Exception:
                    pass

            # set Spot.status back to FREE and add to free_spots container if possible
            try:
                if hasattr(parking_lot, 'get_spot'):
                    spot_obj = parking_lot.get_spot(spot_id)
                    if spot_obj:
                        spot_obj.status = 'FREE'
                        if hasattr(parking_lot, 'add_spot_to_free'):
                            parking_lot.add_spot_to_free(spot_obj)
                        else:
                            fs = getattr(parking_lot, 'free_spots', None)
                            if fs is not None:
                                try:
                                    fs.add(spot_obj)
                                except Exception:
                                    try:
                                        fs.append(spot_obj)
                                    except Exception:
                                        pass
                else:
                    fs = getattr(parking_lot, 'free_spots', None)
                    if fs is not None:
                        try:
                            fs.add(spot_id)
                        except Exception:
                            try:
                                fs.append(spot_id)
                            except Exception:
                                pass
            except Exception as e:
                print(f"⚠️ Error updating ParkingLot on departure: {e}")
    except Exception as e:
        print(f"⚠️ Error updating ParkingLot on departure: {e}")

    # Update RTDB - mark spot free and mark car as departed
    # update UI branch for spots (reset seen/waiting)
    spots_ref = db.reference(f"/{ROOT_BRANCH}/SPOTS")
    spots_ref.child(str(spot_id)).update({'status': 'FREE', 'carId': None, 'seenCarId': '-', 'waitingCarId': '-'})
    # Remove the car record from the RTDB so departed cars don't linger.
    # Attempt both the namespaced branch and the legacy top-level /CARS to be safe.
    try:
        namespaced_ref = db.reference(f"/{ROOT_BRANCH}/CARS").child(str(departing_car_id))
        try:
            # Best-effort update to mark departed before deletion (useful for listeners)
            namespaced_ref.update({'status': 'departed', 'allocatedSpot': '-'})
        except Exception:
            pass
        try:
            namespaced_ref.delete()
            print(f"[DB] Deleted car {departing_car_id} from /{ROOT_BRANCH}/CARS")
        except Exception:
            print(f"[DB] Failed to delete car {departing_car_id} from /{ROOT_BRANCH}/CARS")
    except Exception:
        print(f"[DB] Error handling namespaced car delete for {departing_car_id}")

    # Also attempt to remove legacy top-level /CARS entries if present
    try:
        legacy_ref = db.reference(f"/CARS").child(str(departing_car_id))
        try:
            legacy_ref.delete()
            print(f"[DB] Deleted car {departing_car_id} from /CARS (legacy)")
        except Exception:
            # not fatal; just log
            print(f"[DB] Failed to delete car {departing_car_id} from /CARS (legacy)")
    except Exception:
        pass

    print(f"✅ Triggered departure for spot {spot_id}")
    return departing_car_id


def simulate_car_parked(parking_lot: typing.Optional[ParkingLot], plate_id: str):
    """Mark a previously-assigned car as physically arrived and update RTDB.

    - Sets CARS/{plate}.SpotIn.Arrievied = True and status = 'parked'
    - Updates SondosPark/SPOTS/{spot}: status -> 'OCCUPIED', carId/seenCarId -> plate, waitingCarId -> '-'
    - Updates parking_lot internal structures where possible
    Returns the allocated spot id or None on failure.
    """
    if not plate_id:
        print("❌ No plate id provided to simulate_car_parked")
        return None

    cars_ref = db.reference(f"/{ROOT_BRANCH}/CARS")
    # Find allocated spot: prefer parking_lot mapping, fallback to DB stored allocatedSpot
    allocated_spot = None
    try:
        if parking_lot and hasattr(parking_lot, 'occupied_spots'):
            # find spot by matching plate id
            for s, c in getattr(parking_lot, 'occupied_spots').items():
                if c == plate_id:
                    allocated_spot = s
                    break
        if not allocated_spot:
            car_record = cars_ref.child(plate_id).get() or {}
            allocated_spot = car_record.get('allocatedSpot')
    except Exception as e:
        print(f"⚠️ Error determining allocated spot for {plate_id}: {e}")

    if not allocated_spot:
        print(f"❌ No allocated spot found for car {plate_id}")
        return None

    # Update car record: arrived
    try:
        cars_ref.child(plate_id).update({'SpotIn': {'Arrievied': True}, 'status': 'parked', 'allocatedSpot': allocated_spot})
    except Exception as e:
        print(f"⚠️ Failed to update car record for {plate_id}: {e}")

    # Update spot record to OCCUPIED and set seen/waiting fields
    spots_ref = db.reference(f"{ROOT_BRANCH}/SPOTS")
    ts = int(time.time() * 1000)
    try:
        spots_ref.child(str(allocated_spot)).update({'status': 'OCCUPIED', 'carId': plate_id, 'seenCarId': plate_id, 'waitingCarId': '-', 'lastUpdateMs': ts})
    except Exception as e:
        print(f"⚠️ Failed to update spot {allocated_spot} for parked car {plate_id}: {e}")

    # Update parking_lot internal structures if APIs available
    try:
        if parking_lot:
            if hasattr(parking_lot, 'add_occupied_spot'):
                parking_lot.add_occupied_spot(allocated_spot, plate_id)
            elif hasattr(parking_lot, 'occupied_spots'):
                parking_lot.occupied_spots[allocated_spot] = plate_id
            # remove from free_spots if present
            if hasattr(parking_lot, 'free_spots'):
                fs = getattr(parking_lot, 'free_spots')
                try:
                    if isinstance(fs, set):
                        fs.discard(allocated_spot)
                    else:
                        # try remove for list-like
                        try:
                            fs.remove(allocated_spot)
                        except Exception:
                            pass
                except Exception:
                    pass
    except Exception as e:
        print(f"⚠️ Error updating parking_lot internals for parked car {plate_id}: {e}")

    print(f"✅ Car {plate_id} parked at spot {allocated_spot}")
    return allocated_spot
