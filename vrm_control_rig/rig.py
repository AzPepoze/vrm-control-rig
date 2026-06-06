"""Rig generation and deletion."""

import math

import bpy
from mathutils import Vector

from .constants import (
    ADDON_ID,
    CONTROL_BONES,
    CONTROL_COLLECTION,
    GENERATED_BONES,
    HELPER_BONES,
    HELPER_COLLECTION,
    IK_CONSTRAINT_NAME,
    ROOT_CONSTRAINT_NAME,
)
from .detection import detect_humanoid_bones, format_missing_bones
from .logs import clear_log, log_delta, log_line, log_mapping, log_snapshot, snapshot_pose
from .shapes import ensure_shapes
from .utils import ObjectMode, remove_generated_constraints, remove_generated_fcurves, tag_generated


class RigBuildError(Exception):
    """Raised when the selected armature cannot support the generated rig."""


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

    shapes = ensure_shapes(context)
    scale = context.scene.vrm_control_rig.controller_scale

    generated = _create_controller_bones(context, armature_object, mapping, scale)
    log_line(context, "Created generated bones: " + ", ".join(generated))
    _assign_collections(armature_object)
    _configure_pose_bones(armature_object, shapes, scale, context.scene.vrm_control_rig.auto_hide_helpers)
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
        for name in ("Hand_IK.L", "Hand_IK.R", "Foot_IK.L", "Foot_IK.R"):
            child = edit_bones.get(name)
            if child and root:
                child.parent = root
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

    root_placement = _matching_or_vertical(head("hips"), tail("hips"), unit * 1.8)

    return {
        "Root_CTRL": root_placement,
        "Hand_IK.L": _marker(left_hand, unit),
        "Hand_IK.R": _marker(right_hand, unit),
        "Foot_IK.L": _marker(left_foot, unit),
        "Foot_IK.R": _marker(right_foot, unit),
        "Elbow_Pole.L": _pole_placement(head("upper_arm.L"), head("lower_arm.L"), head("hand.L"), unit, scale),
        "Elbow_Pole.R": _pole_placement(head("upper_arm.R"), head("lower_arm.R"), head("hand.R"), unit, scale),
        "Knee_Pole.L": _pole_placement(head("upper_leg.L"), head("lower_leg.L"), head("foot.L"), unit, scale),
        "Knee_Pole.R": _pole_placement(head("upper_leg.R"), head("lower_leg.R"), head("foot.R"), unit, scale),
    }


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


def _configure_pose_bones(armature_object, shapes, scale, hide_helpers):
    for pose_bone in armature_object.pose.bones:
        if pose_bone.name in GENERATED_BONES:
            tag_generated(pose_bone)
            pose_bone.lock_scale = (True, True, True)
            _set_custom_shape_scale(pose_bone, scale)

    for name in CONTROL_BONES:
        pose_bone = armature_object.pose.bones.get(name)
        if pose_bone:
            pose_bone.custom_shape = shapes["root"] if name == "Root_CTRL" else shapes["ik"]
            _set_color(pose_bone, "THEME09")

    for name in HELPER_BONES:
        pose_bone = armature_object.pose.bones.get(name)
        if pose_bone:
            pose_bone.custom_shape = shapes["pole"]
            _set_color(pose_bone, "THEME04")
            pose_bone.bone.hide = hide_helpers


def _align_controls_to_current_pose(context, armature_object, mapping, scale):
    """Initialize generated controls from the current pose before constraints run."""

    log_line(context, "Aligning generated controls to current source pose before adding constraints.")
    context.view_layer.update()

    root = armature_object.pose.bones.get("Root_CTRL")
    hips = armature_object.pose.bones.get(mapping["hips"])
    if root and hips:
        root.matrix = hips.matrix.copy()
        log_line(context, f"  Root_CTRL aligned to {hips.name} pose matrix.")

    for target_name, source_key in (
        ("Hand_IK.L", "hand.L"),
        ("Hand_IK.R", "hand.R"),
        ("Foot_IK.L", "foot.L"),
        ("Foot_IK.R", "foot.R"),
    ):
        target = armature_object.pose.bones.get(target_name)
        source = armature_object.pose.bones.get(mapping[source_key])
        if target and source:
            _set_pose_head_location(target, source.head)
            log_line(context, f"  {target_name} head aligned to {source.name} pose head.")

    unit = _pose_unit(armature_object, mapping, scale)
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


def _set_pose_head_location(pose_bone, head_location):
    matrix = pose_bone.matrix.copy()
    matrix.translation = head_location
    pose_bone.matrix = matrix


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
