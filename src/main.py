from simulation import Simulator
import sys

def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError("error: Usage: python3 main.py <map_file>")
        path = sys.argv[1]
        sim = Simulator()
        sim.Simulation(path)
    except Exception as e:
        print(f"opps {e}")

if __name__ == "__main__":
    main()
