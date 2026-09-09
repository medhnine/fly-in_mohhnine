"""Colored terminal visualization for Fly-in simulations."""

from typing import cast

from tools import Drone, Graph, Zone


class ColoredTerminal:
    """Display graph and drone state using ANSI terminal colors."""

    RESET = "\033[0m"

    COLORS: dict[str, str] = {
        "black": "\033[30m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "purple": "\033[35m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
        "white": "\033[37m",
        "gray": "\033[90m",
        "grey": "\033[90m",
        "orange": "\033[38;5;208m",
        "gold": "\033[38;5;220m",
        "brown": "\033[38;5;94m",
        "pink": "\033[38;5;205m",
        "violet": "\033[38;5;177m",
        "maroon": "\033[38;5;88m",
        "crimson": "\033[38;5;160m",
        "lime": "\033[38;5;118m",
        "olive": "\033[38;5;100m",
        "navy": "\033[38;5;17m",
        "teal": "\033[38;5;30m",
        "aqua": "\033[38;5;51m",
        "indigo": "\033[38;5;54m",
        "turquoise": "\033[38;5;44m",
        "beige": "\033[38;5;230m",
    }

    def color_zone(self, zone: Zone) -> str:
        """Return a zone name wrapped in its configured ANSI color.

        Args:
            zone: Zone to format for terminal output.

        Returns:
            The colored zone name followed by the ANSI reset sequence.
        """
        color = self.COLORS.get(cast(str, zone.color), "")
        if color == "":
            color = "\033[31m"
        return f"{color}{zone.name}{self.RESET}"

    def display_colored_info(
        self,
        graph: Graph,
        drones: list[Drone],
        turn: int,
    ) -> None:
        """Display the current simulation state with terminal colors.

        Args:
            graph: Graph whose zones are being displayed.
            drones: Drones participating in the simulation.
            turn: Current simulation turn number.
        """
        print("========================================")
        print(f"TURN: {turn}")
        print("========================================\n")
        print("ZONES:\n")
        for zone in graph.zones.values():
            ids: list[str] = []
            for drone in drones:
                if (
                    zone.name == drone.current_zone.name
                    and drone.in_connection is None
                ):
                    ids.append(f"D{drone.id}")
            print(
                f'{self.color_zone(zone)}    '
                f'<-{" ".join(ids)}->'
            )
        in_transit = True
        for drone in drones:
            if drone.in_connection is not None:
                if in_transit:
                    print("\nIN TRANSIT:\n")
                    in_transit = False
                next_zone = cast(Zone, drone.next_zone)
                print(
                    f"D{drone.id} "
                    f"{self.color_zone(drone.current_zone)} -> "
                    f"{self.color_zone(next_zone)}"
                )
        print("\nMOVMENTS:\n")
