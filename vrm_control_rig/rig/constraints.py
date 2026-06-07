"""Constraint creation logic."""

import bpy
from ..constants import (
    ADDON_ID,
    IK_CONSTRAINT_NAME,
    ROOT_CONSTRAINT_NAME,
    ROTATION_CONSTRAINT_NAME,
    EYE_CONSTRAINT_NAME,
    B_ROOT,
    B_HIPS,
    B_EYE_TARGET_L,
    B_EYE_TARGET_R,
    B_HAND_IK_L,
    B_HAND_IK_R,
    B_FOOT_IK_L,
    B_FOOT_IK_R,
    B_ELBOW_POLE_L,
    B_ELBOW_POLE_R,
    B_KNEE_POLE_L,
    B_KNEE_POLE_R,
)
from ..logs import log_line
from ..utils import tag_generated
from .fingers import detect_finger_chains, add_finger_curl_driver

def create_constraints(context, armature_object, mapping, before_matrices, bone_names):
    """Create all rig constraints in POSE mode."""
    _add_root_constraint(armature_object, mapping["hips"], bone_names[B_HIPS])
    context.view_layer.update()
    
    _add_ik_constraint(
        context,
        armature_object,
        mapping["lower_arm.L"],
        bone_names[B_HAND_IK_L],
        bone_names[B_ELBOW_POLE_L],
        (mapping["upper_arm.L"], mapping["lower_arm.L"], mapping["hand.L"]),
        before_matrices,
    )
    _add_ik_constraint(
        context,
        armature_object,
        mapping["lower_arm.R"],
        bone_names[B_HAND_IK_R],
        bone_names[B_ELBOW_POLE_R],
        (mapping["upper_arm.R"], mapping["lower_arm.R"], mapping["hand.R"]),
        before_matrices,
    )
    _add_rotation_constraint(armature_object, mapping["hand.L"], bone_names[B_HAND_IK_L])
    _add_rotation_constraint(armature_object, mapping["hand.R"], bone_names[B_HAND_IK_R])
    _add_rotation_constraint(armature_object, mapping["foot.L"], bone_names[B_FOOT_IK_L])
    _add_rotation_constraint(armature_object, mapping["foot.R"], bone_names[B_FOOT_IK_R])
    
    _add_eye_constraints(context, armature_object, mapping, bone_names)
    _add_finger_drivers(context, armature_object, bone_names)
    
    _add_ik_constraint(
        context,
        armature_object,
        mapping["lower_leg.L"],
        bone_names[B_FOOT_IK_L],
        bone_names[B_KNEE_POLE_L],
        (mapping["upper_leg.L"], mapping["lower_leg.L"], mapping["foot.L"]),
        before_matrices,
    )
    _add_ik_constraint(
        context,
        armature_object,
        mapping["lower_leg.R"],
        bone_names[B_FOOT_IK_R],
        bone_names[B_KNEE_POLE_R],
        (mapping["upper_leg.R"], mapping["lower_leg.R"], mapping["foot.R"]),
        before_matrices,
    )

def _add_root_constraint(armature_object, bone_name, target_bone):
    pose_bone = armature_object.pose.bones[bone_name]
    constraint = pose_bone.constraints.new(type="COPY_TRANSFORMS")
    constraint.name = ROOT_CONSTRAINT_NAME
    constraint.target = armature_object
    constraint.subtarget = target_bone
    constraint.target_space = "LOCAL_WITH_PARENT"
    constraint.owner_space = "LOCAL_WITH_PARENT"
    tag_generated(constraint)

def _add_ik_constraint(context, armature_object, bone_name, target_bone, pole_bone, affected_bones, before_matrices):
    pose_bone = armature_object.pose.bones[bone_name]
    chain_count = _count_chain_to_bone(armature_object.data, bone_name, affected_bones[0])
    constraint = pose_bone.constraints.new(type="IK")
    constraint.name = IK_CONSTRAINT_NAME
    constraint.target = armature_object
    constraint.subtarget = target_bone
    constraint.pole_target = armature_object
    constraint.pole_subtarget = pole_bone
    constraint.chain_count = chain_count
    constraint.use_rotation = False
    tag_generated(constraint)
    log_line(
        context,
        f"  IK on {bone_name}: chain_count={chain_count} "
        f"(from {bone_name} up to {affected_bones[0]})",
    )
    _calibrate_pole_angle(context, armature_object, constraint, pole_bone, affected_bones, before_matrices)

def _add_rotation_constraint(armature_object, bone_name, target_bone):
    pose_bone = armature_object.pose.bones.get(bone_name)
    if not pose_bone:
        return
    constraint = pose_bone.constraints.new(type="COPY_ROTATION")
    constraint.name = ROTATION_CONSTRAINT_NAME
    constraint.target = armature_object
    constraint.subtarget = target_bone
    constraint.target_space = "POSE"
    constraint.owner_space = "POSE"
    tag_generated(constraint)

def _add_eye_constraints(context, armature_object, mapping, bone_names):
    added = 0
    for side in ("L", "R"):
        source_key = f"eye.{side}"
        logical_target = B_EYE_TARGET_L if side == "L" else B_EYE_TARGET_R
        actual_target = bone_names[logical_target]
        if source_key not in mapping or actual_target not in armature_object.pose.bones:
            continue
        pose_bone = armature_object.pose.bones.get(mapping[source_key])
        if not pose_bone:
            continue
        constraint = pose_bone.constraints.new(type="DAMPED_TRACK")
        constraint.name = EYE_CONSTRAINT_NAME
        constraint.target = armature_object
        constraint.subtarget = actual_target
        _set_eye_track_axis(constraint, pose_bone)
        tag_generated(constraint)
        added += 1

    if added:
        log_line(context, f"Added {added} eye tracking constraints.")
    else:
        log_line(context, "No eye bones detected; skipped eye tracking constraints.")

def _add_finger_drivers(context, armature_object, bone_names):
    added = 0
    chains = detect_finger_chains(armature_object.data.bones, bone_names)
    for actual_control_name, chain in chains.items():
        if actual_control_name not in armature_object.pose.bones:
            continue
        
        # Add rotation constraint to the proximal bone so the controller can orient the finger.
        proximal_bone = armature_object.pose.bones.get(chain[0])
        if proximal_bone:
            # Rotation in POSE space to perfectly follow the controller's armature-space orientation.
            rot_const = proximal_bone.constraints.new(type="COPY_ROTATION")
            rot_const.name = ROTATION_CONSTRAINT_NAME
            rot_const.target = armature_object
            rot_const.subtarget = actual_control_name
            rot_const.target_space = "POSE"
            rot_const.owner_space = "POSE"
            tag_generated(rot_const)

        for bone_name in chain:
            pose_bone = armature_object.pose.bones.get(bone_name)
            if not pose_bone:
                continue
            if add_finger_curl_driver(armature_object, pose_bone, actual_control_name):
                added += 1

    if added:
        log_line(context, f"Added {added} finger curl scale drivers and orientation constraints.")
    else:
        log_line(context, "No finger chains detected; skipped finger curl drivers.")

def _count_chain_to_bone(armature_data, bone_name, root_bone_name):
    """Count bones from bone_name up the parent chain to root_bone_name (inclusive)."""
    bones = armature_data.bones
    bone = bones.get(bone_name)
    target = bones.get(root_bone_name)
    if not bone or not target:
        return 2
    count = 0
    current = bone
    while current and count < 100:
        count += 1
        if current == target:
            return count
        current = current.parent
    return 2

def _set_eye_track_axis(constraint, pose_bone):
    direction = pose_bone.bone.tail_local - pose_bone.bone.head_local
    axis_values = {
        "TRACK_X": abs(direction.x),
        "TRACK_Y": abs(direction.y),
        "TRACK_Z": abs(direction.z),
    }
    constraint.track_axis = max(axis_values, key=axis_values.get)

def _calibrate_pole_angle(context, armature_object, constraint, pole_bone_name, affected_bones, before_matrices):
    """Pick a pole angle that minimally changes the source chain on creation."""
    import math
    best_angle = 0.0
    best_score = None
    samples = [(-math.pi + (math.tau * index / 64.0)) for index in range(65)]

    for angle in samples:
        constraint.pole_angle = angle
        context.view_layer.update()
        score = _matrix_delta_score(armature_object, affected_bones, before_matrices)
        if best_score is None or score < best_score:
            best_score = score
            best_angle = angle

    constraint.pole_angle = best_angle
    context.view_layer.update()
    log_line(
        context,
        f"  {constraint.name} on {constraint.id_data.name if hasattr(constraint, 'id_data') else '<unknown>'} "
        f"target={constraint.subtarget} pole={pole_bone_name} calibrated_pole_angle={best_angle:.5f} "
        f"score={best_score:.8f}",
    )

def _matrix_delta_score(armature_object, bone_names, before_matrices):
    score = 0.0
    for bone_name in bone_names:
        pose_bone = armature_object.pose.bones.get(bone_name)
        before = before_matrices.get(bone_name)
        if not pose_bone or before is None:
            continue
        delta = pose_bone.matrix - before
        for row in delta:
            for value in row:
                score += abs(value)
    return score
