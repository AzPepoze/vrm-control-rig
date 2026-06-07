"""Bone creation and hierarchy logic."""

import bpy
from mathutils import Vector
from ..constants import (
    CONTROL_BONES,
    CONTROL_COLLECTION,
    HELPER_BONES,
    HELPER_COLLECTION,
    B_ROOT,
    B_HIPS,
    B_EYES,
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
    GENERATED_BONES,
)
from ..utils import ObjectMode, tag_generated, is_generated
from .fingers import detect_finger_chains, FINGER_CONTROLS
from .utils import marker, matching_or_vertical

def create_controller_bones(context, armature_object, mapping, scale, bone_names, settings):
    """Create and parent generated bones in EDIT mode."""
    positions = _controller_positions(armature_object, mapping, scale, bone_names)
    created = []

    with ObjectMode(context, armature_object, "EDIT"):
        edit_bones = armature_object.data.edit_bones
        for name, placement in positions.items():
            if edit_bones.get(name):
                edit_bones.remove(edit_bones[name])
            bone = edit_bones.new(name)
            bone.head = placement["head"]
            bone.tail = placement["tail"]
            bone.roll = 0.0
            bone.use_deform = False
            bone.parent = None
            tag_generated(bone)
            created.append(name)

        root = edit_bones.get(bone_names[B_ROOT])
        
        # Determine which bones should be parented to the root.
        root_children = [
            bone_names[B_HIPS],
            bone_names[B_EYES],
            bone_names[B_ELBOW_POLE_L],
            bone_names[B_ELBOW_POLE_R],
            bone_names[B_KNEE_POLE_L],
            bone_names[B_KNEE_POLE_R],
        ]
        
        if settings.parent_limbs_to_root:
            root_children.extend([
                bone_names[B_HAND_IK_L],
                bone_names[B_HAND_IK_R],
                bone_names[B_FOOT_IK_L],
                bone_names[B_FOOT_IK_R],
            ])

        for name in root_children:
            child = edit_bones.get(name)
            if child and root:
                child.parent = root
                child.use_connect = False

        hand_parents = {
            bone_names[B_THUMB_CURL_L]: bone_names[B_HAND_IK_L],
            bone_names[B_INDEX_CURL_L]: bone_names[B_HAND_IK_L],
            bone_names[B_MIDDLE_CURL_L]: bone_names[B_HAND_IK_L],
            bone_names[B_RING_CURL_L]: bone_names[B_HAND_IK_L],
            bone_names[B_LITTLE_CURL_L]: bone_names[B_HAND_IK_L],
            bone_names[B_THUMB_CURL_R]: bone_names[B_HAND_IK_R],
            bone_names[B_INDEX_CURL_R]: bone_names[B_HAND_IK_R],
            bone_names[B_MIDDLE_CURL_R]: bone_names[B_HAND_IK_R],
            bone_names[B_RING_CURL_R]: bone_names[B_HAND_IK_R],
            bone_names[B_LITTLE_CURL_R]: bone_names[B_HAND_IK_R],
        }

        eyes_parent = edit_bones.get(bone_names[B_EYES])
        for name in (bone_names[B_EYE_TARGET_L], bone_names[B_EYE_TARGET_R]):
            child = edit_bones.get(name)
            if child and eyes_parent:
                child.parent = eyes_parent
                child.use_connect = False

        for name in FINGER_CONTROLS:
            actual_name = bone_names[name]
            child = edit_bones.get(actual_name)
            parent_name = hand_parents.get(actual_name)
            parent = edit_bones.get(parent_name) if parent_name else None
            if child and parent:
                child.parent = parent
                child.use_connect = False

    return created

def assign_collections(armature_object, bone_names):
    """Assign generated bones to their respective bone collections."""
    data = armature_object.data
    controls = _ensure_bone_collection(data, CONTROL_COLLECTION)
    helpers = _ensure_bone_collection(data, HELPER_COLLECTION)

    for logical_name in CONTROL_BONES:
        actual_name = bone_names[logical_name]
        bone = data.bones.get(actual_name)
        if bone:
            controls.assign(bone)

    for logical_name in HELPER_BONES:
        actual_name = bone_names[logical_name]
        bone = data.bones.get(actual_name)
        if bone:
            helpers.assign(bone)

def configure_pose_bones(armature_object, shapes, scale, hide_helpers, bone_names):
    """Apply custom shapes, locks, and colors in POSE mode."""
    for pose_bone in armature_object.pose.bones:
        if is_generated(pose_bone):
            pose_bone.lock_scale = (True, True, True)
            _set_custom_shape_scale(pose_bone, scale)

    for logical_name in CONTROL_BONES:
        actual_name = bone_names[logical_name]
        pose_bone = armature_object.pose.bones.get(actual_name)
        if pose_bone:
            if logical_name == B_ROOT:
                pose_bone.custom_shape = shapes["root"]
                pose_bone.lock_location = (False, False, False)
                _set_custom_shape_scale(pose_bone, scale)
                _set_custom_shape_rotation(pose_bone, 90.0, 0.0, 0.0)
            elif logical_name == B_HIPS:
                pose_bone.custom_shape = shapes["box"]
                _set_custom_shape_scale(pose_bone, scale * 4.0)
            elif logical_name == B_EYES:
                pose_bone.custom_shape = shapes["eye"]
                _set_custom_shape_scale(pose_bone, scale * 1.8)
            elif logical_name == B_HAND_IK_L:
                pose_bone.custom_shape = shapes["hand"]
                _set_custom_shape_scale(pose_bone, scale * 1.8)
                _set_custom_shape_rotation(pose_bone, -90.0, 0.0, 90.0)
            elif logical_name == B_HAND_IK_R:
                pose_bone.custom_shape = shapes["hand"]
                _set_custom_shape_scale(pose_bone, scale * 1.8)
                _set_custom_shape_rotation(pose_bone, 90.0, 0.0, 90.0)
            elif logical_name in (B_FOOT_IK_L, B_FOOT_IK_R):
                pose_bone.custom_shape = shapes["foot"]
                _set_custom_shape_scale(pose_bone, scale * 2.0)
                _set_custom_shape_translation(pose_bone, 0.0, 0.018 * scale, 0.072 * scale)
                _set_custom_shape_rotation(pose_bone, 0.0, 0.0, 90.0)
            elif logical_name in FINGER_CONTROLS:
                pose_bone.custom_shape = shapes["finger"]
                pose_bone.lock_rotation = (True, True, True)
                pose_bone.lock_scale = (True, True, False)
                _set_custom_shape_scale(pose_bone, scale * 0.55)
                _set_custom_shape_rotation(pose_bone, 0.0, 0.0, 90.0)
            else:
                pose_bone.custom_shape = shapes["hand"]
            _set_color(pose_bone, "THEME09")

    for logical_name in HELPER_BONES:
        actual_name = bone_names[logical_name]
        pose_bone = armature_object.pose.bones.get(actual_name)
        if pose_bone:
            is_eye = logical_name in (B_EYE_TARGET_L, B_EYE_TARGET_R)
            pose_bone.custom_shape = shapes["eye"] if is_eye else shapes["pole"]
            if is_eye:
                _set_custom_shape_scale(pose_bone, scale * 1.25)
            _set_color(pose_bone, "THEME11" if is_eye else "THEME04")
            pose_bone.bone.hide = hide_helpers and not is_eye

def _controller_positions(armature_object, mapping, scale, bone_names):
    data = armature_object.data
    bones = data.bones

    def head(name):
        return bones[mapping[name]].head_local.copy()

    def tail(name):
        return bones[mapping[name]].tail_local.copy()

    hips = head("hips")
    head_top = tail("head")
    height = max((head_top - hips).length, 1.0)
    unit = max(height * 0.08 * scale, 0.05)

    left_hand = head("hand.L")
    right_hand = head("hand.R")
    left_foot = head("foot.L")
    right_foot = head("foot.R")

    root_placement = _root_controller_placement(bones, mapping, unit)
    positions = {
        bone_names[B_ROOT]: root_placement,
        bone_names[B_HIPS]: matching_or_vertical(hips, tail("hips"), unit),
        bone_names[B_HAND_IK_L]: matching_or_vertical(left_hand, tail("hand.L"), unit),
        bone_names[B_HAND_IK_R]: matching_or_vertical(right_hand, tail("hand.R"), unit),
        bone_names[B_FOOT_IK_L]: marker(left_foot, unit),
        bone_names[B_FOOT_IK_R]: marker(right_foot, unit),
        bone_names[B_ELBOW_POLE_L]: _pole_placement(
            head("upper_arm.L"), head("lower_arm.L"), head("hand.L"), unit, scale, fallback_bias=Vector((0, 1, 0))
        ),
        bone_names[B_ELBOW_POLE_R]: _pole_placement(
            head("upper_arm.R"), head("lower_arm.R"), head("hand.R"), unit, scale, fallback_bias=Vector((0, 1, 0))
        ),
        bone_names[B_KNEE_POLE_L]: _pole_placement(
            head("upper_leg.L"), head("lower_leg.L"), head("foot.L"), unit, scale, fallback_bias=Vector((0, -1, 0))
        ),
        bone_names[B_KNEE_POLE_R]: _pole_placement(
            head("upper_leg.R"), head("lower_leg.R"), head("foot.R"), unit, scale, fallback_bias=Vector((0, -1, 0))
        ),
    }

    from .alignment import _eye_controller_positions, _finger_controller_positions
    eye_positions = _eye_controller_positions(bones, mapping, unit, bone_names)
    positions.update(eye_positions)
    positions.update(_finger_controller_positions(bones, mapping, unit, bone_names))
    return positions

def _root_controller_placement(bones, mapping, unit):
    from .source import _source_root_bone
    source_root = _source_root_bone(bones, mapping)
    if source_root:
        return matching_or_vertical(source_root.head_local.copy(), source_root.tail_local.copy(), unit * 1.8)

    left_foot = bones.get(mapping.get("foot.L", ""))
    right_foot = bones.get(mapping.get("foot.R", ""))
    if left_foot and right_foot:
        origin = (left_foot.head_local + right_foot.head_local) * 0.5
        origin.z = min(left_foot.head_local.z, right_foot.head_local.z)
        return marker(origin, unit * 1.8)

    return matching_or_vertical(bones[mapping["hips"]].head_local.copy(), bones[mapping["hips"]].tail_local.copy(), unit * 1.8)

def _pole_placement(root, mid, tip, unit, scale, fallback_bias=None):
    from .alignment import _pole_position
    pole, _bend_dir, _is_straight = _pole_position(root, mid, tip, unit * 3.0 * scale, fallback_bias)
    return marker(pole, unit * 0.75)

def _ensure_bone_collection(armature_data, name):
    collection = armature_data.collections.get(name)
    if collection is None:
        collection = armature_data.collections.new(name)
    return collection

def _set_custom_shape_scale(pose_bone, scale):
    if hasattr(pose_bone, "custom_shape_scale_xyz"):
        pose_bone.custom_shape_scale_xyz = (scale, scale, scale)
    elif hasattr(pose_bone, "custom_shape_scale"):
        pose_bone.custom_shape_scale = scale

def _set_custom_shape_translation(pose_bone, x, y, z):
    if not hasattr(pose_bone, "custom_shape_translation"):
        return
    try:
        pose_bone.custom_shape_translation = (x, y, z)
    except (AttributeError, TypeError, ValueError):
        pass

def _set_custom_shape_rotation(pose_bone, x_degrees, y_degrees, z_degrees):
    import math
    if not hasattr(pose_bone, "custom_shape_rotation_euler"):
        return
    try:
        pose_bone.custom_shape_rotation_euler = (
            math.radians(x_degrees),
            math.radians(y_degrees),
            math.radians(z_degrees),
        )
    except (AttributeError, TypeError, ValueError):
        pass

def _set_color(pose_bone, palette):
    try:
        pose_bone.color.palette = palette
    except Exception:
        pass
