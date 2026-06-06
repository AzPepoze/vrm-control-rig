"""VRM humanoid bone detection.

The VRM add-on and DCC importers commonly preserve humanoid intent in bone
names, but exact spelling differs between VRM0, VRM1, Unity, and Japanese VRM
templates. Detection intentionally stays name-based so this addon does not
depend on a specific VRM importer package.
"""

import re

from .constants import HUMANOID_BONES, REQUIRED_BONES


def _norm(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


ALIASES = {
    "hips": ("hips", "hip", "pelvis", "j_bip_c_hips", "j_bip_c_hip"),
    "spine": ("spine", "spine1", "j_bip_c_spine"),
    "chest": ("chest", "spine2", "j_bip_c_chest"),
    "upper_chest": ("upperchest", "upper_chest", "spine3", "j_bip_c_upperchest"),
    "neck": ("neck", "j_bip_c_neck"),
    "head": ("head", "j_bip_c_head"),
    "upper_arm.L": (
        "upperarm.l",
        "upper_arm.l",
        "leftupperarm",
        "leftarm",
        "j_bip_l_upperarm",
    ),
    "lower_arm.L": (
        "lowerarm.l",
        "lower_arm.l",
        "leftlowerarm",
        "leftforearm",
        "j_bip_l_lowerarm",
    ),
    "hand.L": ("hand.l", "left hand", "lefthand", "j_bip_l_hand"),
    "upper_arm.R": (
        "upperarm.r",
        "upper_arm.r",
        "rightupperarm",
        "rightarm",
        "j_bip_r_upperarm",
    ),
    "lower_arm.R": (
        "lowerarm.r",
        "lower_arm.r",
        "rightlowerarm",
        "rightforearm",
        "j_bip_r_lowerarm",
    ),
    "hand.R": ("hand.r", "right hand", "righthand", "j_bip_r_hand"),
    "upper_leg.L": (
        "upperleg.l",
        "upper_leg.l",
        "leftupperleg",
        "leftthigh",
        "j_bip_l_upperleg",
    ),
    "lower_leg.L": (
        "lowerleg.l",
        "lower_leg.l",
        "leftlowerleg",
        "leftshin",
        "leftcalf",
        "j_bip_l_lowerleg",
    ),
    "foot.L": ("foot.l", "leftfoot", "j_bip_l_foot"),
    "upper_leg.R": (
        "upperleg.r",
        "upper_leg.r",
        "rightupperleg",
        "rightthigh",
        "j_bip_r_upperleg",
    ),
    "lower_leg.R": (
        "lowerleg.r",
        "lower_leg.r",
        "rightlowerleg",
        "rightshin",
        "rightcalf",
        "j_bip_r_lowerleg",
    ),
    "foot.R": ("foot.r", "rightfoot", "j_bip_r_foot"),
}


def detect_humanoid_bones(armature_object):
    """Return (mapping, missing_required) for an armature object."""

    bones = armature_object.data.bones
    by_norm = {_norm(bone.name): bone.name for bone in bones}
    mapping = {}

    for canonical in HUMANOID_BONES:
        candidates = [_norm(alias) for alias in ALIASES.get(canonical, (canonical,))]
        found = None
        for candidate in candidates:
            if candidate in by_norm:
                found = by_norm[candidate]
                break

        if found is None:
            found = _suffix_match(by_norm, candidates)

        if found is not None:
            mapping[canonical] = found

    missing = [name for name in REQUIRED_BONES if name not in mapping]
    return mapping, missing


def _suffix_match(by_norm, candidates):
    """Handle common prefixes such as Armature|Hips or metarig:upper_arm.L."""

    for bone_norm, original_name in by_norm.items():
        for candidate in candidates:
            if bone_norm.endswith(candidate):
                return original_name
    return None


def format_missing_bones(missing):
    return ", ".join(missing) if missing else ""

