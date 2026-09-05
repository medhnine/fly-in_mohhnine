from tools import Graph, Zone

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
                data_file += res + "\n"
            with open(
                "/home/mohhnine/Desktop/fly-in/src/vis_data.txt",
                "w",
            ) as file:
                file.write(data_file)
        except FileNotFoundError as e:
            raise ValueError(f"file not found {e}")
        except PermissionError as e:
            raise ValueError(f"Permission diened {e}")
        return result

    def valid_meta(self, meta_d, info, nb_line):
        info["zone_type"] = None
        info["color"] = None
        info["max_drones"] = None
        if len(meta_d) <= 2:
            raise ValueError(
                f"error in line {nb_line}: unvlaid meta data"
            )
        if meta_d[0] != "[" or meta_d[len(meta_d) - 1] != "]":
            raise ValueError(
                f"error in line {nb_line}: unvlaid meta data"
            )
        data = meta_d[1:len(meta_d) - 1]
        data.strip()
        result = data.split(" ")
        if len(result) > 3:
            raise ValueError(
                f"error in line {nb_line}: unvlaid meta data"
            )
        zone_types = [
            "normal",
            "priority",
            "restricted",
            "blocked",
        ]
        for meta in result:
            res = meta.split("=")
            if (
                res[0] in ["zone", "color", "max_drones"]
                and len(res) == 2
            ):
                if res[0] == "zone":
                    if res[1] in zone_types:
                        if info["zone_type"]:
                            raise ValueError(
                                f"error in line {nb_line}: "
                                "duplicated zone in meta data"
                            )
                        info["zone_type"] = res[1]
                    else:
                        raise ValueError(
                            f"error in line {nb_line}: "
                            "unvlaid meta data for zone type"
                        )
                elif res[0] == "max_drones":
                    try:
                        if info["max_drones"] is not None:
                            raise ValueError(
                                f"error in line {nb_line}: "
                                "duplicated max_drones in meta data"
                            )
                        info["max_drones"] = int(res[1])
                        if info["max_drones"] <= 0:
                            raise ValueError(
                                f"error in line {nb_line}: "
                                "enter valid nb_max_drones >= 1"
                            )
                    except ValueError:
                        raise ValueError(
                            f"error in line {nb_line}: "
                            "unvlaid meta data max_drones"
                        )
                elif res[0] == "color":
                    if info["color"] is not None:
                        raise ValueError(
                            f"error in line {nb_line}: "
                            "duplicated color in meta data"
                        )
                    info["color"] = res[1]
            else:
                raise ValueError(
                    f"error in line {nb_line}: unvlaid meta data"
                )
        return True

    def hub_manger(self, graph: Graph, data: str, nb_line):
        info = {}
        if graph.nb_drones is None:
            raise ValueError(
                f"error in line {nb_line}: "
                "valid nb_drones is required as first line info"
            )
        result: list[str] = data.split(":", 1)
        if (
            len(result) != 2
            or (
                result[0] != "start_hub"
                and result[0] != "hub"
                and result[0] != "end_hub"
            )
        ):
            raise ValueError(
                f"error in line {nb_line}: hub not valid"
            )
        result[1] = result[1].strip()
        values = result[1].split(" ")
        if len(values) < 3:
            raise ValueError(
                f"error in line {nb_line}: "
                "hub info must at least have: hub x y"
            )
        if values[0] in self.zones_name:
            raise ValueError(
                f"error in line {nb_line}: duplicated zone name"
            )
        self.zones_name.append(values[0])
        info["name"] = values[0]

        try:
            x = int(values[1])
            y = int(values[2])
            info["x"] = x
            info["y"] = y
        except ValueError:
            raise ValueError(
                f"error in line {nb_line}: "
                "x, y cordinate not valid"
            )
        if len(values) > 3:
            store = ""
            data = [x for x in values if x != ""]
            for i in range(3, len(data)):
                if i > 3:
                    store += " " + data[i].strip()
                else:
                    store += data[i]
            if "[" in data[3]:
                self.valid_meta(store, info, nb_line)
            else:
                raise ValueError(
                    f"error in line {nb_line}: unvlaid metadata"
                )
        else:
            info["zone_type"] = None
            info["color"] = None
            info["max_drones"] = None
        return info

    def connection_handler(self, data, count, graph: Graph, nb_line):
        if count < 2:
            raise ValueError(
                f"error in line {nb_line}: unvalid structure "
                "can not make connection add hubs"
            )
        result = data.split(":", 1)
        if len(result) != 2 or result[1] == "":
            raise ValueError(
                f"error in line {nb_line}: "
                "error unvalid connection"
            )
        connection = result[1].strip()
        connection = connection.split(":", 1)
        if len(connection) < 1 or connection[0] == "":
            raise ValueError(
                f"error in line {nb_line}: "
                "error unvalid connection"
            )
        elif "-" not in connection[0]:
            raise ValueError(
                f"error in line {nb_line}: "
                "error unvalid connection"
            )
        zones = connection[0].split("-", 1)
        if len(zones) != 2 or zones[0] == "" or zones[1] == "":
            raise ValueError(
                f"error in line {nb_line}: "
                "error unvalid connection"
            )
        zone_name1 = zones[0]
        zone_name2 = zones[1].split(" ", 1)[0]
        if (
            zone_name1 == zone_name2
            or zone_name1 not in self.zones_name
            or zone_name2 not in self.zones_name
        ):
            raise ValueError(
                f"error in line {nb_line}: unvalid connection "
                "same connection or zone are not known"
            )
        zone1 = graph.get_zone(zone_name1)
        zone2 = graph.get_zone(zone_name2)
        if zone2 in zone1.neighbors:
            raise ValueError(
                "error duplicated concetion: "
                f"({zone_name1}->{zone_name2})"
            )
        if len(connection) <= 2:
            meta = connection[0].split(" ", 1)
            if len(meta) == 2:
                if "[" in meta[1]:
                    max_link_capacity = self.connection_meta(
                        meta[1], nb_line
                    )
                    graph.connect(
                        zone_name1,
                        zone_name2,
                        max_link_capacity,
                    )
                else:
                    raise ValueError(
                        f"error in line {nb_line}: "
                        "error in connectin meta data"
                    )
            else:
                graph.connect(zone_name1, zone_name2, 1)

    def connection_meta(self, meta_d, nb_line):
        data = meta_d[1:len(meta_d) - 1]
        if not data:
            raise ValueError(
                f"error in line {nb_line}: unvlid metadata/empty"
            )
        result = data.split("=")
        if (
            len(result) != 2
            or result[0] != "max_link_capacity"
            or result[1] == ""
        ):
            raise ValueError(
                f"error in line {nb_line}: "
                "unvlaid meta data for connection"
            )
        try:
            value = int(result[1])
        except ValueError as e:
            raise ValueError(
                f"error in line {nb_line}: "
                f"enter valid value in metadata {e}"
            )
        if value <= 0:
            raise ValueError(
                f"error in line {nb_line}: unvlaid "
                "max_link_capacity number for connection"
            )
        return value

    def parse(self, graph: Graph):
        zones = []
        data = self.read_file()
        count = 0
        start_hub = False
        end_hub = False
        nb_line = 1
        filtered_data = [
            line.split("#", 1)[0].strip()
            for line in data
            if not (
                line.strip().startswith("#")
                or line.startswith("\n")
                or line == ""
            )
        ]
        for line in filtered_data:
            if line.startswith("nb_drones:"):
                if graph.nb_drones is not None:
                    raise ValueError(
                        f"error in line {nb_line}: "
                        "duplicated nb_drones"
                    )
                self.handle_drones(line, graph, nb_line)
            elif line.startswith("start_hub:"):
                if start_hub:
                    raise ValueError("duplicated zone start_hub")
                hub_info = self.hub_manger(graph, line, nb_line)
                hub = Zone(
                    hub_info["name"],
                    hub_info["x"],
                    hub_info["y"],
                    hub_info["color"],
                    hub_info["zone_type"],
                    float("inf"),
                )
                hub.set_default()
                hub.drones_in = graph.nb_drones
                zones.append(hub)
                graph.start = hub
                graph.add_zone(hub)
                start_hub = True
                count += 1
            elif line.startswith("hub:"):
                hub_info = self.hub_manger(graph, line, nb_line)
                hub = Zone(
                    hub_info["name"],
                    hub_info["x"],
                    hub_info["y"],
                    hub_info["color"],
                    hub_info["zone_type"],
                    hub_info["max_drones"],
                )
                hub.set_default()
                graph.add_zone(hub)
                zones.append(hub)
                count += 1
            elif line.startswith("end_hub:"):
                if end_hub:
                    raise ValueError("duplicated zone end_hub")
                hub_info = self.hub_manger(graph, line, nb_line)
                hub = Zone(
                    hub_info["name"],
                    hub_info["x"],
                    hub_info["y"],
                    hub_info["color"],
                    hub_info["zone_type"],
                    float("inf"),
                )
                hub.set_default()
                zones.append(hub)
                graph.end = hub
                graph.add_zone(hub)
                end_hub = True
                count += 1
            elif line.startswith("connection:"):
                self.connection_handler(
                    line,
                    count,
                    graph,
                    nb_line,
                )
            else:
                raise ValueError("unvalid data line")
            nb_line += 1
        if not start_hub or not end_hub:
            raise ValueError(
                "start_hub or end_hub are not present"
            )
        return zones

    def handle_drones(
        self,
        data: str,
        graph: Graph,
        line: int,
    ) -> Graph:
        result = data.split(":", 1)
        if len(result) != 2:
            raise ValueError(
                f"error in line {line}: "
                "enter valid argumnet 'nb_drones'!"
            )
        if result[0] != "nb_drones":
            raise ValueError(
                f"error in line {line}: "
                "enter valid argumnet 'nb_drones'!"
            )
        try:
            nb_drones = int(result[1])
        except ValueError:
            raise ValueError(
                f"error in line {line}: enter valid nb_drones!"
            )
        if nb_drones <= 0:
            raise ValueError(
                f"error in line {line}: "
                "enter valid nb_drones >= 1 !"
            )
        graph.nb_drones = nb_drones
        return graph
