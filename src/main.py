from tools import Graph, Zone
from parsing import Parse
import sys


def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError("error: Usage: python3 main.py <map_file>")
        path = sys.argv[1]
        parser = Parse(path)
        graph = Graph(2)
        parser.parse(graph)
        res = []
        in_path: set["Zone"] = set()
        paths = []
        max_paths = 2
        while res is not None:
            res = graph.find_path(in_path)
            if res is None:
                break
            paths.append(res.copy())
            block = res[1:-1]
            for zone in block:
                in_path.add(zone)
            if max_paths == 1:
                break
            max_paths -= 1

        drones = graph.assign_paths(paths)
        count = 1
        data = ""
        while not graph.is_all_arrived(drones):
            for key, value in graph.connection.items():
                value.usage = 0
            for drone in drones:
                if drone.in_connection is not None:
                    drone.in_connection.usage += 1
            dr_left = [d for d in drones if d.arrived is False]
            sr_drones = sorted(dr_left, key=lambda d: d.step, reverse=True)
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
                        moves.append(
                            f"D{drone.id}-{next_zone.name}"
                        )
                        moved = True
                        continue

                    if next_zone.zone_type == "restricted":
                        if next_zone.has_place and connection.check_capacity:
                            drone.in_connection = connection
                            moves.append(
                                f"D{drone.id}-{current_zone.name}-"
                                f"{next_zone.name}"
                            )
                            connection.usage += 1
                            current_zone.drones_in -= 1
                            next_zone.reserved += 1
                            moved = True
                    elif next_zone.has_place and connection.check_capacity:
                        next_zone.drones_in += 1
                        current_zone.drones_in -= 1
                        moves.append(f"D{drone.id}-{next_zone.name}")
                        connection.usage += 1
                        moved = True
                        drone.step += 1

            if moved is False:
                print("deadlock")
                return
            print(" ".join(moves))
            res = " ".join(moves)
            data += res + '\n'
            count += 1
        with open("/home/mohhnine/Desktop/fly-in/vis_data.txt", "a") as file:
            file.write(data)

    except Exception as e:
        print(f"opps {e}")


if __name__ == "__main__":
    main()
