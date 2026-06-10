"""Pose mode alignment and pre-bend logic."""

import math
import bpy
from mathutils import Matrix, Vector
from ..constants import (
    B_ROOT,
    B_HIPS,
    B_EYES,
    B_EYE_TARGET_L,
    B_EYE_TARGET_R,
    B_HAND_IK_L,
    B_HAND_IK_R,
    B_FOOT_IK_L,
    B_FOOT_IK_R,
    B_HAND_IK_MCH_ROOT_L,
    B_HAND_IK_MCH_ROOT_R,
    B_FOOT_IK_MCH_ROOT_L,
    B_FOOT_IK_MCH_ROOT_R,
    B_ELBOW_POLE_L,
    B_ELBOW_POLE_R,
    B_KNEE_POLE_L,
    B_KNEE_POLE_R,
    P_MCH,
)
from ..logs import log_line
from .fingers import detect_finger_chains
from .utils import average_eye_forward, marker

def align_controls_to_current_pose(context, armature_object, mapping, scale, bone_names):
    """Initialize generated controls from the current pose before constraints run."""

    log_line(context, "Aligning generated controls to current source pose before adding constraints.")
    context.view_layer.update()

    root = armature_object.pose.bones.get(bone_names[B_ROOT])
    from .source import _source_root_bone
    source_root = _source_root_bone(armature_object.data.bones, mapping)
    source_root_pose = armature_object.pose.bones.get(source_root.name) if source_root else None
    if root and source_root_pose:
        root.matrix = source_root_pose.matrix.copy()
        log_line(context, f"  {bone_names[B_ROOT]} aligned to {source_root_pose.name} pose matrix.")
    elif root:
        log_line(context, f"  {bone_names[B_ROOT]} kept at generated floor/root placement.")

    for logical_name, source_key in (
        (B_HIPS, "hips"),
        (B_HAND_IK_L, "hand.L"),
        (B_HAND_IK_R, "hand.R"),
        (B_FOOT_IK_L, "foot.L"),
        (B_FOOT_IK_R, "foot.R"),
    ):
        actual_name = bone_names[logical_name]
        target = armature_object.pose.bones.get(actual_name)
        source = armature_object.pose.bones.get(mapping[source_key])
        if target and source:
            _set_pose_from_source(target, source, source.head)
            log_line(context, f"  {actual_name} aligned to {source.name} pose head and rotation.")
            
            # Sync the space-switching MCH bone immediately
            mch_map = {
                B_HAND_IK_L: B_HAND_IK_MCH_ROOT_L,
                B_HAND_IK_R: B_HAND_IK_MCH_ROOT_R,
                B_FOOT_IK_L: B_FOOT_IK_MCH_ROOT_L,
                B_FOOT_IK_R: B_FOOT_IK_MCH_ROOT_R,
            }
            mch_logical = mch_map.get(logical_name)
            if mch_logical:
                mch_name = bone_names.get(mch_logical)
                mch_pb = armature_object.pose.bones.get(mch_name) if mch_name else None
                if mch_pb:
                    # Update view layer to ensure target.matrix is fresh after parent/source alignment
                    context.view_layer.update()
                    mch_pb.matrix = target.matrix.copy()
                    log_line(context, f"  {mch_name} (MCH) synced to {actual_name} pose.")
                else:
                    log_line(context, f"  Warning: Could not find MCH bone {mch_name} for {actual_name}")

    context.view_layer.update()
    unit = _pose_unit(armature_object, mapping, scale)
    _align_finger_controls_to_current_pose(context, armature_object, unit, bone_names)

    eyes = armature_object.pose.bones.get(bone_names[B_EYES])
    if eyes:
        target_positions = []
        target_updates = []
        for logical_name, source_key in ((B_EYE_TARGET_L, "eye.L"), (B_EYE_TARGET_R, "eye.R")):
            actual_name = bone_names[logical_name]
            target = armature_object.pose.bones.get(actual_name)
            source = armature_object.pose.bones.get(mapping.get(source_key, ""))
            if target and source:
                direction = source.tail - source.head
                if direction.length < 0.0001:
                    direction = Vector((0, -1, 0))
                target_location = source.head + direction.normalized() * unit * 3.0
                target_positions.append(target_location)
                target_updates.append((target, target_location, source.name))
        if target_positions:
            average = sum(target_positions, Vector((0, 0, 0))) / len(target_positions)
            _set_pose_head_location(eyes, average)
            log_line(context, f"  {bone_names[B_EYES]} aligned to the average eye target position.")
            context.view_layer.update()
        for target, target_location, source_name in target_updates:
            _set_pose_head_location(target, target_location)
            log_line(context, f"  {target.name} aligned in front of {source_name}.")

    for logical_name, keys in (
        (B_ELBOW_POLE_L, ("upper_arm.L", "lower_arm.L", "hand.L")),
        (B_ELBOW_POLE_R, ("upper_arm.R", "lower_arm.R", "hand.R")),
        (B_KNEE_POLE_L, ("upper_leg.L", "lower_leg.L", "foot.L")),
        (B_KNEE_POLE_R, ("upper_leg.R", "lower_leg.R", "foot.R")),
    ):
        actual_name = bone_names[logical_name]
        target = armature_object.pose.bones.get(actual_name)
        root_bone = armature_object.pose.bones.get(mapping[keys[0]])
        mid_bone = armature_object.pose.bones.get(mapping[keys[1]])
        tip_bone = armature_object.pose.bones.get(mapping[keys[2]])
        if target and root_bone and mid_bone and tip_bone:
            pole_distance = unit * 3.0 * scale
            bias = Vector((0, 1, 0)) if logical_name in (B_ELBOW_POLE_L, B_ELBOW_POLE_R) else Vector((0, -1, 0))
            pole_position, bend_dir, is_straight = _pole_position(
                root_bone.head, mid_bone.head, tip_bone.head, pole_distance, fallback_bias=bias
            )
            _set_pose_head_location(target, pole_position)
            log_line(context, f"  {actual_name} aligned to current bend plane.")

            if is_straight:
                # The chain is perfectly straight — the IK solver hits a
                # singularity and can't determine the bend direction.  Nudge
                # the IK target slightly toward the pole to prime the solver.
                logical_ik_target = {
                    B_ELBOW_POLE_L: B_HAND_IK_L,
                    B_ELBOW_POLE_R: B_HAND_IK_R,
                    B_KNEE_POLE_L: B_FOOT_IK_L,
                    B_KNEE_POLE_R: B_FOOT_IK_R,
                }.get(logical_name)
                actual_ik_target = bone_names[logical_ik_target]
                ik_target = armature_object.pose.bones.get(actual_ik_target)
                if ik_target:
                    nudge = bend_dir * (pole_distance * 0.002)
                    matrix = ik_target.matrix.copy()
                    matrix.translation += nudge
                    ik_target.matrix = matrix
                    log_line(
                        context,
                        f"  {actual_ik_target} nudged {nudge.length:.4f} toward "
                        f"pole to break straight-chain singularity.",
                    )

                # Also apply a tiny visual bend (0.2 degrees) to the source bones 
                # in pose mode to help the IK solver find its way.
                chain_vec = tip_bone.head - root_bone.head
                if chain_vec.length > 0.0001:
                    chain_dir = chain_vec.normalized()
                    axis = chain_dir.cross(bend_dir).normalized()
                    if axis.length > 0.5:
                        # Rotate AWAY from the pole to bias the hinge (elbow/knee) TOWARDS the pole.
                        local_axis = mid_bone.matrix.to_3x3().inverted() @ axis
                        rot_matrix = Matrix.Rotation(math.radians(-0.2), 4, local_axis)
                        mid_bone.matrix = mid_bone.matrix @ rot_matrix
                        log_line(context, f"  {mid_bone.name} pre-bent 0.2 deg for IK bias.")

    context.view_layer.update()

def _align_finger_controls_to_current_pose(context, armature_object, unit, bone_names):
    chains = detect_finger_chains(armature_object.data.bones, bone_names)
    for actual_name, chain in chains.items():
        target = armature_object.pose.bones.get(actual_name)
        base_bone = armature_object.pose.bones.get(chain[0])
        next_bone = armature_object.pose.bones.get(chain[1]) if len(chain) > 1 else None
        if not target or not base_bone:
            continue

        direction = None
        if next_bone:
            direction = next_bone.head - base_bone.head
        if direction is None or direction.length < 0.0001:
            direction = base_bone.tail - base_bone.head
        if direction.length < 0.0001:
            direction = Vector((0, 0, unit))

        target_location = base_bone.head + direction.normalized() * unit * 0.12
        target_matrix = base_bone.matrix.copy()
        target_matrix.translation = target_location
        target.matrix = target_matrix
        log_line(context, f"  {actual_name} aligned near {base_bone.name} and parented to hand IK.")

    context.view_layer.update()

def _pole_position(root, mid, tip, distance, fallback_bias=None):
    """Return (pole_world_pos, bend_direction, is_straight)."""
    chain = tip - root
    if chain.length < 0.0001:
        bend = fallback_bias if fallback_bias else Vector((0, -1, 0))
        return mid + bend.normalized() * distance, bend.normalized(), True

    chain_dir = chain.normalized()
    projection = root + chain_dir * (mid - root).dot(chain_dir)
    bend = mid - projection
    is_straight = False

    if bend.length < 0.0001:
        is_straight = True
        # Chain is straight — pick a perpendicular direction.
        if fallback_bias:
            # Use bias if provided, as long as it's not parallel to the chain.
            perp = fallback_bias - chain_dir * fallback_bias.dot(chain_dir)
            if perp.length < 0.0001:
                # Bias was parallel, fallback to cross products.
                perp = chain_dir.cross(Vector((0, 0, 1)))
        else:
            perp = chain_dir.cross(Vector((0, 0, 1)))

        if perp.length < 0.0001:
            perp = chain_dir.cross(Vector((0, 1, 0)))
        if perp.length < 0.0001:
            perp = Vector((0, -1, 0))
        bend = perp.normalized()

    return mid + bend.normalized() * distance, bend.normalized(), is_straight

def _eye_controller_positions(bones, mapping, unit, bone_names):
    head_bone = bones[mapping["head"]]
    head_center = (head_bone.head_local + head_bone.tail_local) * 0.5
    center = head_center
    eye_heads = []
    eye_targets = {}

    for side in ("L", "R"):
        key = f"eye.{side}"
        if key not in mapping:
            continue
        eye = bones[mapping[key]]
        direction = eye.tail_local - eye.head_local
        if direction.length < 0.0001:
            direction = Vector((0, -1, 0))
        target = eye.head_local + direction.normalized() * unit * 3.0
        eye_heads.append(eye.head_local.copy())
        logical_name = B_EYE_TARGET_L if side == "L" else B_EYE_TARGET_R
        target_name = bone_names[logical_name]
        eye_targets[target_name] = marker(target, unit * 0.6)

    if eye_heads:
        center = sum(eye_heads, Vector((0, 0, 0))) / len(eye_heads)
    
    forward = average_eye_forward(bones, mapping)
    eyes_ctrl = center + forward * unit * 4.2
    if not eye_heads:
        eyes_ctrl = head_center + forward * unit * 4.2
    
    positions = {bone_names[B_EYES]: marker(eyes_ctrl, unit * 1.2)}
    positions.update(eye_targets)
    return positions

def _finger_controller_positions(bones, mapping, unit, bone_names):
    positions = {}
    chains = detect_finger_chains(bones, bone_names)
    for side in ("L", "R"):
        for control_name, chain in chains.items():
            base_bone = bones.get(chain[0])
            next_bone = bones.get(chain[1]) if len(chain) > 1 else None
            if not base_bone:
                continue
            direction = None
            if next_bone:
                direction = next_bone.head_local - base_bone.head_local
            if direction is None or direction.length < 0.0001:
                direction = base_bone.tail_local - base_bone.head_local
            if direction.length < 0.0001:
                direction = Vector((0, 0, unit))
            
            origin = base_bone.head_local + direction.normalized() * unit * 0.12
            positions[control_name] = marker(origin, unit * 0.35)
    return positions

def _pose_matrices(armature_object, bone_names):
    """Return a dictionary of bone matrices for the given names."""
    matrices = {}
    for bone_name in bone_names:
        pose_bone = armature_object.pose.bones.get(bone_name)
        if pose_bone:
            matrices[bone_name] = pose_bone.matrix.copy()
    return matrices

def _set_pose_head_location(pose_bone, head_location):
    matrix = pose_bone.matrix.copy()
    matrix.translation = head_location
    pose_bone.matrix = matrix

def _set_pose_from_source(target_bone, source_bone, head_location):
    matrix = source_bone.matrix.copy()
    matrix.translation = head_location
    target_bone.matrix = matrix

def _pose_unit(armature_object, mapping, scale):
    hips = armature_object.pose.bones[mapping["hips"]].head
    head_top = armature_object.pose.bones[mapping["head"]].tail
    height = max((head_top - hips).length, 1.0)
    return max(height * 0.08 * scale, 0.05)
