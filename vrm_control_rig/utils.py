"""Utility helpers for mode, selection, and generated data cleanup."""

import bpy

from .constants import ADDON_ID, GENERATED_BONES, IK_CONSTRAINT_NAME, ROOT_CONSTRAINT_NAME


def active_armature(context):
    obj = context.object
    if obj and obj.type == "ARMATURE":
        return obj
    return None


class ObjectMode:
    """Context manager that restores the active object and previous mode."""

    def __init__(self, context, obj, mode="OBJECT"):
        self.context = context
        self.obj = obj
        self.mode = mode
        self.previous_object = context.view_layer.objects.active
        self.previous_mode = self.previous_object.mode if self.previous_object else "OBJECT"

    def __enter__(self):
        if self.context.object and self.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        self.context.view_layer.objects.active = self.obj
        self.obj.select_set(True)
        bpy.ops.object.mode_set(mode=self.mode)
        return self.obj

    def __exit__(self, exc_type, exc_value, traceback):
        if self.context.object and self.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        if self.previous_object:
            self.context.view_layer.objects.active = self.previous_object
            try:
                bpy.ops.object.mode_set(mode=self.previous_mode)
            except RuntimeError:
                pass


def tag_generated(id_block):
    try:
        id_block[ADDON_ID] = True
    except TypeError:
        pass


def is_generated(id_block):
    return bool(id_block.get(ADDON_ID, False))


def remove_generated_constraints(armature_object):
    for pose_bone in armature_object.pose.bones:
        for constraint in list(pose_bone.constraints):
            if constraint.name in {IK_CONSTRAINT_NAME, ROOT_CONSTRAINT_NAME} or constraint.get(ADDON_ID):
                pose_bone.constraints.remove(constraint)


def remove_generated_fcurves(armature_object):
    animation_data = armature_object.animation_data
    if not animation_data or not animation_data.action:
        return
    action = animation_data.action
    generated_paths = tuple(f'pose.bones["{name}"]' for name in GENERATED_BONES)
    for fcurves in _action_fcurve_collections(action):
        for fcurve in list(fcurves):
            if fcurve.data_path.startswith(generated_paths):
                fcurves.remove(fcurve)


def _action_fcurve_collections(action):
    """Yield f-curve collections for legacy and Blender 5 layered actions."""

    if hasattr(action, "fcurves"):
        yield action.fcurves
        return

    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                if hasattr(channelbag, "fcurves"):
                    yield channelbag.fcurves
