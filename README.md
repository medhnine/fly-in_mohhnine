*This project has been created as part of the 42 curriculum by mohhnine.*

# Fly-in

## Description

Fly-in is a turn-based drone-routing simulation written in Python. The goal is to move a fleet of drones from a start hub to an end hub through a graph of connected zones while respecting zone capacities, connection capacities, blocked zones, restricted-zone movement costs, and priority zones.

The program parses a map file, builds a custom object-oriented graph, computes routes without using external graph libraries, assigns drones to the available paths, and simulates their movement turn by turn. The implementation also provides an optional colored terminal visualization to make drone positions and restricted-zone transit easier to follow.

## Features

- Custom object-oriented graph implementation.
- Parsing of `nb_drones`, hubs, metadata, and connections.
- Support for `normal`, `priority`, `restricted`, and `blocked` zones.
- Zone capacity handling through `max_drones`.
- Connection capacity handling through `max_link_capacity`.
- Two-turn movement into restricted zones.
- Priority-zone preference during pathfinding.
- Multiple-path drone distribution.
- Deadlock detection during simulation.
- Colored terminal visualization with `--visual`.
- Type annotations, docstrings, `mypy`, and `flake8` support.

## Instructions

### Requirements

- Python 3.10 or later
- `pip`

Install the development dependencies with:

```bash
make install
```

This installs the dependencies listed in `requirements.txt`, including `flake8` and `mypy`.

### Run the simulation

The general command is:

```bash
python3 main.py <map_file>
```

Example:

```bash
python3 main.py maps/easy/01_linear_path.txt
```

The same can be done through the Makefile:

```bash
make run MAP=maps/easy/01_linear_path.txt
```

If `MAP` is not specified, the Makefile uses:

```text
maps/easy/01_linear_path.txt
```

### Run with terminal visualization

```bash
python3 main.py maps/easy/01_linear_path.txt --visual
```

or:

```bash
make visual MAP=maps/easy/01_linear_path.txt
```

### Debug

```bash
make debug MAP=maps/easy/01_linear_path.txt
```

### Lint and type-check

```bash
make lint
```

This runs `flake8` and `mypy` using the flags required by the project.

For stricter type checking:

```bash
make lint-strict
```

### Clean temporary files

```bash
make clean
```

## Input Format

A map begins with the number of drones, followed by zone definitions and connections.

Example:

```text
nb_drones: 2
start_hub: start 0 0 [color=green]
hub: middle 1 0 [zone=normal color=blue max_drones=1]
end_hub: goal 2 0 [color=yellow]
connection: start-middle
connection: middle-goal
```

Zone metadata can contain:

- `zone=<type>`
- `color=<value>`
- `max_drones=<positive_integer>`

Connection metadata can contain:

- `max_link_capacity=<positive_integer>`

Example:

```text
connection: start-middle [max_link_capacity=2]
```

## Example Output

For the two-drone example above, the simulation produces output in the following form:

```text
D1-middle
D1-goal D2-middle
D2-goal
```

Each line represents one simulation turn. Drones that do not move during a turn are omitted.

For movement toward a restricted zone, the drone first appears on the connection and reaches the restricted zone during the following turn.

## Algorithm and Implementation Strategy

### Graph representation

The graph is built from custom Python classes:

- `Zone` stores zone properties, occupancy, capacity, neighbors, and reservations.
- `Connection` stores the two endpoint zones, maximum link capacity, and current usage.
- `Drone` stores its assigned path, current path position, and restricted-zone transit state.
- `Graph` stores all zones and connections and contains the pathfinding and path-assignment logic.

Connections are bidirectional and are stored using a normalized pair of zone names, allowing the same connection to be found regardless of direction.

### Pathfinding

The project uses a custom weighted shortest-path approach inspired by Dijkstra's algorithm.

Each zone is assigned a movement cost based on its type:

- `normal`: 1 turn
- `priority`: 1 turn, with priority used as a tie-breaker
- `restricted`: 2 turns
- `blocked`: excluded from pathfinding

The implementation repeatedly selects the unvisited zone with the smallest current distance. Priority zones reduce the priority component of the path score, which makes them preferred when path costs are otherwise comparable.

The program searches for up to two candidate routes. After selecting a path, its internal zones are penalized when searching for the next path. This encourages the second route to use different areas of the graph when possible while still allowing overlap when necessary.

### Drone distribution

Once candidate paths are found, drones are distributed between them using each path's movement cost and the number of drones already assigned to that path.

For every drone, the program chooses the path with the smallest value based on:

```text
path cost + number of drones already assigned
```

This helps balance drones between available routes instead of sending every drone through the same path.

### Turn scheduling and capacities

The simulation runs in discrete turns.

Active drones are processed from the most advanced path position toward the least advanced one. This allows drones farther along a route to leave zones before following drones attempt to enter them during the same turn.

For every movement, the simulation checks:

- available capacity in the destination zone;
- reservations made for drones travelling toward restricted zones;
- the connection's `max_link_capacity`;
- whether the drone is currently in restricted-zone transit.

Zone occupancy is tracked with `drones_in`. Restricted destinations also use `reserved` slots so that a drone entering a two-turn movement is guaranteed to have space when it arrives on the following turn.

Connection usage is rebuilt at the beginning of every turn from drones that are already in transit. New movements are then allowed only while the connection remains below its configured capacity.

If no drone can move while some drones have not reached the end, the simulator reports a deadlock instead of looping forever.

### Complexity

The pathfinder selects the lowest-cost unvisited zone by scanning the graph rather than using a priority queue. Its approximate time complexity is therefore:

```text
O(V^2 + E)
```

for one path search, where `V` is the number of zones and `E` is the number of connections.

The simulation processes and sorts active drones on each turn. Its cost is approximately:

```text
O(T * (E + D log D))
```

where `T` is the number of simulation turns and `D` is the number of drones.

## Visual Representation

Fly-in provides an optional colored terminal visualization enabled with `--visual`.

For every simulation turn, the visualizer displays:

- the current turn number;
- all zones;
- the drones currently occupying each zone;
- drones travelling on connections toward restricted zones;
- zone colors defined by map metadata.

This makes capacity restrictions and drone movement easier to understand than movement logs alone, especially on maps containing bottlenecks or restricted zones.

The `--visual` mode adds human-readable state information around the normal movement log. Without `--visual`, the program prints only the required turn-by-turn movement output.

## Project Structure

```text
.
├── main.py
├── parsing.py
├── simulation.py
├── tools.py
├── visualizer.py
├── Makefile
├── requirements.txt
├── .gitignore
├── README.md
└── maps/
```

### Main files

- `main.py` — command-line entry point.
- `parsing.py` — validates and parses map files.
- `tools.py` — graph, zone, drone, connection, and pathfinding classes.
- `simulation.py` — turn-based simulation and movement scheduling.
- `visualizer.py` — colored terminal visualization.

## Resources

The following resources were useful for understanding the concepts and tools used in this project:

- Python documentation: https://docs.python.org/3/
- Python `typing` documentation: https://docs.python.org/3/library/typing.html
- Dijkstra's shortest path algorithm: https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
- mypy documentation: https://mypy.readthedocs.io/
- flake8 documentation: https://flake8.pycqa.org/
- 42 Fly-in subject and evaluation requirements.

### AI Usage

AI tools were used as support during development to:

- review and clarify parts of the Fly-in subject and evaluation requirements;
- discuss parser and simulation edge cases;
- help diagnose `mypy` and `flake8` issues;
- improve type annotations and docstrings;
- review the implementation for requirement mismatches and possible test cases.
