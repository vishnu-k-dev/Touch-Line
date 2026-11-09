"""Shot context from a StatsBomb 360 freeze-frame.

Coordinates are the event coordinates (120 x 80 pitch, attacking toward x=120; verified: the freeze-frame actor's
location equals the event location). Defenders are opponents that are not the goalkeeper. A freeze-frame lists only
the players in the camera's `visible_area`, and even with the whole lane visible it does not always list every
player (measured: 11 of 25 blocked shots show zero defenders in the lane). So `defenders_in_cone` is a LOWER BOUND
on the defenders in the lane: a positive count is reliable, a zero does not prove a clear lane. It still tracks
chance quality (clear-lane shots average ~0.18 xG, shots with 2+ visible defenders ~0.05)."""

from math import hypot

GOAL_POSTS = ((120.0, 36.0), (120.0, 44.0))  # goal is 8 yards wide, centred on y=40
# The visible-area polygon runs exactly to the goal line, so a post on the edge fails a point-in-polygon test.
# Probe half a yard inside instead. ponytail: 0.5 yd tolerance, tighten if a provider changes the polygon.
_PROBE_X = 119.5


def _cross(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def in_triangle(p, a, b, c) -> bool:
    """Strictly inside triangle abc (points on an edge do not count)."""
    d1, d2, d3 = _cross(p, a, b), _cross(p, b, c), _cross(p, c, a)
    return (d1 > 0 and d2 > 0 and d3 > 0) or (d1 < 0 and d2 < 0 and d3 < 0)


def in_polygon(p, flat: list[float]) -> bool:
    """Ray casting; `flat` is [x1, y1, x2, y2, ...] as StatsBomb stores visible_area."""
    pts = list(zip(flat[0::2], flat[1::2]))
    x, y = p
    inside = False
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def shot_context(shot_xy: tuple[float, float], frame: dict) -> dict:
    opponents = [pl["location"] for pl in frame["freeze_frame"] if not pl["teammate"] and not pl["keeper"]]
    lane = (shot_xy, *GOAL_POSTS)
    probes = (shot_xy, (_PROBE_X, GOAL_POSTS[0][1]), (_PROBE_X, GOAL_POSTS[1][1]))
    return {
        "defenders_in_cone": sum(in_triangle(o, *lane) for o in opponents),
        "cone_visible": all(in_polygon(q, frame["visible_area"]) for q in probes),
        "nearest_defender": round(min(hypot(o[0] - shot_xy[0], o[1] - shot_xy[1]) for o in opponents), 1) if opponents else None,
    }
