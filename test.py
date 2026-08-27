from main import Graph, Zone

class Parse:
    def __init__(self, path):
        self.path = path
        self.zones_name = []
        self.connection = []

    def read_file(self):
        try:
            with open(self.path, "r") as f:
                result = f.readlines()
        except FileNotFoundError as e:
            print(f"file not found {e}")
        except PermissionError as e:
            print(f"Permission diened {e}")
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
                    else:
                        raise ValueError("unvlaid meta data for zone type")
                elif res[0] == "max_drones":
                    try:
                        if info["max_drones"] is not None:
                            raise ValueError("duplicated max_drones in meta data")
                        info["max_drones"] = int(res[1])
                    except ValueError:
                        raise ValueError("unvlaid meta data max_drones")
                elif res[0] == "color":
                    if info["color"] is not None:
                            raise ValueError("duplicated color in meta data")
                    info["color"] = res[1]
            else:
                raise ValueError("unvlaid meta data")
        return True

    def handle_drones(self, data : str) -> Graph:
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
        graph = Graph(nb_drones)
        return graph

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

        try:
            x = int(values[1])
            y = int(values[2])
            info["x"] = x
            info["y"] = y
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

    def connection_handler(self, data, count):
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
        elif zones[0] == zones[1] or zones[0] not in self.zones_name or zones[1].split(' ', 1)[0] not in self.zones_name:
            raise ValueError("unvalid connection same connection or zone are not known")
        con_name = zones[0] + ' ' + zones[1]
        if con_name in self.connection:
            raise ValueError("unvlaid connection")
        self.connection.append(con_name)
        if len(connection) <= 2:
            meta = connection[0].split(' ',1)
            if len(meta) == 2:
                if '[' in meta[1]:
                    self.connection_meta(meta[1])

    def connection_meta(self, meta_d):
        data = meta_d[1:len(meta_d) - 1]
        if not data:
            return
        result = data.split('=')
        if len(result) != 2 or result[0] != "max_link_capacity" or result[1] == "":
            raise ValueError("unvlaid meta data for connection")
        value = int(result[1])
        if value <= 0:
            raise ValueError("unvlaid max_link_capacity number for connection")

    def parse(self, graph):
        zones = []
        data = self.read_file()
        filtered_data : list[str] = []
        count = 0
        # zone = Zone()
        start_hub = False
        end_hub = False
        filtered_data = [line.strip() for line in data if not (line.startswith('#') or line.startswith('\n') or line == '')]
        for line in filtered_data:
            if line.startswith("nb_drones:"):
                graph = self.handle_drones(line)
            elif line.startswith("start_hub:"):
                if start_hub == True:
                    raise ValueError("duplicated zone start_hub")
                hub_info = (self.hub_manger(graph, line))
                graph.start = Zone(hub_info["name"], hub_info["x"], hub_info["y"], hub_info["color"], hub_info["zone_type"], hub_info["max_drones"])
                start_hub = True
                count += 1
            elif line.startswith("hub:"):
                hub_info = self.hub_manger(graph, line)
                zones.append(Zone(hub_info["name"], hub_info["x"], hub_info["y"], hub_info["color"], hub_info["zone_type"], hub_info["max_drones"]))
                count += 1
            elif line.startswith("end_hub:"):
                if end_hub == True:
                    raise ValueError("duplicated zone end_hub")
                hub_info = self.hub_manger(graph, line)
                graph.end = Zone(hub_info["name"], hub_info["x"], hub_info["y"], hub_info["color"], hub_info["zone_type"], hub_info["max_drones"])
                end_hub = True
                count += 1
            elif line.startswith("connection:"):
                self.connection_handler(line, count)
            else:
                raise ValueError("unvalid data line")
        if not start_hub or not end_hub:
            raise ValueError("start_hub or end_hub are not present")
        return zones

def main():
    try:
        obj = Parse('/home/mohhnine/Desktop/fly-in/maps/easy/01_linear_path.txt')
        graph = Graph(2)
        zones = obj.parse(graph)
        print(f"zones obj: {zones}")
        dic = {}
        for zone in zones:
            print(f"zones neighbors :{zone.neighbors}")
            print(zone.name)
            dic[zone.name] = zone
        print(dic)
        # meta_d = "[color]"
        # data = meta_d[1:len(meta_d) - 1]
        # print(data)
    except Exception as e:
        print(f"opps {e}")
main()