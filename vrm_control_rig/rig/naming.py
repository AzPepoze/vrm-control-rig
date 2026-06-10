"""Bone naming and obfuscation logic."""

from ..constants import GENERATED_BONES

def get_bone_names(settings):
    """Return a mapping of logical bone constants to their actual names."""
    mapping = {}
    for name in GENERATED_BONES:
        if settings.use_random_names:
            # Join characters with hyphens to prevent auto-mapping by external tools.
            # Example: 'Hand.L' -> 'h-a-n-d-l'
            clean = "".join(c for c in name.lower() if c.isalnum())
            mapping[name] = "-".join(list(clean))
        else:
            mapping[name] = name
    return mapping
