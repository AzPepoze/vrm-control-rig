"""Rig generation and deletion."""

import math
import re

import bpy
from mathutils import Vector

from .constants import (
    ADDON_ID,
    CONTROL_BONES,
    CONTROL_COLLECTION,
    GENERATED_BONES,
    HELPER_BONES,
    HELPER_COLLECTION,
    EYE_CONSTRAINT_NAME,
    FINGER_CURL_DRIVER_TAG,
    IK_CONSTRAINT_NAME,
    ROTATION_CONSTRAINT_NAME,
    ROOT_CONSTRAINT_NAME,
)
from .detection import detect_humanoid_bones, format_missing_bones
from .logs import clear_log, log_delta, log_line, log_mapping, log_snapshot, snapshot_pose
from .shapes import ensure_shapes
from .utils import ObjectMode, remove_generated_constraints, remove_generated_fcurves, tag_generated


class RigBuildError(Exception):
    """Raised when the selected armature cannot support the generated rig."""


FINGER_CONTROLS = (
    "Thumb_Curl.L",
    "Index_Curl.L",
    "Middle_Curl.L",
    "Ring_Curl.L",
    "Little_Curl.L",
    "Thumb_Curl.R",
    "Index_Curl.R",
    "Middle_Curl.R",
    "Ring_Curl.R",
    "Little_Curl.R",
)

FINGER_SPECS = (
    ("Thumb", "thumb"),
    ("Index", "index"),
    ("Middle", "middle"),
    ("Ring", "ring"),
    ("Little", "little"),
)

HIDDEN_EXTRA_BONE_TAG = ADDON_ID + "_hidden_extra_bone"


def generate_control_rig(context, armature_object, *, regenerate=False):
    mapping, missing = detect_humanoid_bones(armature_object)
    if context.scene.vrm_control_rig.enable_diagnostics and context.scene.vrm_control_rig.clear_log_on_generate:
        clear_log()
    log_line(context, f"Generate requested for armature: {armature_object.name}")
    log_mapping(context, mapping, missing)
    if missing:
        raise RigBuildError("Missing required VRM humanoid bones: " + format_missing_bones(missing))

    tracked_source_bones = _tracked_source_bones(mapping)
    before = snapshot_pose(armature_object, tracked_source_bones)
    before_matrices = _pose_matrices(armature_object, tracked_source_bones)
    log_snapshot(context, "Before generation source bone transforms:", before)

    if has_control_rig(armature_object):
        if not regenerate:
            raise RigBuildError("A VRM Control Rig already exists. Use Regenerate Control Rig to rebuild it.")
        log_line(context, "Existing generated rig found; deleting before regenerate.")
        delete_control_rig(context, armature_object)

    settings = context.scene.vrm_control_rig
    shapes = ensure_shapes(context)
    scale = settings.controller_scale

    generated = _create_controller_bones(context, armature_object, mapping, scale)
    log_line(context, "Created generated bones: " + ", ".join(generated))
    _assign_collections(armature_object)
    _configure_source_bones(context, armature_object, mapping, settings)
    _configure_pose_bones(armature_object, shapes, scale, settings.auto_hide_helpers)
    _align_controls_to_current_pose(context, armature_object, mapping, scale)
    _create_constraints(context, armature_object, mapping, before_matrices)
    context.view_layer.update()

    after_source = snapshot_pose(armature_object, tracked_source_bones)
    after_controls = snapshot_pose(armature_object, GENERATED_BONES)
    log_snapshot(context, "After generation source bone transforms:", after_source)
    log_snapshot(context, "After generation generated control transforms:", after_controls)
    log_delta(context, "Source bone transform delta after generation:", before, after_source)

    armature_object[ADDON_ID] = True
    return generated


def delete_control_rig(context, armature_object):
    log_line(context, f"Delete requested for armature: {armature_object.name}")
    remove_generated_constraints(armature_object)
    remove_generated_fcurves(armature_object)
    _restore_extra_source_bones(armature_object)

    with ObjectMode(context, armature_object, "EDIT"):
        edit_bones = armature_object.data.edit_bones
        for name in GENERATED_BONES:
            bone = edit_bones.get(name)
            if bone:
                edit_bones.remove(bone)

    return True


def has_control_rig(armature_object):
    return any(name in armature_object.data.bones for name in GENERATED_BONES)


def _create_controller_bones(context, armature_object, mapping, scale):
    positions = _controller_positions(armature_object, mapping, scale)
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

        root = edit_bones.get("Root_CTRL")
        hand_parents = {
            "Thumb_Curl.L": "Hand_IK.L",
            "Index_Curl.L": "Hand_IK.L",
            "Middle_Curl.L": "Hand_IK.L",
            "Ring_Curl.L": "Hand_IK.L",
            "Little_Curl.L": "Hand_IK.L",
            "Thumb_Curl.R": "Hand_IK.R",
            "Index_Curl.R": "Hand_IK.R",
            "Middle_Curl.R": "Hand_IK.R",
            "Ring_Curl.R": "Hand_IK.R",
            "Little_Curl.R": "Hand_IK.R",
        }
        for name in (
            "Eyes_CTRL",
            "Eye_Target.L",
            "Eye_Target.R",
            "Hand_IK.L",
            "Hand_IK.R",
            "Foot_IK.L",
            "Foot_IK.R",
            "Elbow_Pole.L",
            "Elbow_Pole.R",
            "Knee_Pole.L",
            "Knee_Pole.R",
        ):
            child = edit_bones.get(name)
            if child and root:
                child.parent = root
                child.use_connect = False

        for name in FINGER_CONTROLS:
            child = edit_bones.get(name)
            parent_name = hand_parents.get(name)
            parent = edit_bones.get(parent_name) if parent_name else None
            if child and parent:
                child.parent = parent
                child.use_connect = False

    return created


def _controller_positions(armature_object, mapping, scale):
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
        "Root_CTRL": root_placement,
        "Hand_IK.L": _matching_or_vertical(left_hand, tail("hand.L"), unit),
        "Hand_IK.R": _matching_or_vertical(right_hand, tail("hand.R"), unit),
        "Foot_IK.L": _marker(left_foot, unit),
        "Foot_IK.R": _marker(right_foot, unit),
        "Elbow_Pole.L": _pole_placement(head("upper_arm.L"), head("lower_arm.L"), head("hand.L"), unit, scale),
        "Elbow_Pole.R": _pole_placement(head("upper_arm.R"), head("lower_arm.R"), head("hand.R"), unit, scale),
        "Knee_Pole.L": _pole_placement(head("upper_leg.L"), head("lower_leg.L"), head("foot.L"), unit, scale),
        "Knee_Pole.R": _pole_placement(head("upper_leg.R"), head("lower_leg.R"), head("foot.R"), unit, scale),
    }

    eye_positions = _eye_controller_positions(bones, mapping, unit)
    positions.update(eye_positions)
    positions.update(_finger_controller_positions(bones, mapping, unit))
    return positions


def _root_controller_placement(bones, mapping, unit):
    source_root = _source_root_bone(bones, mapping)
    if source_root:
        return _matching_or_vertical(source_root.head_local.copy(), source_root.tail_local.copy(), unit * 1.8)

    left_foot = bones.get(mapping.get("foot.L", ""))
    right_foot = bones.get(mapping.get("foot.R", ""))
    if left_foot and right_foot:
        origin = (left_foot.head_local + right_foot.head_local) * 0.5
        origin.z = min(left_foot.head_local.z, right_foot.head_local.z)
        return _marker(origin, unit * 1.8)

    return _matching_or_vertical(bones[mapping["hips"]].head_local.copy(), bones[mapping["hips"]].tail_local.copy(), unit * 1.8)


def _source_root_bone(bones, mapping):
    hips = bones.get(mapping.get("hips", ""))
    if hips and hips.parent:
        return hips.parent

    for bone in bones:
        if bone.name in GENERATED_BONES:
            continue
        if _norm_name(bone.name) in {"root", "armatureroot"}:
            return bone

    return None


def _vertical(center, length):
    half = length * 0.5
    return {"head": center - Vector((0, 0, half)), "tail": center + Vector((0, 0, half))}


def _marker(origin, length):
    return {"head": origin, "tail": origin + Vector((0, 0, length))}


def _matching_or_vertical(head, tail, fallback_length):
    if (tail - head).length > 0.0001:
        return {"head": head, "tail": tail}
    return _vertical(head, fallback_length)


def _pole_placement(root, mid, tip, unit, scale):
    pole = _pole_position(root, mid, tip, unit * 3.0 * scale)
    return _marker(pole, unit * 0.75)


def _pole_position(root, mid, tip, distance):
    chain = tip - root
    if chain.length < 0.0001:
        return mid + Vector((0, -distance, 0))

    projection = root + chain.normalized() * (mid - root).dot(chain.normalized())
    bend = mid - projection
    if bend.length < 0.0001:
        bend = Vector((0, -1, 0))
    return mid + bend.normalized() * distance


def _eye_controller_positions(bones, mapping, unit):
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
        eye_targets[f"Eye_Target.{side}"] = _marker(target, unit * 0.6)

    if eye_heads:
        center = sum(eye_heads, Vector((0, 0, 0))) / len(eye_heads)
    forward = _average_eye_forward(bones, mapping)
    eyes_ctrl = center + forward * unit * 4.2
    if not eye_heads:
        eyes_ctrl = head_center + forward * unit * 4.2
    positions = {"Eyes_CTRL": _marker(eyes_ctrl, unit * 1.2)}
    positions.update(eye_targets)
    return positions


def _finger_controller_positions(bones, mapping, unit):
    positions = {}
    chains = _detect_finger_chains(bones)
    for side in ("L", "R"):
        for control_name, chain in chains.items():
            if not control_name.endswith(f".{side}"):
                continue
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
            positions[control_name] = _marker(origin, unit * 0.35)
    return positions


def _detect_finger_chains(bones):
    by_norm = {_norm_name(bone.name): bone.name for bone in bones}
    chains = {}

    for side in ("L", "R"):
        side_word = "left" if side == "L" else "right"
        side_short = "l" if side == "L" else "r"
        for display_name, finger_name in FINGER_SPECS:
            chain = []
            for index, segment_name in enumerate(("proximal", "intermediate", "distal"), start=1):
                aliases = (
                    f"{side_word}{finger_name}{segment_name}",
                    f"{side_word}{finger_name}{index}",
                    f"{side_short}{finger_name}{segment_name}",
                    f"{side_short}{finger_name}{index}",
                    f"j_bip_{side_short}_{finger_name}{index}",
                    f"j_bip_{side_short}_{finger_name}_{index}",
                    f"j_bip_{side_short}_{finger_name}{segment_name}",
                    f"{finger_name}{index}.{side_short}",
                    f"{finger_name}{segment_name}.{side_short}",
                )
                found = _find_normalized_bone(by_norm, aliases)
                if found:
                    chain.append(found)
            if chain:
                chains[f"{display_name}_Curl.{side}"] = chain

    return chains


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


def _average_eye_forward(bones, mapping):
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


def _assign_collections(armature_object):
    data = armature_object.data
    controls = _ensure_bone_collection(data, CONTROL_COLLECTION)
    helpers = _ensure_bone_collection(data, HELPER_COLLECTION)

    for name in CONTROL_BONES:
        bone = data.bones.get(name)
        if bone:
            controls.assign(bone)

    for name in HELPER_BONES:
        bone = data.bones.get(name)
        if bone:
            helpers.assign(bone)


def _ensure_bone_collection(armature_data, name):
    collection = armature_data.collections.get(name)
    if collection is None:
        collection = armature_data.collections.new(name)
    return collection


def _configure_source_bones(context, armature_object, mapping, settings):
    if getattr(settings, "source_bones_wireframe", False):
        try:
            armature_object.data.display_type = "WIRE"
            armature_object.show_in_front = True
        except (AttributeError, TypeError, ValueError):
            pass

    _restore_extra_source_bones(armature_object)
    if getattr(settings, "remove_extra_source_bones", False):
        _remove_extra_source_bones(context, armature_object, mapping)


def _remove_extra_source_bones(context, armature_object, mapping):
    controlled_source_bones = set(mapping.values())
    for chain in _detect_finger_chains(armature_object.data.bones).values():
        controlled_source_bones.update(chain)

    remove_names = [
        bone.name
        for bone in armature_object.data.bones
        if bone.name not in GENERATED_BONES and bone.name not in controlled_source_bones
    ]
    if not remove_names:
        return

    with ObjectMode(context, armature_object, "EDIT"):
        edit_bones = armature_object.data.edit_bones
        for name in remove_names:
            bone = edit_bones.get(name)
            if bone:
                edit_bones.remove(bone)


def _restore_extra_source_bones(armature_object):
    for bone in armature_object.data.bones:
        if _is_generated_extra_hidden(bone):
            bone.hide = False
            _clear_hidden_extra_tag(bone)


def tag_generated_extra_hidden(bone):
    try:
        bone[HIDDEN_EXTRA_BONE_TAG] = True
    except TypeError:
        pass


def _is_generated_extra_hidden(bone):
    try:
        return bool(bone.get(HIDDEN_EXTRA_BONE_TAG, False))
    except TypeError:
        return False


def _clear_hidden_extra_tag(bone):
    try:
        if HIDDEN_EXTRA_BONE_TAG in bone:
            del bone[HIDDEN_EXTRA_BONE_TAG]
    except TypeError:
        pass


def _configure_pose_bones(armature_object, shapes, scale, hide_helpers):
    for pose_bone in armature_object.pose.bones:
        if pose_bone.name in GENERATED_BONES:
            tag_generated(pose_bone)
            pose_bone.lock_scale = (True, True, True)
            _set_custom_shape_scale(pose_bone, scale)

    for name in CONTROL_BONES:
        pose_bone = armature_object.pose.bones.get(name)
        if pose_bone:
            if name == "Root_CTRL":
                pose_bone.custom_shape = shapes["root"]
                pose_bone.lock_location = (False, True, False)
                _set_custom_shape_scale(pose_bone, scale * 2.2)
                _set_custom_shape_rotation(pose_bone, 90.0, 0.0, 0.0)
            elif name == "Eyes_CTRL":
                pose_bone.custom_shape = shapes["eye"]
                _set_custom_shape_scale(pose_bone, scale * 1.8)
            elif name == "Hand_IK.L":
                pose_bone.custom_shape = shapes["hand"]
                _set_custom_shape_scale(pose_bone, scale * 0.9)
                _set_custom_shape_rotation(pose_bone, -90.0, 0.0, 90.0)
            elif name == "Hand_IK.R":
                pose_bone.custom_shape = shapes["hand"]
                _set_custom_shape_scale(pose_bone, scale * 0.9)
                _set_custom_shape_rotation(pose_bone, 90.0, 0.0, 90.0)
            elif name.startswith("Foot_IK"):
                pose_bone.custom_shape = shapes["foot"]
                _set_custom_shape_scale(pose_bone, scale * 2.0)
                _set_custom_shape_translation(pose_bone, 0.0, 0.018 * scale, 0.072 * scale)
                _set_custom_shape_rotation(pose_bone, 0.0, 0.0, 90.0)
            elif name in FINGER_CONTROLS:
                pose_bone.custom_shape = shapes["finger"]
                pose_bone.lock_rotation = (True, True, True)
                pose_bone.lock_scale = (True, True, False)
                _set_custom_shape_scale(pose_bone, scale * 0.55)
                _set_custom_shape_rotation(pose_bone, 0.0, 0.0, 90.0)
            else:
                pose_bone.custom_shape = shapes["hand"]
            _set_color(pose_bone, "THEME09")

    for name in HELPER_BONES:
        pose_bone = armature_object.pose.bones.get(name)
        if pose_bone:
            pose_bone.custom_shape = shapes["eye"] if name.startswith("Eye_Target") else shapes["pole"]
            if name.startswith("Eye_Target"):
                _set_custom_shape_scale(pose_bone, scale * 1.25)
            _set_color(pose_bone, "THEME11" if name.startswith("Eye_Target") else "THEME04")
            pose_bone.bone.hide = hide_helpers and not name.startswith("Eye_Target")


def _align_controls_to_current_pose(context, armature_object, mapping, scale):
    """Initialize generated controls from the current pose before constraints run."""

    log_line(context, "Aligning generated controls to current source pose before adding constraints.")
    context.view_layer.update()

    root = armature_object.pose.bones.get("Root_CTRL")
    source_root = _source_root_bone(armature_object.data.bones, mapping)
    source_root_pose = armature_object.pose.bones.get(source_root.name) if source_root else None
    if root and source_root_pose:
        root.matrix = source_root_pose.matrix.copy()
        log_line(context, f"  Root_CTRL aligned to {source_root_pose.name} pose matrix.")
    elif root:
        log_line(context, "  Root_CTRL kept at generated floor/root placement.")

    for target_name, source_key in (
        ("Hand_IK.L", "hand.L"),
        ("Hand_IK.R", "hand.R"),
        ("Foot_IK.L", "foot.L"),
        ("Foot_IK.R", "foot.R"),
    ):
        target = armature_object.pose.bones.get(target_name)
        source = armature_object.pose.bones.get(mapping[source_key])
        if target and source:
            _set_pose_from_source(target, source, source.head)
            log_line(context, f"  {target_name} aligned to {source.name} pose head and rotation.")

    context.view_layer.update()
    unit = _pose_unit(armature_object, mapping, scale)
    _align_finger_controls_to_current_pose(context, armature_object, unit)

    eyes = armature_object.pose.bones.get("Eyes_CTRL")
    if eyes:
        target_positions = []
        for target_name, source_key in (("Eye_Target.L", "eye.L"), ("Eye_Target.R", "eye.R")):
            target = armature_object.pose.bones.get(target_name)
            source = armature_object.pose.bones.get(mapping.get(source_key, ""))
            if target and source:
                direction = source.tail - source.head
                if direction.length < 0.0001:
                    direction = Vector((0, -1, 0))
                target_location = source.head + direction.normalized() * unit * 3.0
                _set_pose_head_location(target, target_location)
                target_positions.append(target_location)
                log_line(context, f"  {target_name} aligned in front of {source.name}.")
        if target_positions:
            average = sum(target_positions, Vector((0, 0, 0))) / len(target_positions)
            _set_pose_head_location(eyes, average)
            log_line(context, "  Eyes_CTRL aligned to the average eye target position.")

    for target_name, keys in (
        ("Elbow_Pole.L", ("upper_arm.L", "lower_arm.L", "hand.L")),
        ("Elbow_Pole.R", ("upper_arm.R", "lower_arm.R", "hand.R")),
        ("Knee_Pole.L", ("upper_leg.L", "lower_leg.L", "foot.L")),
        ("Knee_Pole.R", ("upper_leg.R", "lower_leg.R", "foot.R")),
    ):
        target = armature_object.pose.bones.get(target_name)
        root = armature_object.pose.bones.get(mapping[keys[0]])
        mid = armature_object.pose.bones.get(mapping[keys[1]])
        tip = armature_object.pose.bones.get(mapping[keys[2]])
        if target and root and mid and tip:
            pole_position = _pole_position(root.head, mid.head, tip.head, unit * 3.0 * scale)
            _set_pose_head_location(target, pole_position)
            log_line(context, f"  {target_name} aligned to current bend plane.")

    context.view_layer.update()


def _align_finger_controls_to_current_pose(context, armature_object, unit):
    chains = _detect_finger_chains(armature_object.data.bones)
    for control_name, chain in chains.items():
        target = armature_object.pose.bones.get(control_name)
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
        _set_pose_head_location(target, target_location)
        log_line(context, f"  {control_name} aligned near {base_bone.name} and parented to hand IK.")


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


def _create_constraints(context, armature_object, mapping, before_matrices):
    _add_root_constraint(armature_object, mapping["hips"], "Root_CTRL")
    context.view_layer.update()
    _add_ik_constraint(
        context,
        armature_object,
        mapping["lower_arm.L"],
        "Hand_IK.L",
        "Elbow_Pole.L",
        (mapping["upper_arm.L"], mapping["lower_arm.L"], mapping["hand.L"]),
        before_matrices,
    )
    _add_ik_constraint(
        context,
        armature_object,
        mapping["lower_arm.R"],
        "Hand_IK.R",
        "Elbow_Pole.R",
        (mapping["upper_arm.R"], mapping["lower_arm.R"], mapping["hand.R"]),
        before_matrices,
    )
    _add_rotation_constraint(armature_object, mapping["hand.L"], "Hand_IK.L")
    _add_rotation_constraint(armature_object, mapping["hand.R"], "Hand_IK.R")
    _add_rotation_constraint(armature_object, mapping["foot.L"], "Foot_IK.L")
    _add_rotation_constraint(armature_object, mapping["foot.R"], "Foot_IK.R")
    _add_eye_constraints(context, armature_object, mapping)
    _add_finger_drivers(context, armature_object)
    _add_ik_constraint(
        context,
        armature_object,
        mapping["lower_leg.L"],
        "Foot_IK.L",
        "Knee_Pole.L",
        (mapping["upper_leg.L"], mapping["lower_leg.L"], mapping["foot.L"]),
        before_matrices,
    )
    _add_ik_constraint(
        context,
        armature_object,
        mapping["lower_leg.R"],
        "Foot_IK.R",
        "Knee_Pole.R",
        (mapping["upper_leg.R"], mapping["lower_leg.R"], mapping["foot.R"]),
        before_matrices,
    )


def _tracked_source_bones(mapping):
    keys = (
        "hips",
        "spine",
        "chest",
        "upper_chest",
        "neck",
        "head",
        "eye.L",
        "eye.R",
        "upper_arm.L",
        "lower_arm.L",
        "hand.L",
        "upper_arm.R",
        "lower_arm.R",
        "hand.R",
        "upper_leg.L",
        "lower_leg.L",
        "foot.L",
        "upper_leg.R",
        "lower_leg.R",
        "foot.R",
    )
    return [mapping[key] for key in keys if key in mapping]


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
    constraint = pose_bone.constraints.new(type="IK")
    constraint.name = IK_CONSTRAINT_NAME
    constraint.target = armature_object
    constraint.subtarget = target_bone
    constraint.pole_target = armature_object
    constraint.pole_subtarget = pole_bone
    constraint.chain_count = 2
    constraint.use_rotation = False
    tag_generated(constraint)
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


def _add_eye_constraints(context, armature_object, mapping):
    added = 0
    for side in ("L", "R"):
        source_key = f"eye.{side}"
        target_bone = f"Eye_Target.{side}"
        if source_key not in mapping or target_bone not in armature_object.pose.bones:
            continue
        pose_bone = armature_object.pose.bones.get(mapping[source_key])
        if not pose_bone:
            continue
        constraint = pose_bone.constraints.new(type="DAMPED_TRACK")
        constraint.name = EYE_CONSTRAINT_NAME
        constraint.target = armature_object
        constraint.subtarget = target_bone
        _set_eye_track_axis(constraint, pose_bone)
        tag_generated(constraint)
        added += 1

    if added:
        log_line(context, f"Added {added} eye tracking constraints.")
    else:
        log_line(context, "No eye bones detected; skipped eye tracking constraints.")


def _add_finger_drivers(context, armature_object):
    added = 0
    chains = _detect_finger_chains(armature_object.data.bones)
    for control_name, chain in chains.items():
        if control_name not in armature_object.pose.bones:
            continue
        for bone_name in chain:
            pose_bone = armature_object.pose.bones.get(bone_name)
            if not pose_bone:
                continue
            if _add_finger_curl_driver(armature_object, pose_bone, control_name):
                added += 1

    if added:
        log_line(context, f"Added {added} finger curl scale drivers.")
    else:
        log_line(context, "No finger chains detected; skipped finger curl drivers.")


def _add_finger_curl_driver(armature_object, pose_bone, control_name):
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


def _pose_matrices(armature_object, bone_names):
    matrices = {}
    for bone_name in bone_names:
        pose_bone = armature_object.pose.bones.get(bone_name)
        if pose_bone:
            matrices[bone_name] = pose_bone.matrix.copy()
    return matrices
