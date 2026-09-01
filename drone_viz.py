# with open(map_file, "r") as file:
#             content = file.read()

#         with open("log.txt", "w") as file:
#             file.write(content)
#             file.write("\n".join(sim.visualizer.recordes))
"""
drone_viz.py

Stand-alone visualisation for a Fly-in drone simulation *log file*, rendered
with pygame.

Same design language as visualisation.py, but the input is different:
visualisation.py wraps a live Simulator and captures its stdout, while this
one reads a saved log after the fact. That means it works on any log you
already have on disk - no Map/Zone/Drone/Simulator objects needed, no import
of your project, nothing to re-run.

Usage
-----
    python3 drone_viz.py log.txt
    python3 drone_viz.py log.txt --fps 3 --snapshots --gif run.gif

Log format
----------
Map section:
    nb_drones: 25
    start_hub: start 0 0 [color=green max_drones=25]
    hub: gate_hell1 2 0 [color=red max_drones=1]
    end_hub: impossible_goal 23 0 [color=rainbow max_drones=25]
    connection: start-gate_hell1 [max_link_capacity=1]

Move section, one line per turn, space separated:
    D1-gate_hell1                  drone 1 is sitting on gate_hell1
    D1-micro_gate1-overflow_hell1  drone 1 is IN FLIGHT on that link and
                                   lands on overflow_hell1 next turn

A drone missing from a line simply did not move that turn, so positions
carry over. Turn 0 is the state before anything moved: every drone parked on
the start hub. In-flight tokens are normalised internally to the same
"from->to" notation visualisation.py already uses, and drawn at the midpoint
of the link.

If the log holds the same solution several times over (a solver that printed
its answer twice, or several scenarios appended into one file), each replay
is detected as a separate run - press TAB to cycle through them - instead of
being stitched into one impossible animation where drones teleport back to
the start.

Controls
--------
    SPACE                     play / pause
    RIGHT / N / click         step one turn forward
    LEFT  / P / right-click   step one turn back
    HOME / END                jump to the first / last turn
    drag (left button)        pan the camera
    scroll wheel              zoom around the cursor
    + / -                     zoom around the centre
    R / 0                     reset the view (fit the whole map)
    G                         switch layout: map coordinates <-> BFS phases
    F / SHIFT+F               focus the next / previous drone
    ESC                       clear the focus, or quit if nothing is focused
    TAB                       next run (only if the log holds more than one)

Two things worth knowing about
------------------------------
1. Two layouts, press G to switch (the header says which one is on).

   MAP layout uses the x/y written in the log file. That is the author's own
   hand-drawn picture of the map, so it is the one to look at when you want
   the shape you designed - the maze block here, the overflow block there.

   PHASE layout throws those coordinates away and rebuilds the map by hop
   distance from the start (_levels_by_bfs), one shaded column per phase,
   ordered inside each column by a Sugiyama-style barycenter sweep
   (_order_within_levels) so links to the next column stay as straight and
   uncrossed as possible. This is the one to look at when you want to see
   how far along a drone actually is, because "further right" then really
   means "closer to the goal" - which hand-written coordinates only loosely
   imply.

2. Focus one drone with F. Everything else fades back, the drone's whole
   route across the run is traced, and the header shows where it is right
   now. On a 25-drone log, following one drone through a bottleneck by eye
   is otherwise close to impossible.

Every link is routed by how many columns it spans, so one column's links
never blend into another's: neighbouring columns get a plain straight line,
same-column links are bowed sideways to clear whatever is stacked between
them, and links that skip two or more columns are routed up into a lane
above the whole map so they visibly jump over the columns in between.
Colour and dashing follow the same three kinds - see the in-window legend.

Hub names, capacity and link capacity are always drawn, on a solid label
background, so nothing needed to trace a move is ever hidden behind a
crossing edge. Spacing is fixed rather than squeezed to fit the window;
pan and zoom are what let a dense map breathe.

With --snapshots it also writes one PNG per turn, and with --gif it stitches
them into an animated gif (needs pillow). Both are off by default: a 90-turn
log would otherwise drop 90 files into your working directory every run.
"""

import argparse
import glob
import math
import os
import re
import sys
from collections import defaultdict, deque

try:
    import pygame
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "drone_viz.py needs pygame. Install it with: pip install pygame"
    ) from exc


# ------------------------------------------------------------------ #
# palette
# ------------------------------------------------------------------ #

BACKGROUND = (250, 250, 250)
EDGE_COLOR = (180, 180, 180)
EDGE_LABEL_BG = (250, 250, 250)
TEXT_COLOR = (20, 20, 20)
MUTED_TEXT_COLOR = (110, 110, 110)
NODE_BORDER = (20, 20, 20)
HEADER_BG = (235, 235, 235)
LEGEND_BORDER = (210, 210, 210)

DRONE_FILL = (0, 210, 255)
DRONE_BORDER = (4, 40, 70)
DRONE_TEXT = (4, 20, 35)
DRONE_DONE_FILL = (90, 220, 140)
DRONE_FADED_FILL = (196, 208, 214)
DRONE_FADED_BORDER = (150, 165, 172)

ACTIVE_EDGE_COLOR = (255, 45, 130)
ACTIVE_EDGE_OUTLINE = (60, 10, 30)
FOCUS_ROUTE_COLOR = (255, 170, 40)
FOCUS_RING = (255, 120, 0)

RESTRICTED_RING = (70, 70, 70)
PRIORITY_RING = (200, 150, 20)
CONGESTED_RING = (220, 30, 30)
START_RING = (30, 160, 80)
END_RING = (200, 40, 200)

LATERAL_EDGE_COLOR = (30, 140, 150)
SKIP_EDGE_COLOR = (145, 70, 195)

PHASE_BAND_COLORS = ((219, 231, 245, 90), (241, 241, 234, 90))
PHASE_DIVIDER = (205, 212, 222)
PHASE_LABEL_COLOR = (95, 105, 122)

VIEW_W, VIEW_H = 1680, 980
HEADER_H = 68
NODE_RADIUS = 28
DRONE_RADIUS = 12
MIN_ZOOM, MAX_ZOOM = 0.05, 3.0
# Below these zoom levels a label would be smaller than the ink it sits on,
# so detail is dropped a tier at a time instead of piling unreadable text on
# top of itself: full labels, then names only, then no text at all.
DETAIL_FULL_ZOOM = 0.45
DETAIL_NAME_ZOOM = 0.22
ANIM_DURATION = 0.35
GOLDEN_ANGLE = math.pi * (3 - math.sqrt(5))
X_GAP, Y_GAP = 340, 210

LAYOUT_MAP, LAYOUT_PHASE = "map", "phase"

# colour names a log may use that pygame does not know
EXTRA_COLORS = {
    "darkred": (139, 0, 0),
    "maroon": (128, 0, 0),
    "crimson": (220, 20, 60),
    "rainbow": (255, 105, 180),
}


# ------------------------------------------------------------------ #
# the map, parsed out of the log
# ------------------------------------------------------------------ #

class Hub:
    """One zone of the map, exactly as the log file describes it."""

    __slots__ = ("name", "x", "y", "color", "zone_type", "max_drones", "kind")

    def __init__(self, name, x, y, attrs, kind):
        self.name = name
        self.x = x
        self.y = y
        self.kind = kind                                  # start | end | hub
        self.color = attrs.get("color", "gray")
        self.zone_type = attrs.get("zone", "normal")
        raw_cap = attrs.get("max_drones")
        self.max_drones = int(raw_cap) if raw_cap and raw_cap.isdigit() else None

    @property
    def cap_text(self):
        return str(self.max_drones) if self.max_drones is not None else "-"


ATTR_RE = re.compile(r"(\w+)\s*=\s*([^\s\]]+)")
HUB_LINE_RE = re.compile(r"^(hub|start_hub|end_hub)\s*:\s*(.*)$")
DRONE_TOKEN_RE = re.compile(r"^D(\d+)-(.+)$")


def _attrs(text):
    return dict(ATTR_RE.findall(text or ""))


def _split_hub_pair(token, hubs):
    """
    Split "a-b" into (a, b) by matching against the hub names we know,
    rather than splitting on the first hyphen. Hub names are then free to
    contain hyphens of their own.
    """
    for i in range(1, len(token)):
        if token[i] != "-":
            continue
        left, right = token[:i], token[i + 1:]
        if left in hubs and right in hubs:
            return left, right
    return None


def parse_map(lines):
    """
    Read the map section.

    Returns (hubs, edges, nb_drones, move_start_index) where hubs is
    {name: Hub}, edges is a de-duplicated [(name1, name2, capacity_or_None)],
    and move_start_index is the line the move section begins on.
    """
    hubs, raw_edges, nb_drones = {}, [], 0
    move_start = len(lines)

    for index, raw in enumerate(lines):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        if line.startswith("nb_drones:"):
            try:
                nb_drones = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
            continue

        hub_match = HUB_LINE_RE.match(line)
        if hub_match:
            kind = {"hub": "hub", "start_hub": "start", "end_hub": "end"}[hub_match.group(1)]
            body = hub_match.group(2)
            attr_text = ""
            if "[" in body:
                body, attr_text = body.split("[", 1)
            parts = body.split()
            if len(parts) >= 3:
                try:
                    hubs[parts[0]] = Hub(parts[0], float(parts[1]), float(parts[2]),
                                         _attrs(attr_text), kind)
                except ValueError:
                    pass
            continue

        if line.startswith("connection:"):
            body = line.split(":", 1)[1].strip()
            attr_text = ""
            if "[" in body:
                body, attr_text = body.split("[", 1)
            raw_cap = _attrs(attr_text).get("max_link_capacity")
            raw_edges.append((body.strip(),
                              int(raw_cap) if raw_cap and raw_cap.isdigit() else None))
            continue

        if DRONE_TOKEN_RE.match(line.split()[0]):
            move_start = index
            break

    edges, seen = [], set()
    for body, capacity in raw_edges:
        pair = _split_hub_pair(body, hubs)
        if not pair:
            continue
        key = tuple(sorted(pair))
        if key in seen:
            continue
        seen.add(key)
        edges.append((pair[0], pair[1], capacity))

    return hubs, edges, nb_drones, move_start


def parse_runs(lines, hubs, adjacency, nb_drones, start_name):
    """
    Read the move section into runs of per-turn snapshots.

    A snapshot is {drone_id: position}, where position is either a hub name
    or the "from->to" mid-transit notation. Every snapshot holds every drone,
    so a drone that did not move this turn is still in there - the log only
    prints what changed, but the animation needs the whole picture.

    A log that replays the same solution more than once is split into one run
    per replay. The split is detected by legality, not by looking for a
    repeated first line: the moment a line asks a drone to appear somewhere
    it could not possibly have reached from where it currently stands, the
    log must have restarted.
    """
    def base_snapshot():
        return {str(i): start_name for i in range(1, max(nb_drones, 1) + 1)}

    def reachable(current, target):
        """Could a drone at `current` legally be at `target` next turn?"""
        if "->" in current:
            _source, destination = current.split("->", 1)
            if "->" in target:
                return target == current                  # still crossing
            return target == destination                  # landed
        if "->" in target:
            source, _destination = target.split("->", 1)
            return source == current                      # took off
        return target == current or target in adjacency.get(current, ())

    runs, snapshots, positions = [], [], base_snapshot()

    def flush():
        if len(snapshots) > 1:
            runs.append(list(snapshots))

    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        parsed = []
        for token in line.split():
            token_match = DRONE_TOKEN_RE.match(token)
            if not token_match:
                continue
            drone_id, rest = token_match.group(1), token_match.group(2)
            if rest in hubs:
                parsed.append((drone_id, rest))
            else:
                pair = _split_hub_pair(rest, hubs)
                if pair:
                    parsed.append((drone_id, f"{pair[0]}->{pair[1]}"))
        if not parsed:
            continue

        if snapshots and any(not reachable(positions.get(d, start_name), p) for d, p in parsed):
            flush()
            snapshots, positions = [], base_snapshot()

        if not snapshots:
            snapshots.append(dict(positions))             # turn 0

        for drone_id, position in parsed:
            positions[drone_id] = position
        snapshots.append(dict(positions))

    flush()
    return runs


# ------------------------------------------------------------------ #
# layout
# ------------------------------------------------------------------ #

def _levels_by_bfs(hubs, adjacency, start_name):
    """
    {hub_name: hop distance from the start}. Anything the start cannot reach
    is parked in its own column past the end, so an unreachable dead end
    still renders instead of taking the layout down with it.
    """
    levels = {start_name: 0}
    queue = deque([start_name])
    while queue:
        current = queue.popleft()
        for neighbor in sorted(adjacency.get(current, ())):
            if neighbor not in levels:
                levels[neighbor] = levels[current] + 1
                queue.append(neighbor)

    spare = (max(levels.values()) + 1) if levels else 0
    for name in sorted(hubs):
        if name not in levels:
            levels[name] = spare
            spare += 1
    return levels


def _order_within_levels(adjacency, levels):
    """
    {level: [name, ...]} ordered to cut down crossings between neighbouring
    columns before any position is handed out: a Sugiyama-style barycenter
    sweep, alternating left-to-right and right-to-left a few times, where a
    hub is pulled towards the average slot of its neighbours in the column
    next door. A hub with no neighbour there keeps its previous relative
    order, so nothing ever collapses onto one spot. The starting order is
    alphabetical, which makes the whole thing deterministic: same log in,
    same picture out.
    """
    grouped = defaultdict(list)
    for name, level in levels.items():
        grouped[level].append(name)
    for names in grouped.values():
        names.sort()

    if not grouped:
        return grouped
    max_level = max(grouped)

    def sweep(level_range, offset):
        for level in level_range:
            reference = level + offset
            if reference not in grouped:
                continue
            reference_index = {n: i for i, n in enumerate(grouped[reference])}
            current_index = {n: i for i, n in enumerate(grouped[level])}

            def sort_key(name, reference_index=reference_index,
                         reference=reference, current_index=current_index):
                slots = [reference_index[n] for n in adjacency.get(name, ())
                         if levels.get(n) == reference and n in reference_index]
                if slots:
                    return (0, sum(slots) / len(slots))
                return (1, current_index[name])

            grouped[level].sort(key=sort_key)

    for _ in range(3):
        sweep(range(1, max_level + 1), -1)
        sweep(range(max_level - 1, -1, -1), 1)

    return grouped


def phase_layout(adjacency, levels):
    """
    Left to right by hop distance from the start, one column per phase.
    Returns ({name: (world_x, world_y)}, {name: column_index}).

    Gaps are fixed rather than shrunk to fit the window, so labels never have
    to overlap to make room - the camera is what deals with a big map.
    """
    grouped = _order_within_levels(adjacency, levels)
    positions = {}
    for level, names in grouped.items():
        count = len(names)
        for i, name in enumerate(names):
            positions[name] = (level * X_GAP, (i - (count - 1) / 2) * Y_GAP)
    return positions, dict(levels)


def map_layout(hubs):
    """
    The x/y the log file itself gives, scaled into world units. Returns
    ({name: (world_x, world_y)}, {name: column_index}) where the column is
    just the rounded x, so links still get classified and routed by how far
    across the map they reach.
    """
    positions, columns = {}, {}
    for name, hub in hubs.items():
        positions[name] = (hub.x * X_GAP, hub.y * Y_GAP)
        columns[name] = int(round(hub.x))
    return positions, columns


def _edge_path(name1, name2, positions, columns, content_top):
    """
    World-space route for one link, plus its kind, chosen from how many
    columns it spans:

      - neighbouring columns, the normal case: a plain straight line.
      - same column, a lateral link such as a loop inside one layer: bowed
        sideways so it does not run straight through whatever else is
        stacked in that column.
      - two or more columns skipped: routed up into a lane above the whole
        map and back down, so it visibly jumps over the columns in between
        instead of cutting through their hubs. The further it jumps, the
        higher the lane, so several skips never collapse onto one line.

    Returns (points, kind).
    """
    x1, y1 = positions[name1]
    x2, y2 = positions[name2]
    column1, column2 = columns.get(name1), columns.get(name2)

    if column1 is None or column2 is None:
        return [(x1, y1), (x2, y2)], "forward"

    if column1 == column2:
        bow = 26 + min(80, abs(y2 - y1) * 0.15)
        return [(x1, y1), (max(x1, x2) + bow, (y1 + y2) / 2), (x2, y2)], "lateral"

    span = abs(column1 - column2)
    if span == 1:
        return [(x1, y1), (x2, y2)], "forward"

    # deterministic small stagger, so several skips of the same span do not
    # all trace the exact same lane
    fan = (sum(map(ord, name1 + name2)) % 4) * 7
    lane_y = content_top - 130 - (span - 2) * 24 - fan
    return [(x1, y1), (x1, lane_y), (x2, lane_y), (x2, y2)], "skip"


def _edge_path_geometric(name1, name2, positions):
    """
    Route for one link in MAP layout, where column-span routing does not
    apply.

    In phase layout a column really is a hop, so "this link spans three
    columns" is a meaningful statement about the link. In map layout the
    x/y are just where the author drew each hub, and the gaps between them
    mean nothing in particular - a plain neighbouring link like
    start(x=0) - gate_hell1(x=2) would be branded a two-column jump and
    hauled up into the lane above the map, which is nonsense.

    So links are straight here, and the only question worth asking is
    geometric: does this straight line run over some *other* hub on its way?
    If it does, the line is bowed to the far side of whatever it was about to
    cut through, so a link never looks like it terminates at a hub it merely
    passes over. Otherwise it stays straight.

    Returns (points, kind), with the same "forward" / "lateral" vocabulary
    the rest of the drawing code already understands.
    """
    x1, y1 = positions[name1]
    x2, y2 = positions[name2]
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return [(x1, y1), (x2, y2)], "forward"

    ux, uy = dx / length, dy / length
    clearance = 0.35 * Y_GAP
    worst = None                                   # (distance, cross_sign)

    for name, (px, py) in positions.items():
        if name in (name1, name2):
            continue
        along = (px - x1) * ux + (py - y1) * uy
        if not 0 < along < length:                 # not between the two ends
            continue
        offset = abs((px - x1) * uy - (py - y1) * ux)
        if offset < clearance and (worst is None or offset < worst[0]):
            cross = (px - x1) * uy - (py - y1) * ux
            worst = (offset, 1.0 if cross >= 0 else -1.0)

    if worst is None:
        return [(x1, y1), (x2, y2)], "forward"

    # bow to the opposite side of whatever we were about to run over
    side = -worst[1]
    bow = 0.5 * Y_GAP
    control = ((x1 + x2) / 2 + uy * bow * side, (y1 + y2) / 2 - ux * bow * side)
    return [(x1, y1), control, (x2, y2)], "lateral"


def build_edge_paths(edges, positions, columns, layout):
    """{(name1, name2): (points, kind, capacity)}, computed once per layout."""
    content_top = min(y for _x, y in positions.values())
    paths = {}
    for name1, name2, capacity in edges:
        if name1 not in positions or name2 not in positions:
            continue
        if layout == LAYOUT_PHASE:
            points, kind = _edge_path(name1, name2, positions, columns, content_top)
        else:
            points, kind = _edge_path_geometric(name1, name2, positions)
        paths[(name1, name2)] = (points, kind, capacity)
    return paths


# ------------------------------------------------------------------ #
# small geometry helpers
# ------------------------------------------------------------------ #

def _path_point_at(points, t):
    """
    The point at fraction t along a polyline's real length, so a capacity
    label lands on a routed link's actual visual midpoint rather than the
    midpoint of its two endpoints.
    """
    if len(points) == 1:
        return points[0]
    lengths = [math.hypot(bx - ax, by - ay) for (ax, ay), (bx, by) in zip(points, points[1:])]
    total = sum(lengths)
    if total <= 1e-9:
        return points[0]
    target, walked = total * t, 0.0
    for (start, end), length in zip(zip(points, points[1:]), lengths):
        if length <= 1e-9:
            continue
        if walked + length >= target:
            local = (target - walked) / length
            return (start[0] + (end[0] - start[0]) * local,
                    start[1] + (end[1] - start[1]) * local)
        walked += length
    return points[-1]


def _draw_polyline(screen, color, points, width):
    if len(points) >= 2:
        pygame.draw.lines(screen, color, False, points, width)


def _draw_dashed_polyline(screen, color, points, width, dash_len=10, gap_len=7):
    """
    Dashed version of _draw_polyline. Lateral and cross-column links are
    dashed on top of having their own colour, so which kind of link you are
    looking at survives a black-and-white printout.
    """
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 1e-6:
            continue
        ux, uy = (x2 - x1) / length, (y2 - y1) / length
        walked, drawing = 0.0, True
        while walked < length:
            step = min(walked + (dash_len if drawing else gap_len), length)
            if drawing:
                pygame.draw.line(screen, color,
                                 (x1 + ux * walked, y1 + uy * walked),
                                 (x1 + ux * step, y1 + uy * step), width)
            walked, drawing = step, not drawing


def _draw_arrow(screen, p1, p2, color, size):
    x1, y1 = p1
    x2, y2 = p2
    mx, my = x1 + (x2 - x1) * 0.6, y1 + (y2 - y1) * 0.6
    angle = math.atan2(y2 - y1, x2 - x1)
    left = (mx - size * math.cos(angle - math.pi / 7), my - size * math.sin(angle - math.pi / 7))
    right = (mx - size * math.cos(angle + math.pi / 7), my - size * math.sin(angle + math.pi / 7))
    pygame.draw.polygon(screen, color, [(mx, my), left, right])


def _drone_jitter(seed, max_radius):
    """
    A small per-drone offset, identical on every turn and every frame (a
    sunflower pattern keyed by the drone's index), so a drone always sits in
    the same spot inside a crowded hub instead of reshuffling whenever its
    neighbours come and go. That stability is what makes one drone
    followable by eye across turns.
    """
    angle = seed * GOLDEN_ANGLE
    radius = max_radius * math.sqrt(((seed % 29) + 1) / 29.0)
    return radius * math.cos(angle), radius * math.sin(angle)


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _resolve_world_pos(position, positions):
    """A hub name, or a "from->to" transit drawn at the middle of the link."""
    if position in positions:
        return positions[position]
    if "->" in position:
        source, destination = position.split("->", 1)
        if source in positions and destination in positions:
            x1, y1 = positions[source]
            x2, y2 = positions[destination]
            return (x1 + x2) / 2, (y1 + y2) / 2
    raise KeyError(position)


def _active_edges(previous, current):
    """
    {(name1, name2) sorted: (from_name, to_name)} for every link a drone is
    using in this transition, so it can be highlighted with a direction
    arrow. Covers both a plain hop and the mid-transit notation.
    """
    active = {}
    for drone_id, now in current.items():
        before = previous.get(drone_id, now)
        segments = []
        if "->" in before:
            segments.append(tuple(before.split("->", 1)))
        if "->" in now:
            segments.append(tuple(now.split("->", 1)))
        if before != now and "->" not in before and "->" not in now:
            segments.append((before, now))
        for a, b in segments:
            active[tuple(sorted((a, b)))] = (a, b)
    return active


def _drone_route_edges(snapshots, drone_id):
    """Every link the focused drone uses across the whole run."""
    used = set()
    for previous, current in zip(snapshots, snapshots[1:]):
        before, now = previous.get(drone_id), current.get(drone_id)
        if before is None or now is None:
            continue
        used.update(_active_edges({drone_id: before}, {drone_id: now}))
    return used


def _hub_color(hub):
    if hub.color in EXTRA_COLORS:
        return EXTRA_COLORS[hub.color]
    try:
        return pygame.Color(hub.color)
    except ValueError:
        return pygame.Color("gray")


# ------------------------------------------------------------------ #
# camera
# ------------------------------------------------------------------ #

class Camera:
    def __init__(self, x, y, zoom):
        self.x, self.y, self.zoom = x, y, zoom

    def to_screen(self, wx, wy, viewport_w, viewport_h, header_h):
        return ((wx - self.x) * self.zoom + viewport_w / 2,
                (wy - self.y) * self.zoom + header_h + viewport_h / 2)

    def to_world(self, sx, sy, viewport_w, viewport_h, header_h):
        return ((sx - viewport_w / 2) / self.zoom + self.x,
                (sy - header_h - viewport_h / 2) / self.zoom + self.y)


def _fit_camera(positions, viewport_w, viewport_h, extra_top_margin=0):
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys) - extra_top_margin, max(ys)
    span_x = max(max_x - min_x, NODE_RADIUS * 6)
    span_y = max(max_y - min_y, NODE_RADIUS * 6)
    zoom = min(viewport_w / (span_x * 1.25), viewport_h / (span_y * 1.25))
    # The opening view always fits the whole map, however wide it is - the
    # first thing you should see is the shape of the problem, not a third of
    # it. Labels are what would break at that zoom, so they get dropped a
    # tier at a time (DETAIL_*_ZOOM) rather than the view being clamped to
    # keep them. Scroll in and the detail comes back.
    return Camera((min_x + max_x) / 2, (min_y + max_y) / 2, min(zoom, 1.4))


def _zoom_at(camera, screen_pos, factor, viewport_w, viewport_h, header_h):
    wx, wy = camera.to_world(screen_pos[0], screen_pos[1], viewport_w, viewport_h, header_h)
    camera.zoom = max(MIN_ZOOM, min(MAX_ZOOM, camera.zoom * factor))
    camera.x = wx - (screen_pos[0] - viewport_w / 2) / camera.zoom
    camera.y = wy - (screen_pos[1] - header_h - viewport_h / 2) / camera.zoom


# ------------------------------------------------------------------ #
# text cache
# ------------------------------------------------------------------ #

class TextCache:
    """
    Around 130 labels are redrawn every frame at 60 fps. Rendering each one
    from scratch every time is the most expensive thing here by a wide
    margin, and the text itself barely ever changes, so rendered surfaces
    are kept and reused.
    """

    def __init__(self):
        self._cache = {}

    def render(self, font, text, color):
        key = (id(font), text, color)
        surface = self._cache.get(key)
        if surface is None:
            surface = font.render(text, True, color)
            self._cache[key] = surface
        return surface


# ------------------------------------------------------------------ #
# drawing
# ------------------------------------------------------------------ #

def _draw_phase_bands(screen, to_screen, column_x, content_top, content_bottom,
                      font, cache):
    """
    An alternating shaded band, a divider and a header per column, drawn
    first so every hub, link and drone sits on top of them. This is what
    turns a phase from an invisible x-position into a group you can see.
    """
    top, bottom = content_top - 150, content_bottom + 60
    last = None
    for column in sorted(column_x):
        cx = column_x[column]
        x1, y1 = to_screen(cx - X_GAP / 2, top)
        x2, y2 = to_screen(cx + X_GAP / 2, bottom)
        band = pygame.Surface((max(1, int(x2 - x1)), max(1, int(y2 - y1))), pygame.SRCALPHA)
        band.fill(PHASE_BAND_COLORS[column % 2])
        screen.blit(band, (x1, y1))
        pygame.draw.line(screen, PHASE_DIVIDER, (x1, y1), (x1, y2), 1)
        label = cache.render(font, f"PHASE {column}", PHASE_LABEL_COLOR)
        screen.blit(label, label.get_rect(centerx=(x1 + x2) / 2, top=y1 + 6))
        last = (x2, y1, y2)
    if last:
        x2, y1, y2 = last
        pygame.draw.line(screen, PHASE_DIVIDER, (x2, y1), (x2, y2), 1)


def _draw_legend(screen, font, cache, viewport_w, header_h, focused, layout):
    entries = [
        (DRONE_FILL, "drone", "circle"),
        (DRONE_DONE_FILL, "drone at the goal", "circle"),
        (ACTIVE_EDGE_COLOR, "moved this turn", "line"),
        (CONGESTED_RING, "hub at capacity", "ring"),
        (PRIORITY_RING, "priority zone", "ring"),
        (RESTRICTED_RING, "restricted zone", "ring"),
        (START_RING, "start hub", "ring"),
        (END_RING, "goal hub", "ring"),
    ]
    # naming a link kind the current layout never produces would be worse
    # than saying nothing, so the link rows follow the layout
    if layout == LAYOUT_PHASE:
        entries += [
            (EDGE_COLOR, "next-phase link", "line"),
            (LATERAL_EDGE_COLOR, "same-phase link", "dashed"),
            (SKIP_EDGE_COLOR, "phase-skipping link", "dashed"),
        ]
    else:
        entries += [
            (EDGE_COLOR, "link", "line"),
            (LATERAL_EDGE_COLOR, "link routed around a hub", "dashed"),
        ]
    if focused:
        entries.append((FOCUS_ROUTE_COLOR, f"route of D{focused}", "line"))

    pad, row_h, swatch = 8, 18, 16
    width, height = 215, pad * 2 + row_h * len(entries)
    x, y = viewport_w - width - 12, header_h + 12
    box = pygame.Surface((width, height), pygame.SRCALPHA)
    box.fill((255, 255, 255, 235))
    screen.blit(box, (x, y))
    pygame.draw.rect(screen, LEGEND_BORDER, (x, y, width, height), 1)

    for i, (color, label, shape) in enumerate(entries):
        cy = y + pad + row_h * i + row_h / 2
        cx = x + pad + swatch / 2
        if shape == "circle":
            pygame.draw.circle(screen, color, (cx, cy), swatch / 2.2)
        elif shape == "ring":
            pygame.draw.circle(screen, color, (cx, cy), swatch / 2.2, 2)
        elif shape == "line":
            pygame.draw.line(screen, color, (x + pad, cy), (x + pad + swatch, cy), 3)
        else:
            pygame.draw.line(screen, color, (x + pad, cy), (x + pad + swatch * 0.4, cy), 3)
            pygame.draw.line(screen, color, (x + pad + swatch * 0.6, cy), (x + pad + swatch, cy), 3)
        text = cache.render(font, label, TEXT_COLOR)
        screen.blit(text, (x + pad + swatch + 8, cy - text.get_height() / 2))


def _draw_label_block(screen, cache, lines_and_fonts, x, top):
    """
    A name/capacity block on a solid card, so it stays readable over whatever
    links happen to cross behind it.
    """
    surfaces = [cache.render(font, text, TEXT_COLOR) for font, text in lines_and_fonts]
    rects, y = [], top
    for surface in surfaces:
        rect = surface.get_rect(centerx=x, top=y)
        rects.append(rect)
        y = rect.bottom + 1
    block = rects[0].unionall(rects[1:]).inflate(8, 6)
    pygame.draw.rect(screen, EDGE_LABEL_BG, block, border_radius=3)
    pygame.draw.rect(screen, LEGEND_BORDER, block, 1, border_radius=3)
    for surface, rect in zip(surfaces, rects):
        screen.blit(surface, rect)


def draw_frame(screen, state):
    """One full frame. `state` is the ViewState below."""
    title_font, label_font, small_font = state.fonts
    cache, camera = state.cache, state.camera
    positions, edge_paths = state.positions, state.edge_paths
    eased = _ease(state.anim_t)

    screen.fill(BACKGROUND)

    def to_screen(wx, wy):
        return camera.to_screen(wx, wy, state.viewport_w, state.viewport_h, HEADER_H)

    if state.layout == LAYOUT_PHASE:
        _draw_phase_bands(screen, to_screen, state.column_x, state.content_top,
                          state.content_bottom, label_font, cache)

    active = _active_edges(state.anim_from, state.anim_to)
    kind_color = {"forward": EDGE_COLOR, "lateral": LATERAL_EDGE_COLOR, "skip": SKIP_EDGE_COLOR}

    for (name1, name2), (world_points, kind, capacity) in edge_paths.items():
        points = [to_screen(wx, wy) for wx, wy in world_points]
        key = tuple(sorted((name1, name2)))

        if key in state.focus_route:
            _draw_polyline(screen, FOCUS_ROUTE_COLOR, points, max(4, int(7 * camera.zoom)))

        if key in active:
            width = max(3, int(5 * camera.zoom))
            _draw_polyline(screen, ACTIVE_EDGE_OUTLINE, points, width + 2)
            _draw_polyline(screen, ACTIVE_EDGE_COLOR, points, width)
            if camera.zoom >= 0.25:
                from_name, _to_name = active[key]
                arrow = points if from_name == name1 else list(reversed(points))
                _draw_arrow(screen, arrow[-2], arrow[-1], ACTIVE_EDGE_COLOR,
                            max(6, 10 * camera.zoom))
        else:
            width = max(1, int(2 * camera.zoom))
            if kind == "forward":
                _draw_polyline(screen, kind_color[kind], points, width)
            else:
                _draw_dashed_polyline(screen, kind_color[kind], points, width)

        # A declared link capacity is always spelled out, on its own solid
        # background, so it stays readable no matter how many lines cross
        # behind it. A link with no declared capacity gets no label at all:
        # this map declares one on 5 links out of 70, and printing "cap -"
        # on the other 65 would bury the 5 that matter under its own noise.
        if capacity is not None and camera.zoom >= DETAIL_FULL_ZOOM:
            text = cache.render(small_font, f"cap {capacity}", TEXT_COLOR)
            rect = text.get_rect(center=_path_point_at(points, 0.5))
            pygame.draw.rect(screen, EDGE_LABEL_BG, rect.inflate(6, 3))
            pygame.draw.rect(screen, LEGEND_BORDER, rect.inflate(6, 3), 1)
            screen.blit(text, rect)

    occupancy = defaultdict(int)
    for position in state.anim_to.values():
        if "->" not in position:
            occupancy[position] += 1

    for name, (wx, wy) in positions.items():
        x, y = to_screen(wx, wy)
        hub = state.hubs[name]
        radius = max(8, NODE_RADIUS * camera.zoom)
        occupied = occupancy.get(name, 0)

        pygame.draw.circle(screen, _hub_color(hub), (x, y), radius)
        if hub.zone_type == "restricted":
            pygame.draw.circle(screen, RESTRICTED_RING, (x, y), radius + 4,
                               max(1, int(2 * camera.zoom)))
        elif hub.zone_type == "priority":
            pygame.draw.circle(screen, PRIORITY_RING, (x, y), radius,
                               max(2, int(4 * camera.zoom)))
        if hub.kind == "start":
            pygame.draw.circle(screen, START_RING, (x, y), radius + 8,
                               max(2, int(3 * camera.zoom)))
        elif hub.kind == "end":
            pygame.draw.circle(screen, END_RING, (x, y), radius + 8,
                               max(2, int(3 * camera.zoom)))
        if hub.max_drones is not None and occupied >= hub.max_drones:
            pygame.draw.circle(screen, CONGESTED_RING, (x, y), radius + 7,
                               max(2, int(3 * camera.zoom)))
        pygame.draw.circle(screen, NODE_BORDER, (x, y), radius, max(1, int(2 * camera.zoom)))

        if camera.zoom >= DETAIL_FULL_ZOOM:
            _draw_label_block(screen, cache,
                              [(label_font, name),
                               (small_font, f"({hub.zone_type}) {occupied}/{hub.cap_text}")],
                              x, y + radius + 4)
        elif camera.zoom >= DETAIL_NAME_ZOOM:
            _draw_label_block(screen, cache, [(small_font, name)], x, y + radius + 4)

    arrived = 0
    for drone_id in state.drone_order:
        now = state.anim_to.get(drone_id)
        if now is None:
            continue
        before = state.anim_from.get(drone_id, now)
        try:
            x1, y1 = _resolve_world_pos(before, positions)
            x2, y2 = _resolve_world_pos(now, positions)
        except KeyError:
            continue
        if now == state.end_name:
            arrived += 1

        jx, jy = _drone_jitter(state.drone_seed[drone_id], NODE_RADIUS * 0.95)
        x, y = to_screen(x1 + (x2 - x1) * eased + jx, y1 + (y2 - y1) * eased + jy)

        focused = state.focus == drone_id
        dimmed = state.focus is not None and not focused
        radius = max(4, DRONE_RADIUS * camera.zoom * (1.5 if focused else 1.0))

        if dimmed:
            fill, border = DRONE_FADED_FILL, DRONE_FADED_BORDER
        elif now == state.end_name:
            fill, border = DRONE_DONE_FILL, DRONE_BORDER
        else:
            fill, border = DRONE_FILL, DRONE_BORDER

        pygame.draw.circle(screen, fill, (x, y), radius)
        pygame.draw.circle(screen, border, (x, y), radius, max(1, int(1.5 * camera.zoom)))
        if focused:
            pygame.draw.circle(screen, FOCUS_RING, (x, y), radius + 6,
                               max(2, int(3 * camera.zoom)))
        if radius >= 8 and not dimmed:
            text = cache.render(small_font, drone_id, DRONE_TEXT)
            screen.blit(text, text.get_rect(center=(x, y)))

    # header last, so it stays on top of the world
    pygame.draw.rect(screen, HEADER_BG, (0, 0, state.viewport_w, HEADER_H))
    run_note = f"   run {state.run_index + 1}/{state.run_count}" if state.run_count > 1 else ""
    title = title_font.render(
        f"Drone simulation - turn {state.turn}/{state.max_turn}   "
        f"arrived {arrived}/{len(state.drone_order)}   "
        f"({'playing' if state.playing else 'paused'}, "
        f"{'phase' if state.layout == LAYOUT_PHASE else 'map'} layout, "
        f"zoom {camera.zoom * 100:.0f}%){run_note}",
        True, TEXT_COLOR)
    screen.blit(title, (16, 8))

    if state.focus:
        where = state.anim_to.get(state.focus, "?").replace("->", " -> ")
        hint, color = (f"focused on D{state.focus}: {where}   "
                       f"(F next drone, SHIFT+F previous, ESC clear)"), TEXT_COLOR
    else:
        hint, color = ("SPACE play/pause   click/-> step   right-click/<- back   drag pan   "
                       "scroll/+- zoom   R fit   G layout   F focus a drone   ESC quit"), MUTED_TEXT_COLOR
        if camera.zoom < DETAIL_FULL_ZOOM:
            hint += "      (zoom in for hub names and capacities)"
    screen.blit(small_font.render(hint, True, color), (16, HEADER_H - 20))

    _draw_legend(screen, small_font, cache, state.viewport_w, HEADER_H,
                 state.focus, state.layout)


# ------------------------------------------------------------------ #
# view state
# ------------------------------------------------------------------ #

class ViewState:
    """
    Everything draw_frame needs, in one place, so switching layout or run is
    a matter of rebuilding a couple of fields rather than juggling a dozen
    loose variables through the main loop.
    """

    def __init__(self, hubs, edges, adjacency, runs, start_name, end_name, fonts):
        self.hubs = hubs
        self.edges = edges
        self.adjacency = adjacency
        self.runs = runs
        self.start_name = start_name
        self.end_name = end_name
        self.fonts = fonts
        self.cache = TextCache()

        self.levels = _levels_by_bfs(hubs, adjacency, start_name)
        self.run_index, self.run_count = 0, len(runs)
        self.layout = LAYOUT_MAP
        self.viewport_w, self.viewport_h = VIEW_W, VIEW_H

        self.drone_order = sorted({d for run in runs for snap in run for d in snap},
                                  key=int)
        self.drone_seed = {d: i for i, d in enumerate(self.drone_order)}

        self.focus, self.focus_route = None, set()
        self.playing = True

        self.rebuild_layout()
        self.select_run(0)

    # -- layout ----------------------------------------------------- #

    def rebuild_layout(self):
        if self.layout == LAYOUT_PHASE:
            self.positions, columns = phase_layout(self.adjacency, self.levels)
        else:
            self.positions, columns = map_layout(self.hubs)
        self.columns = columns
        self.edge_paths = build_edge_paths(self.edges, self.positions, columns, self.layout)

        self.content_top = min(y for _x, y in self.positions.values())
        self.content_bottom = max(y for _x, y in self.positions.values())
        self.column_x = {columns[name]: wx for name, (wx, _wy) in self.positions.items()}

        route_ys = [y for points, _kind, _cap in self.edge_paths.values() for _x, y in points]
        self.extra_top_margin = max(
            0.0, self.content_top - min(route_ys, default=self.content_top)) + 30
        self.fit_camera()

    def toggle_layout(self):
        self.layout = LAYOUT_MAP if self.layout == LAYOUT_PHASE else LAYOUT_PHASE
        self.rebuild_layout()

    def fit_camera(self):
        self.camera = _fit_camera(self.positions, self.viewport_w, self.viewport_h,
                                  self.extra_top_margin)

    # -- run and turn ----------------------------------------------- #

    def select_run(self, index):
        self.run_index = index % max(self.run_count, 1)
        self.snapshots = self.runs[self.run_index]
        self.max_turn = len(self.snapshots) - 1
        self.turn = 0
        self.anim_from = self.anim_to = self.snapshots[0]
        self.anim_t = 1.0
        self.refresh_focus_route()

    def goto_turn(self, turn):
        turn = max(0, min(turn, self.max_turn))
        if turn == self.turn:
            return
        self.anim_from = self.snapshots[self.turn]
        self.anim_to = self.snapshots[turn]
        self.anim_t = 0.0
        self.turn = turn

    # -- focus ------------------------------------------------------ #

    def cycle_focus(self, step):
        if not self.drone_order:
            return
        if self.focus is None:
            index = 0 if step > 0 else len(self.drone_order) - 1
        else:
            index = self.drone_order.index(self.focus) + step
            if not 0 <= index < len(self.drone_order):
                self.focus, self.focus_route = None, set()
                return
        self.focus = self.drone_order[index]
        self.refresh_focus_route()

    def refresh_focus_route(self):
        self.focus_route = (_drone_route_edges(self.snapshots, self.focus)
                            if self.focus else set())


# ------------------------------------------------------------------ #
# entry point
# ------------------------------------------------------------------ #

def visualise(path, fps=2.0, out_dir=None, gif_name=None,
              window_title=None, start_layout=LAYOUT_MAP):
    """Open the window and animate the log at `path`."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError as exc:
        print(f"[drone_viz] cannot read {path}: {exc}")
        return 1

    hubs, edges, nb_drones, move_start = parse_map(lines)
    if not hubs:
        print(f"[drone_viz] no hubs found in {path} - is this the right file?")
        return 1

    adjacency = defaultdict(set)
    for name1, name2, _capacity in edges:
        adjacency[name1].add(name2)
        adjacency[name2].add(name1)

    start_name = next((h.name for h in hubs.values() if h.kind == "start"), None)
    end_name = next((h.name for h in hubs.values() if h.kind == "end"), None)
    if start_name is None:
        print("[drone_viz] the map has no start_hub, nothing to animate from")
        return 1

    runs = parse_runs(lines[move_start:], hubs, adjacency, nb_drones, start_name)
    if not runs:
        print("[drone_viz] no drone moves found after the map section")
        return 1

    print(f"[drone_viz] {len(hubs)} hubs, {len(edges)} links, {nb_drones} drones")
    for i, run in enumerate(runs):
        last = run[-1]
        landed = sum(1 for p in last.values() if p == end_name)
        print(f"[drone_viz]   run {i + 1}: {len(run) - 1} turns, "
              f"{landed}/{len(last)} drones at the goal")
    if len(runs) > 1:
        print(f"[drone_viz] {len(runs)} runs in this log - press TAB to switch between them")

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        for stale in glob.glob(os.path.join(out_dir, "frame_*.png")):
            os.remove(stale)

    pygame.init()
    pygame.display.set_caption(window_title or f"Fly-in - {os.path.basename(path)}")
    screen = pygame.display.set_mode((VIEW_W, VIEW_H + HEADER_H), pygame.RESIZABLE)
    clock = pygame.time.Clock()
    fonts = (
        pygame.font.SysFont("arial", 22, bold=True),
        pygame.font.SysFont("arial", 16),
        pygame.font.SysFont("arial", 14),
    )

    state = ViewState(hubs, edges, adjacency, runs, start_name, end_name, fonts)
    if start_layout != state.layout:
        state.toggle_layout()

    # never advance faster than the settle-in animation can play, or a turn's
    # movement (and its saved PNG) would be skipped outright
    turn_interval = max(1.0 / fps if fps > 0 else 1.0, ANIM_DURATION)
    turn_timer = 0.0
    saved_turns, saved_frames = set(), []
    mouse_down, dragged = None, False
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                state.viewport_w = max(event.w, 400)
                state.viewport_h = max(event.h - HEADER_H, 240)
                screen = pygame.display.set_mode(
                    (state.viewport_w, state.viewport_h + HEADER_H), pygame.RESIZABLE)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if state.focus:
                        state.focus, state.focus_route = None, set()
                    else:
                        running = False
                elif event.key == pygame.K_SPACE:
                    state.playing = not state.playing
                elif event.key in (pygame.K_RIGHT, pygame.K_n):
                    state.goto_turn(state.turn + 1)
                    state.playing = False
                elif event.key in (pygame.K_LEFT, pygame.K_p):
                    state.goto_turn(state.turn - 1)
                    state.playing = False
                elif event.key == pygame.K_HOME:
                    state.goto_turn(0)
                    state.playing = False
                elif event.key == pygame.K_END:
                    state.goto_turn(state.max_turn)
                    state.playing = False
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    _zoom_at(state.camera,
                             (state.viewport_w / 2, HEADER_H + state.viewport_h / 2),
                             1.2, state.viewport_w, state.viewport_h, HEADER_H)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    _zoom_at(state.camera,
                             (state.viewport_w / 2, HEADER_H + state.viewport_h / 2),
                             1 / 1.2, state.viewport_w, state.viewport_h, HEADER_H)
                elif event.key in (pygame.K_r, pygame.K_0):
                    state.fit_camera()
                elif event.key == pygame.K_g:
                    state.toggle_layout()
                elif event.key == pygame.K_f:
                    state.cycle_focus(-1 if event.mod & pygame.KMOD_SHIFT else 1)
                elif event.key == pygame.K_TAB and state.run_count > 1:
                    state.select_run(state.run_index + 1)
                    saved_turns, saved_frames = set(), []

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_down, dragged = event.pos, False
                elif event.button == 3:
                    state.goto_turn(state.turn - 1)
                    state.playing = False

            elif event.type == pygame.MOUSEMOTION:
                if mouse_down is not None and event.buttons[0]:
                    dx, dy = event.rel
                    if abs(dx) > 2 or abs(dy) > 2:
                        dragged = True
                    state.camera.x -= dx / state.camera.zoom
                    state.camera.y -= dy / state.camera.zoom

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if not dragged:
                        state.goto_turn(state.turn + 1)
                        state.playing = False
                    mouse_down = None

            elif event.type == pygame.MOUSEWHEEL:
                _zoom_at(state.camera, pygame.mouse.get_pos(), 1.1 ** event.y,
                         state.viewport_w, state.viewport_h, HEADER_H)

        if state.playing:
            turn_timer += dt
            if turn_timer >= turn_interval:
                turn_timer = 0.0
                if state.turn < state.max_turn:
                    state.goto_turn(state.turn + 1)
                else:
                    state.playing = False

        if state.anim_t < 1.0:
            state.anim_t = min(1.0, state.anim_t + dt / ANIM_DURATION)

        draw_frame(screen, state)
        pygame.display.flip()

        if out_dir and state.anim_t >= 1.0 and state.turn not in saved_turns:
            frame_path = os.path.join(out_dir, f"frame_{state.turn:03d}.png")
            pygame.image.save(screen, frame_path)
            saved_turns.add(state.turn)
            saved_frames.append(frame_path)

    pygame.quit()

    if out_dir and saved_frames:
        print(f"[drone_viz] {len(saved_frames)} snapshots written to {out_dir}/")
        if gif_name:
            try:
                from PIL import Image
                frames = [Image.open(p) for p in sorted(saved_frames)]
                frames[0].save(gif_name, save_all=True, append_images=frames[1:],
                               duration=int(1000 / fps) if fps > 0 else 900, loop=0)
                print(f"[drone_viz] animation saved: {gif_name}")
            except ImportError:
                print("[drone_viz] pillow not installed, skipping the gif "
                      "(pip install pillow)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Animate a Fly-in drone simulation log with pygame.")
    parser.add_argument("log", nargs="?", default="log.txt",
                        help="path to the log file (default: log.txt)")
    parser.add_argument("--fps", type=float, default=2.0,
                        help="turns per second during auto-play (default: 2)")
    parser.add_argument("--snapshots", nargs="?", const="snapshots", default=None,
                        metavar="DIR",
                        help="also save one PNG per turn into DIR (default dir: snapshots)")
    parser.add_argument("--gif", nargs="?", const="drone_simulation.gif", default=None,
                        metavar="FILE",
                        help="stitch the snapshots into an animated gif (implies --snapshots)")
    parser.add_argument("--phase", action="store_true",
                        help="start in the BFS phase layout instead of the map's own coordinates")
    args = parser.parse_args(argv)

    out_dir = args.snapshots or ("snapshots" if args.gif else None)
    return visualise(args.log, fps=args.fps, out_dir=out_dir, gif_name=args.gif,
                     start_layout=LAYOUT_PHASE if args.phase else LAYOUT_MAP)


if __name__ == "__main__":
    sys.exit(main())



# with open(map_file, "r") as file1:
#             content = file1.read()

#         with open("log.txt", "w") as file:
#             text = "\n".join(vis.recordes)
#             file.write(content)
#             file.write(text)