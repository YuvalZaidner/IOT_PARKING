import random
import time
from firebase_admin import db
from firebase_init import db as _db_init  # ensures app is initialized
from constants import ROOT_BRANCH
from data_structures import ParkingLot, Spot
from event_generator import simulate_car_arrival, simulate_car_parked, simulate_car_departure, generate_plate_id
import os


# obtain the SPOTS reference lazily to avoid using a reference created before firebase app init
def get_spots_ref():
    return db.reference(f"/{ROOT_BRANCH}/SPOTS")


def get_cars_ref():
    """Return the CARS reference under the configured ROOT_BRANCH.

    Other modules use db.reference(ROOT_BRANCH).child('CARS'), so ensure
    we operate on the same path instead of the top-level '/CARS'.
    """
    return db.reference(f"/{ROOT_BRANCH}/CARS")


def migrate_top_level_cars(copy_only: bool = True):
    """Copy car records referenced by SPOTS from top-level /CARS into /{ROOT_BRANCH}/CARS.

    - If copy_only is True (default) the function copies records and leaves originals.
    - If copy_only is False, after copying the referenced records it will delete them from /CARS.

    Returns a dict with counts: {'found': n_found, 'copied': n_copied, 'deleted': n_deleted}
    """
    spots = get_spots_ref().get() or {}
    occupied = {k: v for k, v in spots.items() if isinstance(v, dict) and (v.get('status') or '').upper() != 'FREE'}
    if not occupied:
        print("[SIM] No occupied spots found; nothing to migrate.")
        return {'found': 0, 'copied': 0, 'deleted': 0}

    top_ref = db.reference('/CARS')
    ns_ref = get_cars_ref()

    top_data = top_ref.get() or {}
    ns_data = ns_ref.get() or {}

    found_ids = set(v.get('carId') for v in occupied.values() if v.get('carId'))
    found_ids = {fid for fid in found_ids if fid}
    print(f"[SIM] Found {len(found_ids)} carIds referenced by occupied spots")

    copied = 0
    deleted = 0
    for cid in found_ids:
        if cid in ns_data:
            # already present in namespaced node
            continue
        if cid in top_data:
            try:
                ns_ref.child(cid).set(top_data[cid])
                copied += 1
            except Exception as e:
                print(f"[SIM] Failed to copy car {cid}:", e)

    if not copy_only:
        for cid in found_ids:
            if cid in top_data:
                try:
                    top_ref.child(cid).delete()
                    deleted += 1
                except Exception as e:
                    print(f"[SIM] Failed to delete top-level car {cid}:", e)

    print(f"[SIM] Migration summary: found={len(found_ids)} copied={copied} deleted={deleted} (copy_only={copy_only})")
    return {'found': len(found_ids), 'copied': copied, 'deleted': deleted}


def clear_cars_and_reset_spots():
    """Remove all car records from the DB and set every spot to FREE.

    This is a stronger reset than `set_all_spots_free()` because it also
    deletes the `CARS` node entirely so there are no leftover car records.
    """
    print(f"[SIM] Clearing all car records from /{ROOT_BRANCH}/CARS and resetting /{ROOT_BRANCH}/SPOTS to FREE...")
    cars_ref = get_cars_ref()

    # attempt to delete the whole node, retry a few times if necessary
    for attempt in range(3):
        try:
            cars_ref.delete()
            print(f"[SIM] /{ROOT_BRANCH}/CARS deleted.")
            break
        except Exception as e:
            print(f"[SIM] Attempt {attempt+1} to delete /{ROOT_BRANCH}/CARS failed:", e)
            # fallback to per-child delete on failure
            try:
                data = cars_ref.get() or {}
                for k in list(data.keys()):
                    try:
                        cars_ref.child(k).delete()
                    except Exception:
                        pass
                # re-check
                remaining = cars_ref.get() or {}
                if not remaining:
                    print(f"[SIM] /{ROOT_BRANCH}/CARS children deleted via fallback.")
                    break
            except Exception as e2:
                print(f"[SIM] Failed to enumerate /{ROOT_BRANCH}/CARS for deletion:", e2)
        time.sleep(0.5)
    else:
        print(f"[SIM] Warning: /{ROOT_BRANCH}/CARS could not be fully deleted after retries.")

    # now set all spots to FREE (reuse helper) and verify
    set_all_spots_free()

    # verify spots and cars state; retry a couple times if DB hasn't reflected changes
    for attempt in range(5):
        try:
            cars_now = get_cars_ref().get()
            spots_now = get_spots_ref().get() or {}
            all_free = True
            for v in spots_now.values():
                if isinstance(v, dict) and (v.get('status') or '').upper() != 'FREE':
                    all_free = False
                    break
            if (not cars_now or cars_now == {}) and all_free:
                print(f"[SIM] Verification succeeded: /{ROOT_BRANCH}/CARS empty and all spots FREE.")
                break
            else:
                print(f"[SIM] Verification attempt {attempt+1}: CARS present? {bool(cars_now)}; all_free? {all_free}. Retrying...")
                # try resetting spots again if needed
                if not all_free:
                    set_all_spots_free()
        except Exception as e:
            print("[SIM] Verification error:", e)
        time.sleep(0.5)
    else:
        print("[SIM] Warning: verification failed — DB may not be fully reset.")


def load_parking_lot_from_db():
    data = get_spots_ref().get() or {}
    if not data:
        print("[SIM] No spots found — did you run the initializer?")
        return None, {}

    pl = ParkingLot()
    # Keep a backup to restore later
    backup = {}

    for sid, s in data.items():
        if not isinstance(s, dict):
            continue
        # sid expected in form 'row,col' or '(row,col)'
        backup[sid] = s
        try:
            row_str, col_str = sid.strip('()').split(',')
            row, col = int(row_str), int(col_str)
        except Exception:
            # try splitting on other delimiters
            parts = sid.replace('(', '').replace(')', '').split(',')
            if len(parts) >= 2:
                row, col = int(parts[0]), int(parts[1])
            else:
                continue

        dist = s.get('distanceFromEntry', 0) or 0
        spot = Spot(row, col, dist)
        # mirror status from DB
        spot.status = s.get('status', 'FREE')
        spot.waiting_car_id = s.get('waitingCarId', '-')
        spot.seen_car_id = s.get('seenCarId', '-')
        pl.spot_lookup[spot.spot_id] = spot
        if spot.status == 'FREE':
            pl.free_spots.add(spot)

    # debug: print free spots and distances
    print(f"[SIM] Loaded parking lot: free_spots_count={len(pl.free_spots)}")
    sample = [(sp.spot_id, sp.distance_from_entry) for sp in pl.free_spots]
    print("[SIM] Free spots (id,dist) sample:", sample[:10])

    return pl, backup


def set_all_spots_free():
    """Set every spot under ROOT_BRANCH/SPOTS to FREE in the RTDB.

    This writes a minimal FREE state (status, carId, seenCarId, waitingCarId, lastUpdateMs)
    for every spot key found under the SPOTS node.
    """
    data = get_spots_ref().get() or {}
    if not data:
        print("[SIM] No spots found to reset.")
        return

    ts = int(time.time() * 1000)
    print(f"[SIM] Setting all {len(data)} spots to FREE...")
    for sid in data.keys():
        payload = {
            'status': 'FREE',
            'carId': None,
            'seenCarId': '-',
            'waitingCarId': '-',
            'lastUpdateMs': ts,
        }
        # attempt a few times per spot in case of transient errors
        for attempt in range(3):
            try:
                # use set() to ensure the entire spot entry is written to the expected shape
                get_spots_ref().child(sid).set({**(data.get(sid) if isinstance(data.get(sid), dict) else {}), **payload})
                break
            except Exception as e:
                print(f"⚠️ Failed to reset spot {sid} (attempt {attempt+1}):", e)
                time.sleep(0.2)
        else:
            print(f"⚠️ Giving up resetting spot {sid} after retries.")
    print("[SIM] All spots set to FREE (requests issued).")


def inject_wrong_park(parking_lot: ParkingLot):
    """Cause a car to park in a random free spot that is NOT the BFS-closest.

    Behavior:
    - Choose the current BFS closest via parking_lot.find_closest
    - From the free_spots choose a different random free spot
    - Write a temporary 'WRONG_PARK' state to that spot (used to show purple) for 2s
    - After 2s, set spot to 'OCCUPIED' and create a CARS entry for the parked car
    - Update parking_lot internal structures accordingly
    Returns the spot_id chosen or None on failure.
    """
    try:
        if not parking_lot:
            return None
        # determine BFS closest
        try:
            bfs = parking_lot.find_closest()
            bfs_key = f"{bfs[0]},{bfs[1]}" if bfs else None
        except Exception:
            bfs_key = None

        # list free spots available
        free_list = []
        if hasattr(parking_lot, 'free_spots'):
            try:
                free_list = [sp for sp in parking_lot.free_spots if getattr(sp, 'spot_id', None) != bfs_key]
            except Exception:
                # fallback: build from spot_lookup
                free_list = [s for s in parking_lot.spot_lookup.values() if getattr(s, 'status', None) == 'FREE' and s.spot_id != bfs_key]

        if not free_list:
            print("[SIM] No alternative free spot available for wrong-park")
            return None

        chosen = random.choice(free_list)
        chosen_id = chosen.spot_id if hasattr(chosen, 'spot_id') else str(chosen)

        spots_ref = get_spots_ref()
        cars_ref = get_cars_ref()

        # set temporary wrong-park visual state (use status 'WRONG_PARK' so UI can color purple)
        ts = int(time.time() * 1000)
        try:
            spots_ref.child(str(chosen_id)).update({'status': 'WRONG_PARK', 'carId': None, 'seenCarId': '-', 'waitingCarId': '-', 'lastUpdateMs': ts})
        except Exception as e:
            print("⚠️ Failed to write WRONG_PARK state for", chosen_id, e)

        # mark the BFS-closest spot as WAITING (orange) to reflect that the system had intended
        # the car to go there. Remove it from free_spots so UI shows orange.
        if bfs_key:
            try:
                spots_ref.child(str(bfs_key)).update({'status': 'WAITING', 'waitingCarId': '-', 'lastUpdateMs': ts})
                spobj = parking_lot.get_spot(bfs_key) if hasattr(parking_lot, 'get_spot') else None
                if spobj:
                    spobj.status = 'WAITING'
                    try:
                        parking_lot.remove_spot_from_free(spobj)
                    except Exception:
                        try:
                            parking_lot.remove_spot_from_free(bfs_key)
                        except Exception:
                            pass
            except Exception:
                pass

        print(f"[SIM] Injected wrong-park at {chosen_id} (purple) and set closest {bfs_key} to WAITING (orange).")
        # keep the closest WAITING state briefly (1s), but keep the wrong-park purple for 2s total
        time.sleep(1)

        # restore the BFS-closest spot to FREE (after 1s)
        if bfs_key:
            try:
                spots_ref.child(str(bfs_key)).update({'status': 'FREE', 'waitingCarId': '-', 'carId': None, 'seenCarId': '-', 'lastUpdateMs': int(time.time() * 1000)})
                spobj = parking_lot.get_spot(bfs_key) if hasattr(parking_lot, 'get_spot') else None
                if spobj:
                    spobj.status = 'FREE'
                    try:
                        parking_lot.add_spot_to_free(spobj)
                    except Exception:
                        try:
                            parking_lot.free_spots.add(spobj)
                        except Exception:
                            pass
            except Exception:
                pass

        # keep the wrong-park purple for one more second (total 2s)
        time.sleep(1)

        # mark wrong spot as occupied and create car record
        plate = generate_plate_id()
        car_payload = {'Id': plate, 'allocatedSpot': chosen_id, 'status': 'parked', 'SpotIn': {'Arrievied': True}, 'timestamp': time.time()}
        try:
            cars_ref.child(plate).set(car_payload)
            spots_ref.child(str(chosen_id)).update({'status': 'OCCUPIED', 'carId': plate, 'seenCarId': plate, 'waitingCarId': '-', 'lastUpdateMs': int(time.time() * 1000)})
        except Exception as e:
            print("⚠️ Failed to finalize wrong-park for", chosen_id, e)

        # update parking_lot internals: remove chosen from free and mark occupied
        try:
            try:
                parking_lot.remove_spot_from_free(chosen)
            except Exception:
                try:
                    parking_lot.remove_spot_from_free(chosen_id)
                except Exception:
                    pass
            if hasattr(parking_lot, 'add_occupied_spot'):
                parking_lot.add_occupied_spot(chosen_id, plate)
            else:
                parking_lot.occupied_spots_with_cars[chosen_id] = plate
        except Exception:
            pass

        print(f"[SIM] Wrong-park finalized: car {plate} at {chosen_id}; closest {bfs_key} was restored to FREE earlier")
        return chosen_id
    except Exception as e:
        print("[SIM] inject_wrong_park failed:", e)
        return None



def refresh_parking_lot(parking_lot: ParkingLot):
    """Refresh the in-memory parking lot state from the database without losing structure.
    
    This updates the status and occupancy of spots to reflect external changes.
    """
    try:
        data = get_spots_ref().get() or {}
        if not data:
            return parking_lot
        
        # Update existing spots
        for sid, s in data.items():
            if not isinstance(s, dict):
                continue
            
            spot = parking_lot.spot_lookup.get(sid)
            if not spot:
                continue
            
            old_status = spot.status
            new_status = s.get('status', 'FREE')
            
            # Update spot attributes
            spot.status = new_status
            spot.waiting_car_id = s.get('waitingCarId', '-')
            spot.seen_car_id = s.get('seenCarId', '-')
            
            # Synchronize free_spots set
            if new_status == 'FREE' and spot not in parking_lot.free_spots:
                parking_lot.free_spots.add(spot)
            elif new_status != 'FREE' and spot in parking_lot.free_spots:
                parking_lot.free_spots.discard(spot)
            
            # Update occupied tracking
            car_id = s.get('carId')
            if new_status == 'OCCUPIED' and car_id:
                parking_lot.occupied_spots_with_cars[sid] = car_id
            elif sid in parking_lot.occupied_spots_with_cars and new_status != 'OCCUPIED':
                parking_lot.occupied_spots_with_cars.pop(sid, None)
        
        print(f"[SIM] Refreshed parking lot: free_spots={len(parking_lot.free_spots)}, occupied={len(parking_lot.occupied_spots_with_cars)}")
        return parking_lot
    except Exception as e:
        print(f"[SIM] Error refreshing parking lot: {e}")
        return parking_lot


def simulate_n_arrivals(n: int = 5, keep_changes: bool = False, wait_between: float = 1.0, arrival_interval: float = 7.0):
    # ensure we start from a clean state in the DB: remove all cars and set spots FREE
    clear_cars_and_reset_spots()
    # reload parking lot from DB so in-memory model matches what we just written
    pl, backup = load_parking_lot_from_db()
    if pl is None:
        return

    created_plates = []
    # periodic departure timer
    depart_interval = float(os.environ.get('DEPART_INTERVAL_SECONDS', '30'))
    # when the lot is full we want an accelerated departure cadence
    depart_when_full = float(os.environ.get('DEPART_WHEN_FULL_SECONDS', '10'))
    last_depart_time = time.time()
    # wrong-park injector (every X seconds a car parks in a non-closest free spot)
    wrong_park_interval = float(os.environ.get('WRONG_PARK_SECONDS', '45'))
    last_wrong_time = time.time()
    # Add refresh interval
    refresh_interval = float(os.environ.get('REFRESH_INTERVAL_SECONDS', '3'))
    last_refresh_time = time.time()
    
    try:
        # sequential arrival -> parked for each car, ensuring allocation moves spot to occupied
        print(f"[SIM] Arrival interval set to {arrival_interval} seconds (env ARRIVAL_INTERVAL_SECONDS)")
        for i in range(n):
            # Periodically refresh parking lot state from DB
            if time.time() - last_refresh_time >= refresh_interval:
                pl = refresh_parking_lot(pl)
                last_refresh_time = time.time()
            
            # if in-memory shows no free spots, we still trigger departures every depart_when_full seconds
            try:
                if (not getattr(pl, 'free_spots', None)) or (hasattr(pl, 'free_spots') and len(pl.free_spots) == 0):
                    if time.time() - last_depart_time >= depart_when_full:
                        simulate_car_departure(pl)
                        last_depart_time = time.time()
                        # give a short moment for DB writes to propagate
                        time.sleep(min(1.0, wait_between))
                        # re-load parking lot state to reflect departure
                        pl, _ = load_parking_lot_from_db()
            except Exception:
                pass
            start_ts = time.time()
            plate = simulate_car_arrival(pl)
            created_plates.append(plate)
            # allow a short delay for the WAITING state to be written/read
            time.sleep(wait_between)
            # print debug snapshot after allocation
            print(f"[SIM] After arrival: free_spots_count={len(pl.free_spots)}; waiting_pair={pl.get_waiting_pair()}")
            # simulate the car physically parking
            simulate_car_parked(pl, plate)
            print(f"[SIM] After parked: free_spots_count={len(pl.free_spots)}; occupied_count={len(pl.occupied_spots_with_cars)}")
            # extra small sleep to let parked writes propagate
            time.sleep(wait_between)

            # pace arrivals so that each arrival starts approximately arrival_interval seconds apart
            elapsed = time.time() - start_ts
            remaining = arrival_interval - elapsed
            if remaining > 0:
                print(f"[SIM] Sleeping {remaining:.2f}s until next arrival (to respect arrival_interval)")
                time.sleep(remaining)

            # periodically inject a wrong-park event (a car parks in a random free spot that is NOT the closest)
            try:
                if time.time() - last_wrong_time >= wrong_park_interval:
                    _ = inject_wrong_park(pl)
                    last_wrong_time = time.time()
            except Exception:
                pass

            # after all have parked, explicitly free each allocated spot and remove the car record
        cars_ref = get_cars_ref()
        spots_ref = get_spots_ref()
        parked_info = []
        for plate in created_plates:
            car_rec = cars_ref.child(plate).get() or {}
            allocated = car_rec.get('allocatedSpot')
            if allocated:
                parked_info.append((plate, allocated))

        for plate, spot in parked_info:
            ts = int(time.time() * 1000)
            try:
                spots_ref.child(str(spot)).update({'status': 'FREE', 'carId': None, 'seenCarId': '-', 'waitingCarId': '-', 'lastUpdateMs': ts})
            except Exception as e:
                print("⚠️ Failed to set spot FREE in DB:", spot, e)

            # update parking lot internals
            try:
                if hasattr(pl, 'remove_occupied_spot'):
                    pl.remove_occupied_spot(spot)
                elif hasattr(pl, 'remove_car'):
                    pl.remove_car(spot)
            except Exception:
                pass

            # remove car record from DB
            try:
                cars_ref.child(plate).delete()
            except Exception:
                pass

            print(f"🚗 Car {plate} departed from spot {spot} and spot set to FREE")
            time.sleep(wait_between)
            # trigger a periodic departure if enough time passed
            try:
                if time.time() - last_depart_time >= depart_interval:
                    simulate_car_departure(pl)
                    last_depart_time = time.time()
            except Exception:
                pass

        print(f"[SIM] Simulated {n} arrivals and parked them.")

        if not keep_changes:
            print("[SIM] Restoring original SPOTS from backup...")
            for sid, s in backup.items():
                try:
                    get_spots_ref().child(sid).set(s)
                except Exception as e:
                    print("⚠️ Failed to restore spot", sid, e)
            # remove created cars
            cars_ref = get_cars_ref()
            for p in created_plates:
                try:
                    cars_ref.child(p).delete()
                except Exception:
                    pass
            print("[SIM] Restore complete.")
    except KeyboardInterrupt:
        print("[SIM] Interrupted by user — leaving current DB state as-is.")


def simulate_continuous_arrivals(keep_changes: bool = False, wait_between: float = 1.0, arrival_interval: float = 5.0):
    """Run arrivals forever (until KeyboardInterrupt). Each arrival is paced by arrival_interval seconds.

    If the parking lot is full, a message is printed to the console each interval.
    On KeyboardInterrupt, if keep_changes is False the original SPOTS backup is restored and created car records removed.
    """
    # prepare DB and in-memory lot (remove cars and reset spots to FREE)
    clear_cars_and_reset_spots()
    pl, backup = load_parking_lot_from_db()
    if pl is None:
        return

    created_plates = []
    depart_interval = float(os.environ.get('DEPART_INTERVAL_SECONDS', '30'))
    depart_when_full = float(os.environ.get('DEPART_WHEN_FULL_SECONDS', '10'))
    last_depart_time = time.time()
    wrong_park_interval = float(os.environ.get('WRONG_PARK_SECONDS', '45'))
    last_wrong_time = time.time()
    # Add refresh interval to periodically sync with DB
    refresh_interval = float(os.environ.get('REFRESH_INTERVAL_SECONDS', '3'))
    last_refresh_time = time.time()
    
    try:
        print(f"[SIM] Starting continuous arrivals every {arrival_interval}s (press Ctrl+C to stop)")
        while True:
            # Periodically refresh parking lot state from DB to catch external changes
            if time.time() - last_refresh_time >= refresh_interval:
                pl = refresh_parking_lot(pl)
                last_refresh_time = time.time()
            
            start_ts = time.time()
            # if no free spots, print a message and wait until next interval
            if not getattr(pl, 'free_spots', None) or len(pl.free_spots) == 0:
                # double-check the real DB in case the in-memory model drifted
                try:
                    data = get_spots_ref().get() or {}
                    db_free = sum(1 for v in data.values() if isinstance(v, dict) and (v.get('status') or '').upper() == 'FREE')
                except Exception:
                    db_free = 0

                if db_free == 0:
                    # parking full: trigger departures every depart_when_full seconds
                    try:
                        if time.time() - last_depart_time >= depart_when_full:
                            simulate_car_departure(pl)
                            last_depart_time = time.time()
                            # short wait to allow DB propagation before re-evaluating
                            time.sleep(min(arrival_interval, 1.0))
                            continue
                    except Exception:
                        pass
                    print("[SIM] PARKING FULL — no free spots available. Waiting until next check...")
                    time.sleep(arrival_interval)
                    continue
                else:
                    # DB reports free spots; resync the in-memory parking lot and continue
                    print(f"[SIM] In-memory free_spots empty but DB shows {db_free} FREE spots -> resyncing in-memory model")
                    try:
                        pl, backup = load_parking_lot_from_db()
                        if pl is None:
                            print("[SIM] Failed to reload parking lot from DB during resync")
                            time.sleep(arrival_interval)
                            continue
                    except Exception as e:
                        print(f"[SIM] Error resyncing parking lot: {e}")
                        time.sleep(arrival_interval)
                        continue

            plate = simulate_car_arrival(pl)
            if not plate:
                print("[SIM] simulate_car_arrival returned no plate — skipping")
                time.sleep(arrival_interval)
                continue

            created_plates.append(plate)
            # short delay so WAITING state persists briefly
            time.sleep(wait_between)
            print(f"[SIM] Arrival: free_spots_count={len(pl.free_spots)}; waiting_pair={pl.get_waiting_pair()}")
            simulate_car_parked(pl, plate)
            # (optionally) record or log parked cars; departures are timed periodically
            print(f"[SIM] Parked: free_spots_count={len(pl.free_spots)}; occupied_count={len(pl.occupied_spots_with_cars)}")
            time.sleep(wait_between)

            # pace to arrival_interval
            elapsed = time.time() - start_ts
            remaining = arrival_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)

            # periodically inject wrong-park events
            try:
                if time.time() - last_wrong_time >= wrong_park_interval:
                    _ = inject_wrong_park(pl)
                    last_wrong_time = time.time()
            except Exception:
                pass

            # trigger periodic departure
            try:
                if time.time() - last_depart_time >= depart_interval:
                    simulate_car_departure(pl)
                    last_depart_time = time.time()
            except Exception:
                pass

    except KeyboardInterrupt:
        print("[SIM] Continuous simulation interrupted by user — cleaning up...")
        if not keep_changes:
            print("[SIM] Restoring original SPOTS from backup...")
            for sid, s in backup.items():
                try:
                    get_spots_ref().child(sid).set(s)
                except Exception as e:
                    print("⚠️ Failed to restore spot", sid, e)
            cars_ref = get_cars_ref()
            for p in created_plates:
                try:
                    cars_ref.child(p).delete()
                except Exception:
                    pass
            print("[SIM] Restore complete.")
        else:
            print("[SIM] Leaving changes in RTDB (KEEP_CHANGES=1).")


def main():
    # Ensure DB is cleared and all spots set to FREE at program start
    clear_cars_and_reset_spots()

    keep = os.environ.get('KEEP_CHANGES', '0') == '1'
    wait = float(os.environ.get('WAIT_SECONDS', '1'))
    n = int(os.environ.get('N_ARRIVALS', '0'))
    arrival_interval = float(os.environ.get('ARRIVAL_INTERVAL_SECONDS', '5'))
    # If N_ARRIVALS is 0 -> run continuous arrivals until interrupted
    if n == 0:
        simulate_continuous_arrivals(keep_changes=keep, wait_between=wait, arrival_interval=arrival_interval)
    else:
        simulate_n_arrivals(n, keep_changes=keep, wait_between=wait, arrival_interval=arrival_interval)


if __name__ == "__main__":
    main()
