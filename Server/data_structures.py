from typing import Dict, Optional, Tuple, Callable
import random
from bisect import bisect_left, insort
from collections import deque

class SortedList:
    """A small sorted list with optional key function. Compatible with previous API.

    If key is provided, items are ordered by key(item). Internally stores
    tuples (k, item) when key is set to allow use of insort.
    """
    def __init__(self, iterable=None, key: Optional[Callable] = None):
        self._key = key
        self._list = []
        if iterable:
            for item in iterable:
                self.add(item)

    def _wrap(self, value):
        return (self._key(value), value) if self._key is not None else value

    def add(self, value):
        if self._key is None:
            insort(self._list, value)
        else:
            # Ensure internal storage uses (key, item) tuples
            if self._list and not isinstance(self._list[0], tuple):
                self._list = [(self._key(v), v) for v in self._list]
            k = self._key(value)
            # build keys list for bisect search to avoid comparing items directly
            keys = [kv[0] for kv in self._list]
            idx = bisect_left(keys, k)
            self._list.insert(idx, (k, value))

    def remove(self, value):
        if self._key is None:
            idx = bisect_left(self._list, value)
            if idx != len(self._list) and self._list[idx] == value:
                self._list.pop(idx)
                return
            raise ValueError(f"{value} not in SortedList")
        else:
            # find by identity of stored item
            for i, (k, item) in enumerate(self._list):
                if item == value:
                    self._list.pop(i)
                    return
            raise ValueError(f"{value} not in SortedList")

    def pop(self, index=-1):
        val = self._list.pop(index)
        return val[1] if self._key is not None else val

    def __len__(self):
        return len(self._list)

    def __getitem__(self, idx):
        val = self._list[idx]
        return val[1] if self._key is not None else val

    def __iter__(self):
        if self._key is None:
            return iter(self._list)
        else:
            return (item for (_, item) in self._list)

    def __contains__(self, value):
        if self._key is None:
            idx = bisect_left(self._list, value)
            return idx != len(self._list) and self._list[idx] == value
        else:
            return any(item == value for (_, item) in self._list)

    def index(self, value):
        if self._key is None:
            idx = bisect_left(self._list, value)
            if idx != len(self._list) and self._list[idx] == value:
                return idx
            raise ValueError(f"{value} not in SortedList")
        else:
            for i, (_, item) in enumerate(self._list):
                if item == value:
                    return i
            raise ValueError(f"{value} not in SortedList")

class Spot:
    """Represents a parking spot with coordinates, distance, and status"""
    
    def __init__(self, row: int, col: int, distance: int):
        # RTDB fields
        self.status = "FREE"
        self.waiting_car_id = "-"
        self.seen_car_id = "-"
        self.distance_from_entry = distance
        
        # Local-only field for efficiency (matches RTDB key format)
        # use plain 'row,col' key format to match event_generator and RTDB child naming
        self.spot_id = f"{row},{col}"
    
    # RTDB sync methods removed

class Car:
    """Represents a car with plate ID, status, and parking information"""
    
    def __init__(self, plate_id: str):
        # RTDB fields
        self.plate_id = plate_id
        self.status = "waiting"  # waiting, parked, parked_illegally
        self.allocated_spot = "-"
        self.timestamp = ""
        
        # Local-only fields
        self.actual_spot = None  # Where car actually parked (if different from allocated)
    
    # RTDB sync methods removed

class ParkingLot:
    """Main class that manages all parking lot data structures and operations"""
    
    def __init__(self):
        # AVL tree (SortedList) of free spots, ordered by distance from entry
        # support key to order by Spot.distance_from_entry
        self.free_spots = SortedList(key=lambda spot: spot.distance_from_entry)

        # Hash tables for O(1) lookups
        self.spot_lookup = {}  # spot_id -> Spot object
        self.car_lookup = {}   # car_plate -> Car object
        # Current waiting pair (car allocated to spot but not yet parked)
        self.waiting_pair = None  # {"car_id": str, "spot_id": str} or None

        # Hash table of occupied spots: spot_id -> car_id (O(1) operations)
        self.occupied_spots_with_cars = {}

        # Variable to hold the time we saved (e.g., last state save timestamp)
        self.saved_time = None
        self.isFull = False
    
    # Basic data operations
    def add_spot(self, spot):
        """Add spot to both free_spots list and spot_lookup hash"""
        self.free_spots.add(spot)
        self.spot_lookup[spot.spot_id] = spot
    
    def add_car(self, car):
        """Add car to car_lookup hash"""
        self.car_lookup[car.plate_id] = car
    
    def get_closest_free_spot(self):
        """Return closest free spot (first element) or None if empty"""
        return self.free_spots[0] if self.free_spots else None
    
    def get_time_saved(self):
        """Get the time saved based on the distance difference between the farthest and closest free spots."""
        if len(self.free_spots) < 2:
            return 0
        else:
            return self.free_spots[-1].distance_from_entry - self.free_spots[0].distance_from_entry
        
    
    def remove_spot_from_free(self, spot):
        """Remove spot from free_spots list"""
        # allow passing either Spot object or spot_id string
        if isinstance(spot, str):
            s = self.spot_lookup.get(spot)
            if s and s in self.free_spots:
                self.free_spots.remove(s)
            return
        if spot in self.free_spots:
            self.free_spots.remove(spot)

    def remove_spot_by_id(self, spot_id: str):
        """Remove a spot from free_spots by its spot_id string."""
        spot = self.spot_lookup.get(spot_id)
        if spot:
            try:
                self.remove_spot_from_free(spot)
            except Exception:
                pass
    
    def add_spot_to_free(self, spot):
        """Add spot back to free_spots list"""
        if spot not in self.free_spots:
            self.free_spots.add(spot)
    
    # Simple lookups
    def get_spot(self, spot_id):
        """Get spot by spot_id from hash table"""
        return self.spot_lookup.get(spot_id)
    
    def get_car(self, car_id):
        """Get car by car_id from hash table"""
        return self.car_lookup.get(car_id)
    
    # Pairing operations
    def set_waiting_pair(self, car_id, spot_id):
        """Set current waiting pair"""
        self.waiting_pair = {"car_id": car_id, "spot_id": spot_id}
    
    def get_waiting_pair(self):
        """Get current waiting pair"""
        return self.waiting_pair
    
    def clear_waiting_pair(self):
        """Clear current waiting pair"""
        self.waiting_pair = None
    
    # Occupied spots tracking methods
    def add_occupied_spot(self, spot_id, car_id):
        """Add a spot to occupied hash table - O(1)"""
        self.occupied_spots_with_cars[spot_id] = car_id
    
    def remove_occupied_spot(self, spot_id):
        """Remove a spot from occupied hash table - O(1)"""
        self.occupied_spots_with_cars.pop(spot_id, None)
    
    def get_occupied_spots(self):
        """Get list of occupied spot tuples [(spot_id, car_id), ...]"""
        return list(self.occupied_spots_with_cars.items())
    
    def get_random_occupied_spot(self):
        """Get a random occupied spot tuple (spot_id, car_id) or None if empty"""
        return random.choice(list(self.occupied_spots_with_cars.items())) if self.occupied_spots_with_cars else None

    # Grid/BFS utilities
    def _parse_spot_coords(self, spot_id: str) -> Tuple[int, int]:
        """Parse spot_id formatted as '(row,col)' or 'row,col' into (row, col) ints."""
        s = spot_id.strip()
        if s.startswith('(') and s.endswith(')'):
            s = s[1:-1]
        parts = s.split(',')
        return int(parts[0]), int(parts[1])

    def _format_coord_tuple(self, row: int, col: int, with_paren: bool = False) -> str:
        if with_paren:
            return f"({row},{col})"
        return f"{row},{col}"

    def find_closest(self, gate_row: int = 0, gate_col: int = 2) -> Optional[Tuple[int, int]]:
        """Find closest FREE spot to the gate using BFS on the grid of spots.

        Returns (row, col) or None if no free spots. The return shape matches the
        rest of the code and the UI which uses 'row,col' string keys.
        """
        # Build set of free positions from spot_lookup
        free_positions = set()
        for sid, spot in self.spot_lookup.items():
            if getattr(spot, 'status', None) == 'FREE':
                row, col = self._parse_spot_coords(sid)
                free_positions.add((row, col))

        if not free_positions:
            return None

        # BFS from gate
        q = deque()
        start = (gate_row, gate_col)
        q.append(start)
        seen = {start}

        # neighbor deltas: up/down/left/right
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        while q:
            r, c = q.popleft()
            if (r, c) in free_positions:
                # return (row, col) to match the 'row,col' key format used by the DB
                return (r, c)
            # Collect potential neighbors, then sort deterministically by (col, row)
            neighbors = []
            for dr, dc in deltas:
                nr, nc = r + dr, c + dc
                if (nr, nc) in seen:
                    continue
                # only explore coordinates that exist in the grid (either free or occupied)
                if (nr, nc) in free_positions or any((nr, nc) == self._parse_spot_coords(sid) for sid in self.spot_lookup):
                    neighbors.append((nr, nc))

            # sort neighbors so tie-breaker prefers lower column, then lower row
            neighbors.sort(key=lambda rc: (rc[1], rc[0]))
            for nr, nc in neighbors:
                seen.add((nr, nc))
                q.append((nr, nc))

        return None

    def allocate_closest_spot(self, car_id: str, gate_row: int = 0, gate_col: int = 2) -> Optional[str]:
        """Allocate the closest free spot (BFS) for car_id.

        Returns the allocated spot id as 'row,col' string (no parentheses) or None.
        Also sets waiting_pair and removes spot from free_spots.
        """
        coord = self.find_closest(gate_row, gate_col)
        if coord is None:
            return None
        # find_closest now returns (row, col)
        row, col = coord
        # our spot_lookup keys use '(row,col)'
        key_paren = self._format_coord_tuple(row, col, with_paren=True)
        key_plain = self._format_coord_tuple(row, col, with_paren=False)
        spot = self.spot_lookup.get(key_paren) or self.spot_lookup.get(f"({row},{col})")
        if spot is None:
            # try the plain key
            spot = self.spot_lookup.get(key_plain)
        if spot is None:
            return None

        # remove from free_spots if present and mark as waiting
        try:
            # mark in-memory
            spot.status = 'WAITING'
            self.remove_spot_from_free(spot)
        except Exception:
            pass

        # set waiting pair and return plain key 'row,col'
        self.set_waiting_pair(car_id, key_plain)
        print(f"[ParkingLot] Allocated spot {key_plain} to car {car_id}; free_spots_count={len(self.free_spots)}")
        return key_plain