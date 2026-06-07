"""Rig-specific utility helpers."""

from mathutils import Vector

def marker(origin, length):
    """Return a placement dictionary for a vertical marker bone."""
    return {"head": origin, "tail": origin + Vector((0, 0, length))}

def vertical(center, length):
    """Return a placement dictionary for a centered vertical bone."""
    half = length * 0.5
    return {"head": center - Vector((0, 0, half)), "tail": center + Vector((0, 0, half))}

def matching_or_vertical(head, tail, fallback_length):
    """Return bone placement matching source if long enough, else vertical fallback."""
    if (tail - head).length > 0.0001:
        return {"head": head, "tail": tail}
    return vertical(head, fallback_length)

def average_eye_forward(bones, mapping):
    """Calculate the average forward direction of eye bones."""
    directions = []
    for side in ("L", "R"):
        key = f"eye.{side}"
        if key in mapping:
            eye = bones[mapping[key]]
            direction = eye.tail_local - eye.head_local
            if direction.length > 0.0001:
                directions.append(direction.normalized())
    if not directions:
        return Vector((0, -1, 0))
    forward = sum(directions, Vector((0, 0, 0)))
    if forward.length < 0.0001:
        return Vector((0, -1, 0))
    return forward.normalized()
