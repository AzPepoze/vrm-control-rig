"""Finger chain detection and driver logic."""

import re
import bpy
from ..constants import (
    P_CTRL, 
    FINGER_CURL_DRIVER_TAG,
    B_THUMB_CURL_L,
    B_INDEX_CURL_L,
    B_MIDDLE_CURL_L,
    B_RING_CURL_L,
    B_LITTLE_CURL_L,
    B_THUMB_CURL_R,
    B_INDEX_CURL_R,
    B_MIDDLE_CURL_R,
    B_RING_CURL_R,
    B_LITTLE_CURL_R,
)

FINGER_SPECS = (
    ("Thumb", "thumb"),
    ("Index", "index"),
    ("Middle", "middle"),
    ("Ring", "ring"),
    ("Little", "little"),
)

FINGER_CONTROLS = (
    B_THUMB_CURL_L,
    B_INDEX_CURL_L,
    B_MIDDLE_CURL_L,
    B_RING_CURL_L,
    B_LITTLE_CURL_L,
    B_THUMB_CURL_R,
    B_INDEX_CURL_R,
    B_MIDDLE_CURL_R,
    B_RING_CURL_R,
    B_LITTLE_CURL_R,
)

def detect_finger_chains(bones, bone_names):
    """Identify source finger bones and map them to control bones."""
    by_norm = {_norm_name(bone.name): bone.name for bone in bones}
    chains = {}

    for side in ("L", "R"):
        for display_name, finger_name in FINGER_SPECS:
            chain = []
            for index, segment_name in enumerate(("proximal", "intermediate", "distal"), start=1):
                aliases = (
                    f"left{finger_name}{segment_name}" if side == "L" else f"right{finger_name}{segment_name}",
                    f"left{finger_name}{index}" if side == "L" else f"right{finger_name}{index}",
                    f"l{finger_name}{segment_name}" if side == "L" else f"r{finger_name}{segment_name}",
                    f"l{finger_name}{index}" if side == "L" else f"r{finger_name}{index}",
                    f"j_bip_{side.lower()}_{finger_name}{index}",
                    f"j_bip_{side.lower()}_{finger_name}_{index}",
                    f"j_bip_{side.lower()}_{finger_name}{segment_name}",
                    f"{finger_name}{index}.{side.lower()}",
                    f"{finger_name}{segment_name}.{side.lower()}",
                )
                found = _find_normalized_bone(by_norm, aliases)
                if found:
                    chain.append(found)
            if chain:
                # Map logical finger bone to actual bone name
                logical_name = f"{P_CTRL}{display_name}_Curl.{side}"
                actual_name = bone_names[logical_name]
                chains[actual_name] = chain

    return chains

def add_finger_curl_driver(armature_object, pose_bone, control_name):
    """Add a scripted driver to rotate finger bones based on control scale."""
    pose_bone.rotation_mode = "XYZ"
    try:
        fcurve = pose_bone.driver_add("rotation_euler", 2)
    except (TypeError, RuntimeError, ValueError):
        return False

    driver = fcurve.driver
    driver.type = "SCRIPTED"
    driver.expression = f"-({FINGER_CURL_DRIVER_TAG}_sz - 1.0) * 0.45"
    variable = driver.variables.new()
    variable.name = FINGER_CURL_DRIVER_TAG + "_sz"
    variable.type = "TRANSFORMS"
    target = variable.targets[0]
    target.id = armature_object
    target.bone_target = control_name
    target.transform_type = "SCALE_Z"
    target.transform_space = "LOCAL_SPACE"
    return True

def _find_normalized_bone(by_norm, aliases):
    candidates = [_norm_name(alias) for alias in aliases]
    for candidate in candidates:
        if candidate in by_norm:
            return by_norm[candidate]
    for bone_norm, original_name in by_norm.items():
        for candidate in candidates:
            if bone_norm.endswith(candidate):
                return original_name
    return None

def _norm_name(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())
