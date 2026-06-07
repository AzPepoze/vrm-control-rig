"""Bone naming and randomization logic."""

import uuid
from ..constants import GENERATED_BONES

def get_bone_names(settings):
    """Return a mapping of logical bone constants to their actual names."""
    mapping = {}
    for name in GENERATED_BONES:
        if settings.use_random_names:
            # Use a prefix that Godot is highly unlikely to map to humanoid.
            mapping[name] = f"vcr_{uuid.uuid4().hex[:8]}"
        else:
            mapping[name] = name
    return mapping
