"""Bake constrained control-rig motion onto original VRM bones."""

import bpy

from .constants import GENERATED_BONES
from .detection import detect_humanoid_bones
from .utils import ObjectMode, remove_generated_constraints, remove_generated_fcurves


def bake_to_vrm_skeleton(context, armature_object, frame_start, frame_end, *, remove_constraints=False):
    mapping, _missing = detect_humanoid_bones(armature_object)
    source_bones = [name for name in mapping.values() if name in armature_object.pose.bones]

    if frame_end < frame_start:
        raise ValueError("Bake end frame must be greater than or equal to start frame.")
    if not source_bones:
        raise ValueError("No VRM humanoid bones were detected to bake.")

    with ObjectMode(context, armature_object, "POSE"):
        bpy.ops.pose.select_all(action="DESELECT")
        for pose_bone in armature_object.pose.bones:
            _set_pose_bone_selected(pose_bone, pose_bone.name in source_bones)
        armature_object.data.bones.active = armature_object.data.bones[source_bones[0]]

        bpy.ops.nla.bake(
            frame_start=frame_start,
            frame_end=frame_end,
            only_selected=True,
            visual_keying=True,
            clear_constraints=False,
            clear_parents=False,
            use_current_action=True,
            bake_types={"POSE"},
        )

    remove_generated_fcurves(armature_object)
    if remove_constraints:
        remove_generated_constraints(armature_object)


def remove_control_animation(armature_object):
    """Remove animation channels for generated bones so exports only carry VRM bones."""

    remove_generated_fcurves(armature_object)
    for name in GENERATED_BONES:
        pose_bone = armature_object.pose.bones.get(name)
        if pose_bone:
            pose_bone.matrix_basis.identity()


def _set_pose_bone_selected(pose_bone, selected):
    """Select a pose bone across Blender selection API changes."""

    if hasattr(pose_bone, "select"):
        pose_bone.select = selected
    elif hasattr(pose_bone.bone, "select"):
        pose_bone.bone.select = selected
