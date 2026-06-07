"""Main orchestration for rig generation and deletion."""

import bpy
from ..constants import ADDON_ID, GENERATED_BONES
from ..detection import detect_humanoid_bones, format_missing_bones
from ..logs import clear_log, log_delta, log_line, log_mapping, log_snapshot, snapshot_pose
from ..shapes import ensure_shapes
from ..utils import (
    ObjectMode,
    get_generated_bone_names,
    remove_generated_constraints,
    remove_generated_fcurves,
)

from .naming import get_bone_names
from .bones import create_controller_bones, assign_collections, configure_pose_bones
from .alignment import align_controls_to_current_pose
from .constraints import create_constraints
from .source import (
    configure_source_bones,
    restore_extra_source_bones,
    restore_extra_objects,
    tracked_source_bones,
)

class RigBuildError(Exception):
    """Raised when the selected armature cannot support the generated rig."""

def generate_control_rig(context, armature_object, *, regenerate=False):
    """Orchestrate the creation of a VRM Control Rig."""
    mapping, missing = detect_humanoid_bones(armature_object)
    if context.scene.vrm_control_rig.enable_diagnostics and context.scene.vrm_control_rig.clear_log_on_generate:
        clear_log()
    log_line(context, f"Generate requested for armature: {armature_object.name}")
    log_mapping(context, mapping, missing)
    if missing:
        raise RigBuildError("Missing required VRM humanoid bones: " + format_missing_bones(missing))

    from .alignment import _pose_matrices
    tracked_bones = tracked_source_bones(mapping)
    before = snapshot_pose(armature_object, tracked_bones)
    before_matrices = _pose_matrices(armature_object, tracked_bones)
    log_snapshot(context, "Before generation source bone transforms:", before)

    if has_control_rig(armature_object):
        if not regenerate:
            raise RigBuildError("A VRM Control Rig already exists. Use Regenerate Control Rig to rebuild it.")
        log_line(context, "Existing generated rig found; deleting before regenerate.")
        delete_control_rig(context, armature_object)

    settings = context.scene.vrm_control_rig
    shapes = ensure_shapes(context)
    scale = settings.controller_scale
    bone_names = get_bone_names(settings)

    generated = create_controller_bones(context, armature_object, mapping, scale, bone_names, settings)
    log_line(context, "Created generated bones: " + ", ".join(generated))
    assign_collections(armature_object, bone_names)
    configure_source_bones(context, armature_object, mapping, settings, bone_names)
    configure_pose_bones(armature_object, shapes, scale, settings.auto_hide_helpers, bone_names)
    align_controls_to_current_pose(context, armature_object, mapping, scale, bone_names)
    create_constraints(context, armature_object, mapping, before_matrices, bone_names)
    context.view_layer.update()

    after_source = snapshot_pose(armature_object, tracked_bones)
    after_controls = snapshot_pose(armature_object, list(bone_names.values()))
    log_snapshot(context, "After generation source bone transforms:", after_source)
    log_snapshot(context, "After generation generated control transforms:", after_controls)
    log_delta(context, "Source bone transform delta after generation:", before, after_source)

    armature_object[ADDON_ID] = True
    return generated

def delete_control_rig(context, armature_object):
    """Remove all generated elements from the armature."""
    log_line(context, f"Delete requested for armature: {armature_object.name}")
    remove_generated_constraints(armature_object)
    remove_generated_fcurves(armature_object)
    restore_extra_source_bones(armature_object)
    restore_extra_objects()

    generated_names = get_generated_bone_names(armature_object)
    with ObjectMode(context, armature_object, "EDIT"):
        edit_bones = armature_object.data.edit_bones
        for name in generated_names:
            bone = edit_bones.get(name)
            if bone:
                edit_bones.remove(bone)

    return True

def has_control_rig(armature_object):
    """Check if the armature has any bones tagged as generated."""
    return bool(get_generated_bone_names(armature_object))
