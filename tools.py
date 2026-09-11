"""Core graph, zone, drone, and connection models for Fly-in."""

from __future__ import annotations

from typing import Any, cast


class Zone:
    """Represent a zone in the drone-routing graph."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        color: str | None,
        zone_type: str | None,
        max_drones: int | float | None,
    ) -> None:
        """Initialize a zone.

        Args:
            name: Zone name.
            x: Zone x-coordinate.
            y: Zone y-coordinate.
            color: Optional visualization color.
            zone_type: Optional zone type.
            max_drones: Maximum number of drones allowed in the zone.
        """
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        self.zone_type = zone_type
        self.max_drones = max_drones
        self.neighbors: list[Zone] = []
        self.drones_in = 0
        self.reserved = 0

    @property
    def cost(self) -> float:
        """Return the movement cost for entering this zone."""
        if self.zone_type == "restricted":
            return 2.0
        return 1.0

    def set_default(self) -> None:
        """Apply default values for missing zone metadata."""
        if self.max_drones is None:
            self.max_drones = 1
        if self.zone_type is None:
            self.zone_type = "normal"

    @property
    def has_place(self) -> bool:
        """Return whether the zone has room for another drone."""
        max_drones = cast(int | float, self.max_drones)
        if self.drones_in + self.reserved < max_drones:
            return True
        return False


class Drone:
    """Represent a drone and its progress along an assigned path."""

    def __init__(self, id: int, path: list[Zone]) -> None:
        """Initialize a drone.

        Args:
            id: Unique drone identifier.
            path: Ordered list of zones assigned to the drone.
        """
        self.id = id
        self.path = path
        self.step = 0
        self.in_connection: Connection | None = None

    @property
    def arrived(self) -> bool:
        """Return whether the drone has reached the final zone."""
        if self.step == len(self.path) - 1:
            return True
        return False

    @property
    def current_zone(self) -> Zone:
        """Return the zone currently occupied by the drone."""
        return self.path[self.step]

    @property
    def next_zone(self) -> Zone | None:
        """Return the next zone in the path, if one exists."""
        if self.arrived:
            return None
        return self.path[self.step + 1]


class Graph:
    """Represent the zone graph and provide pathfinding operations."""

    def __init__(self) -> None:
        """Initialize an empty graph.

        Args:
            nb_drones: Initial drone-count argument used by the caller.
        """
        self.nb_drones: int | None = None
        self.zones: dict[str, Zone] = {}
        self.start: Zone | None = None
        self.end: Zone | None = None
        self.connection: dict[tuple[str, str], Connection] = {}

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph.

        Args:
            zone: Zone to add.

        Raises:
            ValueError: If the zone name already exists.
        """
        if zone.name in self.zones:
            raise ValueError("duplicated zone name")
        else:
            self.zones[zone.name] = zone

    def get_zone(self, z_name: str) -> Zone:
        """Return a zone by name.

        Args:
            z_name: Name of the requested zone.

        Returns:
            The matching zone.
        """
        return cast(Zone, self.zones.get(z_name))

    def connect(
        self,
        name1: str,
        name2: str,
        max_link_capacity: int,
    ) -> None:
        """Create a bidirectional connection between two zones.

        Args:
            name1: Name of the first zone.
            name2: Name of the second zone.
            max_link_capacity: Maximum simultaneous connection usage.
        """
        zone1 = self.zones[name1]
        zone2 = self.zones[name2]
        zone1.neighbors.append(zone2)
        zone2.neighbors.append(zone1)
        items = sorted((name1, name2))
        z_names: tuple[str, str] = (items[0], items[1])
        self.connection[z_names] = Connection(
            zone1, zone2, max_link_capacity
        )

    def mutiple_path(self) -> list[list[Zone]]:
        """Find up to two paths from the start zone to the end zone.

        Returns:
            The discovered paths.

        Raises:
            ValueError: If no route from start to end can be found.
        """
        in_path: set[Zone] = set()
        paths: list[list[Zone]] = []
        path: list[Zone] | None = []
        max_paths = 2
        while path is not None:
            path = self.find_path(in_path)
            if path is None:
                break
            paths.append(path.copy())
            block = path[1:-1]
            for zone in block:
                in_path.add(zone)
            if max_paths == 1:
                break
            max_paths -= 1
        if len(paths) <= 0:
            raise ValueError("There is no path for this map")
        return paths

    def assign_paths(self, paths: list[list[Zone]]) -> list[Drone]:
        """Assign drones across the available paths.

        Args:
            paths: Candidate paths from start to end.

        Returns:
            Drones initialized with their assigned paths.
        """
        drones: list[Drone] = []
        store: dict[int, list[float]] = {}
        id = 1
        for index, path in enumerate(paths):
            store[index] = [sum(zone.cost for zone in path[1:]), 0]
        nb_drones = cast(int, self.nb_drones)
        while id <= nb_drones:
            small = float("inf")
            chosen = 0
            for key, value in store.items():
                if small > value[0] + value[1]:
                    small = value[0] + value[1]
                    chosen = key
            if chosen <= len(paths) - 1:
                drone = Drone(id, paths[chosen])
                store[chosen][1] += 1
                drones.append(drone)
            id += 1
        return drones

    def is_all_arrived(self, drones: list[Drone]) -> bool:
        """Return whether every drone has reached its destination.

        Args:
            drones: Drones participating in the simulation.
        """
        for drone in drones:
            if not drone.arrived:
                return False
        return True

    def get_connection(self, zone1: Zone, zone2: Zone) -> Connection:
        """Return the connection shared by two zones.

        Args:
            zone1: First endpoint zone.
            zone2: Second endpoint zone.
        """
        items = sorted((zone1.name, zone2.name))
        z_names: tuple[str, str] = (items[0], items[1])
        return self.connection[z_names]

    def find_path(self, in_path: set[Zone] | None) -> list[Zone] | None:
        """Find a weighted path from start to end.

        Args:
            in_path: Zones already used by previously selected paths.

        Returns:
            A path from start to end, or None when no path exists.

        Raises:
            ValueError: If the graph has no start or end zone.
        """
        if self.start is None or self.end is None:
            raise ValueError("start or end missing")

        active_path = cast(set[Zone], in_path)
        dist: dict[Zone, tuple[float, int]] = {}
        visited: set[Zone] = set()
        parent: dict[Zone, Zone | None] = {}
        blocked: set[Zone] = {
            zone
            for zone in self.zones.values()
            if zone.zone_type == "blocked"
        }
        for zone in self.zones.values():
            dist[zone] = (float("inf"), 0)
            parent[zone] = None
        dist[self.start] = (0, 0)
        while True:
            lowest: tuple[float, int] = (float("inf"), 0)
            current: Zone | None = None
            for cheap in self.zones.values():
                if cheap not in visited and cheap not in blocked:
                    if dist[cheap] < lowest:
                        lowest = dist[cheap]
                        current = cheap

            if current is None:
                return None
            if current is self.end:
                path: list[Zone] = []
                while current is not None:
                    path.append(current)
                    current = parent[current]
                return path[::-1]
            neighbors = current.neighbors
            visited.add(current)
            for n in neighbors:
                if n not in visited and n not in blocked:
                    new_cost = dist[current][0] + n.cost
                    new_priority = dist[current][1]
                    if n.zone_type == "priority":
                        new_priority -= 1
                    if current in active_path:
                        new_cost += 1
                    new_dist = (new_cost, new_priority)
                    if new_dist < dist[n]:
                        dist[n] = new_dist
                        parent[n] = current

    def sort_paths_priority(self, paths: Any) -> Any:
        """Sort paths using the existing priority-count implementation.

        Args:
            paths: Paths to process.

        Returns:
            The value produced by the existing sorting implementation.
        """
        new_path: Any = []
        for path in paths:
            count = 0
            for zone in path:
                if zone.zone_type == "priority":
                    count += 1
            p = {path: count}
            new_path.append(p)
        result: Any = sorted(new_path, key=lambda p: new_path[p])
        print(result)
        paths = []
        for key in result.items():
            paths.append(key)
        return paths


class Connection:
    """Represent a capacity-limited connection between two zones."""

    def __init__(
        self,
        zone1: Zone,
        zone2: Zone,
        max_link_capacity: int,
    ) -> None:
        """Initialize a connection.

        Args:
            zone1: First endpoint zone.
            zone2: Second endpoint zone.
            max_link_capacity: Maximum simultaneous connection usage.
        """
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity
        self.usage = 0

    @property
    def check_capacity(self) -> bool:
        """Return whether the connection has available capacity."""
        if self.usage < self.max_link_capacity:
            return True
        return False
