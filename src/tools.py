class Zone:
    def __init__(
        self, name: str, x: int, y: int,
        color: str, zone_type: str, max_drones: int | float
    ):
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        self.zone_type = zone_type
        self.max_drones = max_drones
        self.neighbors = []
        self.drones_in = 0
        self.reserved = 0

    @property
    def cost(self) -> float:
        if self.zone_type == "restricted":
            return 2.0
        return 1.0

    def set_default(self):
        if self.color is None:
            self.color = "yellow"
        if self.max_drones is None:
            self.max_drones = 1
        if self.zone_type is None:
            self.zone_type = "normal"

    @property
    def has_place(self):
        if self.drones_in + self.reserved < self.max_drones:
            return True
        return False


class Drone:
    def __init__(self, id, path):
        self.id = id
        self.path = path
        self.step = 0
        self.in_connection: Connection | None = None

    @property
    def arrived(self):
        if self.step == len(self.path) - 1:
            return True
        return False

    @property
    def current_zone(self):
        return self.path[self.step]

    @property
    def next_zone(self):
        if self.arrived:
            return None
        return self.path[self.step + 1]


class Graph:
    def __init__(self, nb_drones: int):
        self.nb_drones = None
        self.zones: dict[str, Zone] = {}
        self.start: Zone | None = None
        self.end: Zone | None = None
        self.connection: dict[tuple[str, str], Connection] = {}

    def add_zone(self, zone):
        if zone.name in self.zones:
            raise ValueError("duplicated zone name")
        else:
            self.zones[zone.name] = zone

    def get_zone(self, z_name):
        return self.zones.get(z_name)

    def connect(
        self, name1, name2, max_link_capacity
    ):
        zone1 = self.zones[name1]
        zone2 = self.zones[name2]
        zone1.neighbors.append(zone2)
        zone2.neighbors.append(zone1)
        items: tuple[str, str] = (name1, name2)
        self.connection[tuple(sorted(items))] = Connection(
            zone1, zone2, max_link_capacity
        )

    def mutiple_path(self):
        in_path: set["Zone"] = set()
        paths = []
        path = []
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
        return paths

    def assign_paths(self, paths):
        drones: list["Drone"] = []
        store = {}
        id = 1
        for index, path in enumerate(paths):
            store[index] = [sum(zone.cost for zone in path[1:]), 0]
        while (id <= self.nb_drones):
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

    def is_all_arrived(self, drones):
        for drone in drones:
            if not drone.arrived:
                return False
        return True

    def get_connection(self, zone1, zone2):
        return self.connection[tuple(sorted([zone1.name, zone2.name]))]

    def find_path(self, in_path: set["Zone"] | None):
        if self.start is None or self.end is None:
            raise ValueError("start or end missing")

        dist: dict["Zone", tuple[float, int]] = {}
        visited: set["Zone"] = set()
        parent: dict["Zone", "Zone | None"] = {}
        blocked: set["Zone"] = {
            zone for zone in self.zones.values() if zone.zone_type == "blocked"
        }
        for zone in self.zones.values():
            dist[zone] = (float("inf"), 0)
            parent[zone] = None
        dist[self.start] = (0, 0)
        while True:
            lowest: tuple = (float("inf"), 0)
            current = None
            for cheap in self.zones.values():
                if cheap not in visited and cheap not in blocked:
                    if dist[cheap] < lowest:
                        lowest = dist[cheap]
                        current = cheap

            if current is None:
                return None
            if current is self.end:
                path = []
                while current is not None:
                    path.append(current)
                    current = parent[current]
                return path[::-1]
            neighbors = current.neighbors
            visited.add(current)
            for n in neighbors:
                if n not in visited and n not in blocked:
                    cost_vlaue = n.cost
                    new_cost = dist[current][0] + cost_vlaue
                    new_priority = dist[current][1]
                    if n.zone_type == "priority":
                        new_priority -= 1
                    if current in in_path:
                        new_cost += 1
                    new_dist = (new_cost, new_priority)
                    if new_dist < dist[n]:
                        dist[n] = new_dist
                        parent[n] = current

    def sort_paths_priority(self, paths):
        new_path: list[dict[list, int]] = []
        for path in paths:
            count = 0
            for zone in path:
                if zone.zone_type == "priority":
                    count += 1
            p = {path: count}
            new_path.append(p)
        result = sorted(new_path, key=lambda p: new_path[p])
        print(result)
        paths = []
        for key in result.items():
            paths.append(key)
        return paths


class Connection:
    def __init__(self, zone1, zone2, max_link_capacity):
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity
        self.usage = 0

    @property
    def check_capacity(self):
        if self.usage < self.max_link_capacity:
            return True
        return False
