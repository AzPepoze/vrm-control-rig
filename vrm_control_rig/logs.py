"""Diagnostic logging for rig generation."""

from datetime import datetime
from math import degrees

import bpy

LOG_TEXT_NAME = "VRM Control Rig Log"


def log_enabled(context):
    return bool(context.scene.vrm_control_rig.enable_diagnostics)


def clear_log():
    text = bpy.data.texts.get(LOG_TEXT_NAME)
    if text:
        text.clear()


def log_line(context, message):
    if not log_enabled(context):
        return

    text = bpy.data.texts.get(LOG_TEXT_NAME)
    if text is None:
        text = bpy.data.texts.new(LOG_TEXT_NAME)

    line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
    text.write(line + "\n")
    print(line)


def log_mapping(context, mapping, missing):
    log_line(context, "Detected humanoid bone mapping:")
    for key in sorted(mapping):
        log_line(context, f"  {key} -> {mapping[key]}")
    if missing:
        log_line(context, "Missing required bones: " + ", ".join(missing))


def snapshot_pose(armature_object, bone_names):
    snapshot = {}
    for bone_name in bone_names:
        pose_bone = armature_object.pose.bones.get(bone_name)
        data_bone = armature_object.data.bones.get(bone_name)
        if not pose_bone or not data_bone:
            continue

        loc = pose_bone.matrix.to_translation()
        rot = pose_bone.matrix.to_euler()
        rest_head = data_bone.head_local
        rest_tail = data_bone.tail_local
        snapshot[bone_name] = {
            "pose_loc": (loc.x, loc.y, loc.z),
            "pose_rot": tuple(degrees(value) for value in rot),
            "rest_head": (rest_head.x, rest_head.y, rest_head.z),
            "rest_tail": (rest_tail.x, rest_tail.y, rest_tail.z),
        }
    return snapshot


def log_snapshot(context, title, snapshot):
    log_line(context, title)
    if not snapshot:
        log_line(context, "  <no bones>")
        return

    for bone_name in sorted(snapshot):
        data = snapshot[bone_name]
        log_line(
            context,
            "  "
            + bone_name
            + " pose_loc="
            + _format_vec(data["pose_loc"])
            + " pose_rot_deg="
            + _format_vec(data["pose_rot"])
            + " rest_head="
            + _format_vec(data["rest_head"])
            + " rest_tail="
            + _format_vec(data["rest_tail"]),
        )


def log_delta(context, title, before, after):
    log_line(context, title)
    common = sorted(set(before).intersection(after))
    if not common:
        log_line(context, "  <no common bones>")
        return

    for bone_name in common:
        loc_before = before[bone_name]["pose_loc"]
        loc_after = after[bone_name]["pose_loc"]
        rot_before = before[bone_name]["pose_rot"]
        rot_after = after[bone_name]["pose_rot"]
        loc_delta = tuple(loc_after[i] - loc_before[i] for i in range(3))
        rot_delta = tuple(rot_after[i] - rot_before[i] for i in range(3))
        log_line(
            context,
            "  "
            + bone_name
            + " delta_loc="
            + _format_vec(loc_delta)
            + " delta_rot_deg="
            + _format_vec(rot_delta),
        )


def _format_vec(values):
    return "(" + ", ".join(f"{value:.5f}" for value in values) + ")"

