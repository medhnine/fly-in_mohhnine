class ColoredTerminal:
        RESET = "\033[0m"

        COLORS = {
            "black": "\033[30m",
            "red": "\033[31m",
            "green": "\033[32m",
            "yellow": "\033[33m",
            "blue": "\033[34m",
            "purple": "\033[35m",
            "magenta": "\033[35m",
            "cyan": "\033[36m",
            "white": "\033[37m",

            # fake colors , if the user request them, defualt terminal color for unknown color
            "gold": "\033[33m",
            "orange": "\033[33m",
            "brown": "\033[33m",
            "maroon": "\033[31m",
            "darkred": "\033[31m",
            "crimson": "\033[31m",
            "violet": "\033[35m",
        }

        def color_zone(self, zone) -> str:
            color = self.COLORS.get(zone.color, "")
            return f"{color}{zone.name}{self.RESET}"

        def display_colored_info(self, graph, drones, turn):
            print("========================================")
            print(f"TURN: {turn}")
            print("========================================\n")
            print("ZONES:\n")
            for zone in graph.zones.values():
                ids = []
                for drone in drones:
                    if zone.name == drone.current_zone.name and drone.in_connection is None:
                        ids.append(f"D{drone.id}")
                print(f"{self.color_zone(zone)}    <-{" ".join(ids)}->")
            in_transit = True
            for drone in drones:
                if drone.in_connection is not None:
                    if in_transit:
                        print("\nIN TRANSIT:\n")
                        in_transit = False
                    print(f"D{drone.id} {self.color_zone(drone.current_zone)} -> {self.color_zone(drone.next_zone)}")