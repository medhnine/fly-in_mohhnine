"""Command-line entry point for the Fly-in simulation."""

import sys

from simulation import Simulator


def main() -> None:
    """Parse command-line arguments and run the simulation."""
    try:
        if len(sys.argv) < 2:
            raise ValueError(
                "error: Usage: python3 main.py <map_file> [--visual]"
            )
        visual = False
        if len(sys.argv) > 2 and "--visual" == sys.argv[2]:
            visual = True
        path = sys.argv[1]
        sim = Simulator(visual)
        sim.Simulation(path)
    except Exception as e:
        print(f"opps {e}")


if __name__ == "__main__":
    main()
