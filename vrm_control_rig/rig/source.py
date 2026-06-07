"""Source bone configuration and cleanup."""

import bpy
from ..constants import ADDON_ID, GENERATED_BONES
from ..logs import log_line
from ..utils import ObjectMode, is_generated
from .fingers import detect_finger_chains, _norm_name

HIDDEN_EXTRA_BONE_TAG = ADDON_ID + "_hidden_extra_bone"
HIDDEN_EXTRA_OBJECT_TAG = ADDON_ID + "_hidden_extra_object"

def configure_source_bones(context, armature_object, mapping, settings, bone_names):
    """Apply wireframe display and optional extra bone cleanup."""
    if getattr(settings, "source_bones_wireframe", False):
        try:
            armature_object.data.display_type = "WIRE"
            armature_object.show_in_front = True
        except (AttributeError, TypeError, ValueError):
            pass

    restore_extra_source_bones(armature_object)
    restore_extra_objects()
    if getattr(settings, "remove_extra_source_bones", False):
        _remove_extra_source_bones(context, armature_object, mapping, bone_names)
        _hide_extra_objects(context)

def restore_extra_source_bones(armature_object):
    """Reveal source bones that were hidden during generation."""
    for bone in armature_object.data.bones:
        if _is_generated_extra_hidden(bone):
            bone.hide = False
            _clear_hidden_extra_tag(bone)

def restore_extra_objects():
    """Reveal external objects (like hair meshes) that were hidden."""
    for obj in bpy.data.objects:
        try:
            if not obj.get(HIDDEN_EXTRA_OBJECT_TAG, False):
                continue
            obj.hide_viewport = False
            obj.hide_render = False
            try:
                obj.hide_set(False)
            except (AttributeError, TypeError, RuntimeError):
                pass
            del obj[HIDDEN_EXTRA_OBJECT_TAG]
        except TypeError:
            continue

def tracked_source_bones(mapping):
    """Return a list of bone names from the mapping that should be tracked for logging."""
    keys = (
        "hips", "spine", "chest", "upper_chest", "neck", "head", "eye.L", "eye.R",
        "upper_arm.L", "lower_arm.L", "hand.L", "upper_arm.R", "lower_arm.R", "hand.R",
        "upper_leg.L", "lower_leg.L", "foot.L", "upper_leg.R", "lower_leg.R", "foot.R",
    )
    return [mapping[key] for key in keys if key in mapping]

def _source_root_bone(bones, mapping):
    """Find the root bone of the source skeleton (usually parent of hips)."""
    hips = bones.get(mapping.get("hips", ""))
    if hips and hips.parent:
        return hips.parent

    for bone in bones:
        if is_generated(bone):
            continue
        if _norm_name(bone.name) in {"root", "armatureroot"}:
            return bone

    return None

def _remove_extra_source_bones(context, armature_object, mapping, bone_names):
    controlled_source_bones = set(mapping.values())
    for chain in detect_finger_chains(armature_object.data.bones, bone_names).values():
        controlled_source_bones.update(chain)

    remove_names = [
        bone.name
        for bone in armature_object.data.bones
        if bone.name.startswith("J_Sec") and not is_generated(bone) and bone.name not in controlled_source_bones
    ]
    if not remove_names:
        return

    with ObjectMode(context, armature_object, "EDIT"):
        edit_bones = armature_object.data.edit_bones
        for name in remove_names:
            bone = edit_bones.get(name)
            if bone:
                edit_bones.remove(bone)

def _hide_extra_objects(context):
    hidden = 0
    for obj in context.scene.objects:
        if "hair" not in _norm_name(obj.name):
            continue
        if obj.type == "ARMATURE":
            continue
        obj[HIDDEN_EXTRA_OBJECT_TAG] = True
        obj.hide_viewport = True
        obj.hide_render = True
        try:
            obj.hide_set(True)
        except (AttributeError, TypeError, RuntimeError):
            pass
        hidden += 1

    if hidden:
        log_line(context, f"Hid {hidden} hair object(s) for Remove Extra Bones.")

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
