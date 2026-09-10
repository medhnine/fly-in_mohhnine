"""Input-file parser for the Fly-in drone simulation."""

from typing import cast

from tools import Graph, Zone


class Parse:
    """Parse a Fly-in map file and populate a graph."""

    def __init__(self, path: str) -> None:
        """Initialize the parser.

        Args:
            path: Path to the map file.
        """
        self.path = path
        self.zones_name: list[str] = []

    def parse(self, graph: Graph) -> list[Zone]:
        """Parse the input file into the provided graph.

        Args:
            graph: Graph to populate.

        Returns:
            Zones created while parsing the file.

        Raises:
            ValueError: If the input structure or values are invalid.
        """
        zones: list[Zone] = []
        data = self.read_file()
        count = 0
        start_hub = False
        end_hub = False
        nb_line = 1
        for line in data:
            if line.startswith("nb_drones:"):
                if graph.nb_drones is not None:
                    raise ValueError(
                        f"error in line {nb_line}: "
                        "duplicated nb_drones"
                    )
                self.handle_drones(line, graph, nb_line)
            elif line.startswith("start_hub:"):
                if start_hub:
                    raise ValueError(
                        f"error in line {nb_line}: "
                        "duplicated zone start_hub"
                    )
                hub_info = self.hub_manger(graph, line, nb_line)
                hub = Zone(
                    cast(str, hub_info["name"]),
                    cast(int, hub_info["x"]),
                    cast(int, hub_info["y"]),
                    cast(str | None, hub_info["color"]),
                    cast(str | None, hub_info["zone_type"]),
                    float("inf"),
                )
                hub.set_default()
                hub.drones_in = cast(int, graph.nb_drones)
                zones.append(hub)
                graph.start = hub
                graph.add_zone(hub)
                start_hub = True
                count += 1
            elif line.startswith("hub:"):
                hub_info = self.hub_manger(graph, line, nb_line)
                hub = Zone(
                    cast(str, hub_info["name"]),
                    cast(int, hub_info["x"]),
                    cast(int, hub_info["y"]),
                    cast(str | None, hub_info["color"]),
                    cast(str | None, hub_info["zone_type"]),
                    cast(
                        int | float | None,
                        hub_info["max_drones"],
                    ),
                )
                hub.set_default()
                graph.add_zone(hub)
                zones.append(hub)
                count += 1
            elif line.startswith("end_hub:"):
                if end_hub:
                    raise ValueError(
                        f"error in line {nb_line}: "
                        "duplicated zone end_hub"
                    )
                hub_info = self.hub_manger(graph, line, nb_line)
                hub = Zone(
                    cast(str, hub_info["name"]),
                    cast(int, hub_info["x"]),
                    cast(int, hub_info["y"]),
                    cast(str | None, hub_info["color"]),
                    cast(str | None, hub_info["zone_type"]),
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
            elif (
                line.strip().startswith("#")
                or line.startswith("\n")
                or line == ""
            ):
                pass
            else:
                raise ValueError(
                    f"error in line {nb_line}: unvalid data line "
                )
            nb_line += 1
        if not start_hub or not end_hub:
            raise ValueError("start_hub or end_hub are not present")
        return zones

    def read_file(self) -> list[str]:
        """Read the configured map file and visualization data.

        Returns:
            Raw lines read from the map file.

        Raises:
            ValueError: If the file cannot be read or written.
        """
        try:
            with open(self.path, "r") as f:
                result = f.readlines()
            data_file = ""
            for line in result:
                res = "".join(line)
                data_file += res + "\n"
            with open(
                "/home/mohhnine/Desktop/fly-in/vis_data.txt",
                "w",
            ) as file:
                file.write(data_file)
        except FileNotFoundError as e:
            raise ValueError(f"file not found {e}")
        except PermissionError as e:
            raise ValueError(f"Permission diened {e}")
        return result

    def handle_drones(
        self,
        data: str,
        graph: Graph,
        line: int,
    ) -> Graph:
        """Parse and store the number of drones.

        Args:
            data: Drone-count input line.
            graph: Graph receiving the parsed drone count.
            line: Current parser line number.

        Returns:
            The updated graph.

        Raises:
            ValueError: If the drone-count syntax or value is invalid.
        """
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

    def hub_manger(
        self,
        graph: Graph,
        data: str,
        nb_line: int,
    ) -> dict[str, object]:
        """Parse one start, end, or regular hub definition.

        Args:
            graph: Graph associated with the parsed map.
            data: Hub definition line.
            nb_line: Current parser line number.

        Returns:
            Parsed hub information.

        Raises:
            ValueError: If the hub definition or metadata is invalid.
        """
        info: dict[str, object] = {}
        line = data
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
        if (
            values[0] in self.zones_name
            or "-" in values[0]
            or " " in values[0]
        ):
            raise ValueError(
                f"error in line {nb_line}: duplicated zone name "
                "or zone_name contain '-'"
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
            data_values = [x for x in values if x != ""]
            for i in range(3, len(data_values)):
                if i > 3:
                    store += " " + data_values[i].strip()
                else:
                    store += data_values[i]
            if "[" in data_values[3]:
                self.valid_meta(store, info, nb_line, line)
            else:
                raise ValueError(
                    f"error in line {nb_line}: unvlaid metadata"
                )
        else:
            info["zone_type"] = None
            info["color"] = None
            info["max_drones"] = None
        return info

    def valid_meta(
        self,
        meta_d: str,
        info: dict[str, object],
        nb_line: int,
        line: str,
    ) -> bool:
        """Validate and store zone metadata.

        Args:
            meta_d: Raw metadata block.
            info: Hub-information dictionary to update.
            nb_line: Current parser line number.
            line: Original hub definition line.

        Returns:
            True when the metadata is accepted.

        Raises:
            ValueError: If metadata syntax or values are invalid.
        """
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
                        max_drones = cast(int, info["max_drones"])
                        if (
                            max_drones <= 0
                            and line.startswith("start_hub:") is False
                            and line.startswith("end_hub:") is False
                        ):
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

    def connection_handler(
        self,
        data: str,
        count: int,
        graph: Graph,
        nb_line: int,
    ) -> None:
        """Parse and add one connection definition.

        Args:
            data: Connection definition line.
            count: Number of hubs parsed so far.
            graph: Graph receiving the connection.
            nb_line: Current parser line number.

        Raises:
            ValueError: If the connection definition is invalid.
        """
        if count < 2:
            raise ValueError(
                f"error in line {nb_line}: unvalid structure "
                "can not make connection add hubs"
            )
        result = data.split(":")
        if len(result) != 2 or result[1] == "":
            raise ValueError(
                f"error in line {nb_line}: "
                "error unvalid connection"
            )
        connection = result[1].strip()
        connection_parts = connection.split(":", 1)
        if len(connection_parts) < 1 or connection_parts[0] == "":
            raise ValueError(
                f"error in line {nb_line}: "
                "error unvalid connection"
            )
        elif "-" not in connection_parts[0]:
            raise ValueError(
                f"error in line {nb_line}: "
                "error unvalid connection"
            )
        zones = connection_parts[0].split("-", 1)
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
        if len(connection_parts) <= 2:
            meta = connection_parts[0].split(" ", 1)
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

    def connection_meta(self, meta_d: str, nb_line: int) -> int:
        """Parse connection capacity metadata.

        Args:
            meta_d: Raw connection metadata block.
            nb_line: Current parser line number.

        Returns:
            Parsed positive connection capacity.

        Raises:
            ValueError: If metadata is malformed or non-positive.
        """
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
