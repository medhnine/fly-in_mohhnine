class Zone:
    def __init__(self, name: str, x: int, y: int, color: str, zone_type: str, max_drones: int | float):
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        self.zone_type = zone_type
        self.max_drones = max_drones
        self.neighbors = []
        self.drones_in = 0

    @property
    def cost(self) -> int:
        if self.zone_type == "restricted":
            return 2
        return 1

    def set_default(self):
        if self.color is None:
            self.color = "yellow"
        if self.max_drones is None:
            self.max_drones = 1
        if self.zone_type is None:
            self.zone_type = "normal"
    
    def has_plsce(self):
        if self.drones_in < self.max_drones:
            return True
        return False

class Drone:
    def __init__(self, id, path):
        self.id = id
        self.path = path
        self.step = 0

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
        self.nb_drones = nb_drones
        self.zones : dict[str, Zone] = {}
        self.start: Zone | None = None
        self.end: Zone | None = None
        self.connection : dict[tuple[str, str], Connection] = {}

    def add_zone(self, zone):
        if zone.name in self.zones:
            raise ValueError("duplicated zone name")
        else:
            self.zones[zone.name] = zone

    def get_zone(self, z_name):
        return self.zones.get(z_name)

    def connect(self, name1, name2, max_link_capacity):
        zone1 = self.zones[name1]
        zone2 = self.zones[name2]
        zone1.neighbors.append(zone2)
        zone2.neighbors.append(zone1)
        items : tuple[str, str] = (name1, name2)
        self.connection[tuple(sorted(items))] = Connection(zone1, zone2, max_link_capacity)

    
    def assign_paths(self, paths):
        drones : list["Drone"] = []
        store = {}
        id = 1
        for index, path in enumerate(paths):
            store[index] = [len(path) - 1, 0]
        while(id <= self.nb_drones):
            small = float("inf")
            chosen = 0
            for key, value in store.items():
                if small > value[0] + value[1]:
                    small = value[0] + value[1]
                    chosen = key
            drone = Drone(id, paths[chosen])
            store[chosen][1] += 1
            drones.append(drone)
            id += 1
        print(store)
        return drones

    def is_all_arrived(self, drones):
        for drone in drones:
            if not drone.arrived:
                return False
        return True

    def get_connection(self, zone1, zone2):
        return self.connection[tuple(sorted([zone1.name, zone2.name]))]
    
    # def highest_step(self, drones):
    #     high = 0
    #     drone_id = 1
    #     for drone in drones:
    #         if drone.step > high and not drone.arrived:
    #             high = drone.step
    #             drone_id = drone.id
    #     return drone_id
    
    # def lowest_step(self, drones):
    #     lowest = float(inf)
    #     for drone in drones:
    #         if drone.step < lowest and not drone.arrived:
    #             lowest = drone.step
    #     return lowest



    def find_path(self, blocked : set["Zone"] | None):
        if self.start is None or self.end is None:
            raise ValueError("start or end missing")
        dist: dict["Zone", float] = {}
        visited: set["Zone"] = set()
        parent: dict["Zone", "Zone | None"] = {}
        for zone in self.zones.values():
            dist[zone] = float("inf")
            parent[zone] = None
        dist[self.start] = 0
        while True:
            lowest = float("inf")
            current = None
            for cheap in self.zones.values():
                if cheap not in visited and cheap not in blocked and dist[cheap] < lowest:
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
                    new_cost = dist[current] + n.cost
                    if new_cost < dist[n]:
                        dist[n] = new_cost
                        parent[n] = current

class Connection:
    def __init__(self, zone1, zone2, max_link_capacity):
        self.zone1 = zone1
        self.zone2 = zone2
        self.max_link_capacity = max_link_capacity
        self.usage = 0






















        # dist[self.start] = 0
        # current = None
        # best = float("inf")
        # parent[self.start] = None
        # while True:
        #     for cheap in self.zones.values():
        #         if cheap not in visited and dist[cheap] < best:
        #             best = dist[cheap]
        #             current = cheap
        #     if current is None:
        #         return None
        #     print(f"cheap {current.name}")
        #     neighbors = current.neighbors
        #     visited.add(current)
        #     for n in neighbors:
        #         if n not in visited:
        #             print(f"neighbor {n.name}")
        #             new_cost = dist[current] + n.cost
        #             print(f"new cost {new_cost}")
        #             print(f"dist {dist[n]}")
        #             if new_cost < dist[n]:
        #                 dist[n] = new_cost
        #                 parent[n] = current
        #                 if parent[current] is not None:
        #                     print(f"in {parent[current].name} came from {parent[n].name}")
        #         if n.name == self.end.name:
        #             # parent[self.end] = n
        #             print(f"in {parent[current].name} came from {parent[self.end].name}")
        #             x = self.end
        #             path = []
        #             # while parent[x] != None:
        #             #     x = parent[x]
        #             #     print(x.name)
        #             #     path.append(x)
        #             return path[:-1]

            

def main():
    from parsing import Parse
    obj = Parse('/home/mohhnine/Desktop/fly-in/maps/medium/01_dead_end_trap.txt')
    graph = Graph(2)
    zones = obj.parse(graph)
    s = "#  start_hub: start 0 0 [color=green]"
    s = s.strip()
    print(s)
    # print('fly-in')

if __name__ == '__main__':
    main()