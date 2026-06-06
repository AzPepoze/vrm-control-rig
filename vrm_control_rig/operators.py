"""Operator classes for VRM Control Rig."""

import bpy

from .bake import bake_to_vrm_skeleton, remove_control_animation
from .constants import GENERATED_BONES
from .detection import detect_humanoid_bones, format_missing_bones
from .rig import RigBuildError, delete_control_rig, generate_control_rig, has_control_rig
from .utils import active_armature


class VRMCONTROLRIG_OT_generate(bpy.types.Operator):
    bl_idname = "vrm_control_rig.generate"
    bl_label = "Generate Control Rig"
    bl_description = "Create non-deforming IK controllers on the selected VRM armature"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        armature = active_armature(context)
        if not armature:
            self.report({"ERROR"}, "Select a VRM armature object first.")
            return {"CANCELLED"}

        try:
            created = generate_control_rig(context, armature, regenerate=False)
        except RigBuildError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Generated VRM Control Rig with {len(created)} control bones.")
        return {"FINISHED"}


class VRMCONTROLRIG_OT_regenerate(bpy.types.Operator):
    bl_idname = "vrm_control_rig.regenerate"
    bl_label = "Regenerate Control Rig"
    bl_description = "Delete and rebuild generated control bones and constraints"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        armature = active_armature(context)
        if not armature:
            self.report({"ERROR"}, "Select a VRM armature object first.")
            return {"CANCELLED"}

        try:
            created = generate_control_rig(context, armature, regenerate=True)
        except RigBuildError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        self.report({"INFO"}, f"Regenerated VRM Control Rig with {len(created)} control bones.")
        return {"FINISHED"}


class VRMCONTROLRIG_OT_delete(bpy.types.Operator):
    bl_idname = "vrm_control_rig.delete"
    bl_label = "Delete Control Rig"
    bl_description = "Remove generated control bones, generated constraints, and control animation channels"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        armature = active_armature(context)
        if not armature:
            self.report({"ERROR"}, "Select a VRM armature object first.")
            return {"CANCELLED"}

        if not has_control_rig(armature):
            self.report({"INFO"}, "No generated VRM Control Rig found on the selected armature.")
            return {"CANCELLED"}

        delete_control_rig(context, armature)
        self.report({"INFO"}, "Deleted generated VRM Control Rig.")
        return {"FINISHED"}


class VRMCONTROLRIG_OT_bake(bpy.types.Operator):
    bl_idname = "vrm_control_rig.bake_to_skeleton"
    bl_label = "Bake To VRM Skeleton"
    bl_description = "Bake visual constrained motion to original VRM humanoid bones"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        armature = active_armature(context)
        if not armature:
            self.report({"ERROR"}, "Select a VRM armature object first.")
            return {"CANCELLED"}

        settings = context.scene.vrm_control_rig
        try:
            bake_to_vrm_skeleton(
                context,
                armature,
                settings.bake_frame_start,
                settings.bake_frame_end,
                remove_constraints=settings.remove_constraints_after_bake,
            )
        except (RuntimeError, ValueError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}

        if settings.delete_controls_after_bake:
            delete_control_rig(context, armature)
        else:
            remove_control_animation(armature)

        self.report({"INFO"}, "Baked control rig motion to original VRM skeleton.")
        return {"FINISHED"}


class VRMCONTROLRIG_OT_validate(bpy.types.Operator):
    bl_idname = "vrm_control_rig.validate"
    bl_label = "Validate VRM Bones"
    bl_description = "Check selected armature for required VRM humanoid bones"
    bl_options = {"REGISTER"}

    def execute(self, context):
        armature = active_armature(context)
        if not armature:
            self.report({"ERROR"}, "Select a VRM armature object first.")
            return {"CANCELLED"}

        _mapping, missing = detect_humanoid_bones(armature)
        if missing:
            self.report({"ERROR"}, "Missing required VRM humanoid bones: " + format_missing_bones(missing))
            return {"CANCELLED"}

        existing_controls = [name for name in GENERATED_BONES if name in armature.data.bones]
        message = "Required VRM humanoid bones detected."
        if existing_controls:
            message += f" Existing control rig bones: {len(existing_controls)}."
        self.report({"INFO"}, message)
        return {"FINISHED"}


CLASSES = (
    VRMCONTROLRIG_OT_generate,
    VRMCONTROLRIG_OT_regenerate,
    VRMCONTROLRIG_OT_delete,
    VRMCONTROLRIG_OT_bake,
    VRMCONTROLRIG_OT_validate,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

