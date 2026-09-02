from main import Graph, Zone, Drone

class Parse:
    def __init__(self, path):
        self.path = path
        self.zones_name = []

    def read_file(self):
        try:
            with open(self.path, "r") as f:
                result = f.readlines()
            data_file = ""
            for line in result:
                res = "".join(line)
                data_file += res + '\n'
            with open("/home/mohhnine/Desktop/fly-in/vis_data.txt", "w") as file:
                file.write(data_file)
        except FileNotFoundError as e:
            raise ValueError(f"file not found {e}")
        except PermissionError as e:
            raise ValueError(f"Permission diened {e}")
        return result

    def valid_meta(self, meta_d, info):
        info["zone_type"] = None
        info["color"] = None
        info["max_drones"] = None
        if len(meta_d) <= 2:
            raise ValueError("unvlaid meta data")
        if meta_d[0] != '[' or meta_d[len(meta_d) - 1] != ']':
            raise ValueError("unvlaid meta data")
        data = meta_d[1:len(meta_d) - 1]
        data.strip()
        result = data.split(' ')
        if len(result) > 3:
            raise ValueError("unvlaid meta data")
        for meta in result:
            res = meta.split('=')
            if res[0] in ['zone', 'color', 'max_drones']:
                if res[0] == "zone":
                    if res[1] in "normal priority restricted blocked":
                        if info["zone_type"]:
                            raise ValueError("duplicated zone in meta data")
                        info["zone_type"] = res[1]
                        print(f"{res[0]} = {info["zone_type"]}")
                    else:
                        raise ValueError("unvlaid meta data for zone type")
                elif res[0] == "max_drones":
                    try:
                        if info["max_drones"] is not None:
                            raise ValueError("duplicated max_drones in meta data")
                        info["max_drones"] = int(res[1])
                        print(f"{res[0]} = {info["max_drones"]}")
                    except ValueError:
                        raise ValueError("unvlaid meta data max_drones")
                elif res[0] == "color":
                    if info["color"] is not None:
                            raise ValueError("duplicated color in meta data")
                    info["color"] = res[1]
                    print(f"{res[0]} = {info["color"]}\n")
            else:
                raise ValueError("unvlaid meta data")
        return True

    def handle_drones(self, data : str, graph : Graph) -> Graph:
        result = data.split(':')
        if len(result) != 2:
            raise ValueError("enter valid argumnet 'nb_drones'!")
        if result[0] != 'nb_drones':
            raise ValueError("enter valid argumnet 'nb_drones'!")
        try:
            nb_drones = int(result[1])
        except ValueError:
            raise ValueError("enter valid nb_drones!")
        if nb_drones <= 0:
            raise ValueError("enter valid nb_drones >= 1 !")
        graph.nb_drones = nb_drones

    def hub_manger(self, graph : Graph, data : str):
        info = {}
        if graph.nb_drones == None:
            raise ValueError("valid nb_drones is required as first line info")
        result : list[str] = data.split(':', 1)
        if len(result) != 2 or (result[0] != "start_hub" and result[0] != "hub" and result[0] != "end_hub"):
            raise ValueError("hub not valid")
        result[1] = result[1].strip()
        values = result[1].split(' ')
        if len(values) < 3:
            raise ValueError("hub info must at least have: hub x y")
        if values[0] in self.zones_name:
            raise ValueError("duplicated zone name")
        self.zones_name.append(values[0])
        info["name"] = values[0]
        print(f"zone name: {values[0]}")

        try:
            x = int(values[1])
            y = int(values[2])
            info["x"] = x
            info["y"] = y
            print(f"x, y = {x} {y}")
        except ValueError:
            raise ValueError("x, y cordinate not valid")
        if len(values) > 3:
            store = ''
            data = [x for x in values if x != '']
            for i in range(3, len(data)):
                if i > 3:
                    store += ' ' + data[i].strip()
                else:
                    store += data[i]
            if '[' in data[3]:
                self.valid_meta(store, info)
            else:
                raise ValueError("unvlaid metadata")
        else:
            info["zone_type"] = None
            info["color"] = None
            info["max_drones"] = None
        return info

    def connection_handler(self, data, count, graph: Graph):
        if count < 2:
            raise ValueError("unvalid structure can not make connection add hubs")
        result = data.split(':', 1)
        if len(result) != 2 or result[1] == "":
            raise ValueError("error unvalid connection")
        connection = result[1].strip()
        connection = connection.split(':',1)
        if len(connection) < 1 or connection[0] == "":
            raise ValueError("error unvalid connection")
        elif '-' not in connection[0]:
            raise ValueError("error unvalid connection")
        zones = connection[0].split('-', 1)
        if len(zones) != 2 or zones[0] == "" or zones[1] == "":
            raise ValueError("error unvalid connection")
        zone_name1 = zones[0]
        zone_name2 = zones[1].split(' ', 1)[0]
        if zone_name1 == zone_name2 or zone_name1 not in self.zones_name or zone_name2 not in self.zones_name:
            raise ValueError("unvalid connection same connection or zone are not known")
        zone1 = graph.get_zone(zone_name1)
        zone2 = graph.get_zone(zone_name2)
        if zone2 in zone1.neighbors:
            raise ValueError(f"error duplicated concetion: ({zone_name1}->{zone_name2})")
        if len(connection) <= 2:
            meta = connection[0].split(' ',1)
            if len(meta) == 2:
                if '[' in meta[1]:
                    max_link_capacity = self.connection_meta(meta[1])
                    graph.connect(zone_name1, zone_name2, max_link_capacity)
                else:
                    raise ValueError("error in connectin meta data")
            else:
                graph.connect(zone_name1, zone_name2, 1)
            



    def connection_meta(self, meta_d):
        data = meta_d[1:len(meta_d) - 1]
        if not data:
            raise ValueError("unvlid metadata/empty")
        result = data.split('=')
        if len(result) != 2 or result[0] != "max_link_capacity" or result[1] == "":
            raise ValueError("unvlaid meta data for connection")
        value = int(result[1])
        if value <= 0:
            raise ValueError("unvlaid max_link_capacity number for connection")
        return value

    def parse(self, graph: Graph):
        zones = []
        data = self.read_file()
        filtered_data : list[str] = []
        count = 0
        start_hub = False
        end_hub = False
        filtered_data = [line.strip() for line in data if not (line.startswith('#') or line.startswith('\n') or line == '')]
        for line in filtered_data:
            if line.startswith("nb_drones:"):
                self.handle_drones(line, graph)
            elif line.startswith("start_hub:"):
                if start_hub == True:
                    raise ValueError("duplicated zone start_hub")
                hub_info = (self.hub_manger(graph, line))
                hub = Zone(hub_info["name"], hub_info["x"], hub_info["y"], hub_info["color"], hub_info["zone_type"], hub_info["max_drones"])
                hub.set_default()
                hub.drones_in = graph.nb_drones
                zones.append(hub)
                graph.start = hub
                graph.add_zone(hub)
                start_hub = True
                count += 1
            elif line.startswith("hub:"):
                hub_info = self.hub_manger(graph, line)
                hub = Zone(hub_info["name"], hub_info["x"], hub_info["y"], hub_info["color"], hub_info["zone_type"], hub_info["max_drones"])
                hub.set_default()
                graph.add_zone(hub)
                zones.append(hub)
                count += 1
            elif line.startswith("end_hub:"):
                if end_hub == True:
                    raise ValueError("duplicated zone end_hub")
                hub_info = self.hub_manger(graph, line)
                hub = Zone(hub_info["name"], hub_info["x"], hub_info["y"], hub_info["color"], hub_info["zone_type"], hub_info["max_drones"])
                hub.set_default()
                zones.append(hub)
                graph.end = hub
                graph.add_zone(hub)
                end_hub = True
                count += 1
            elif line.startswith("connection:"):
                self.connection_handler(line, count, graph)
            else:
                raise ValueError("unvalid data line")
        if not start_hub or not end_hub:
            raise ValueError("start_hub or end_hub are not present")
        return zones

def main():
    # try:
        obj = Parse('/home/mohhnine/Desktop/fly-in/maps/challenger/01_the_impossible_dream.txt')
        graph = Graph(2)
        zones = obj.parse(graph)
        dic: dict = {}
        res = []
        blocked: set["Zone"] = set()
        paths = []
        max_paths = 2
        while res is not None:
            res = graph.find_path(blocked)
            if res is None:
                break
            paths.append(res.copy())
            block = res[1:-1]
            for zone in block:
                blocked.add(zone)
            if max_paths == 1:
                break
            max_paths -=1
            

        # for z in zones:
        #     print(f"the number drones in zone {z.name} is: {z.drones_in}")
        # print(len(paths))

        # for p in paths:
        #     print("path:")
        #     for z in p:
        #         print(f"zone = {z.name} priority is {z.zone_type}")
        drones = graph.assign_paths(paths)
        count = 1
        graph.end.max_drones = float("inf")
        data = ""
        while not graph.is_all_arrived(drones):
            for key, value in graph.connection.items():
                value.usage = 0
            for drone in drones:
                if drone.in_connection is not None:
                    drone.in_connection.usage += 1
            dr_left = [d for d in drones if d.arrived is False]
            sr_drones = sorted(dr_left, key=lambda d: d.step, reverse=True)
            print(f"turn {count}\n")
            moves = []
            moved = False
            for drone in sr_drones:
                current_zone = drone.current_zone
                next_zone = drone.next_zone
                if next_zone is not None:
                    connection = graph.get_connection(current_zone, next_zone)
                    if drone.in_connection is not None:
                        next_zone.drones_in += 1
                        next_zone.reserved -= 1
                        drone.step += 1
                        drone.in_connection = None
                        moves.append(f"D{drone.id}-{next_zone.name}")
                        moved = True
                        continue

                    if next_zone.zone_type == "restricted":
                        if next_zone.has_place and connection.check_capacity:
                            drone.in_connection = connection
                            moves.append(f"D{drone.id}-{current_zone.name}-{next_zone.name}")
                            connection.usage += 1
                            current_zone.drones_in -= 1
                            next_zone.reserved += 1
                            moved = True
                    
                    elif next_zone.has_place and connection.check_capacity:
                        next_zone.drones_in += 1
                        current_zone.drones_in -= 1
                        moves.append(f"D{drone.id}-{next_zone.name}")
                        connection.usage += 1
                        moved =  True
                        drone.step += 1

            if moved is False:
                print("deadlock")
                return
            print(" ".join(moves))
            res = " ".join(moves)
            data += res + '\n'
            count += 1
        # for z in zones:
        #     print(f"the number drones in zone {z.name} is: {z.drones_in}")
        with open("/home/mohhnine/Desktop/fly-in/vis_data.txt", "a") as file:
            file.write(data)

    # except Exception as e:
    #     print(f"opps {e}")
main()
