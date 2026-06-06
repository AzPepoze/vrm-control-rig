"""Addon property definitions."""

import bpy


class VRMControlRigSettings(bpy.types.PropertyGroup):
    controller_scale: bpy.props.FloatProperty(
        name="Controller Size",
        description="Scale multiplier for generated custom shapes and controller placement",
        default=1.0,
        min=0.1,
        max=10.0,
    )
    auto_hide_helpers: bpy.props.BoolProperty(
        name="Auto-hide Helpers",
        description="Hide pole target helper bones after generation",
        default=True,
    )
    source_bones_wireframe: bpy.props.BoolProperty(
        name="Source Bones Wire",
        description="Show the selected armature bones as wire bones so controllers are easier to see",
        default=True,
    )
    remove_extra_source_bones: bpy.props.BoolProperty(
        name="Remove Extra Bones",
        description="Delete non-humanoid source bones such as hair, skirt, and accessory bones when generating controls",
        default=False,
    )
    enable_diagnostics: bpy.props.BoolProperty(
        name="Diagnostics Log",
        description="Write detailed before/after bone transform logs to a Text datablock and the console",
        default=True,
    )
    clear_log_on_generate: bpy.props.BoolProperty(
        name="Clear Log On Generate",
        description="Clear the VRM Control Rig Log text before generating or regenerating",
        default=True,
    )
    bake_frame_start: bpy.props.IntProperty(
        name="Start",
        description="First frame to bake",
        default=1,
        min=-1048574,
        max=1048574,
    )
    bake_frame_end: bpy.props.IntProperty(
        name="End",
        description="Last frame to bake",
        default=250,
        min=-1048574,
        max=1048574,
    )
    remove_constraints_after_bake: bpy.props.BoolProperty(
        name="Remove Constraints",
        description="Remove generated rig constraints after baking visual transforms",
        default=False,
    )
    delete_controls_after_bake: bpy.props.BoolProperty(
        name="Delete Controls",
        description="Delete generated control bones after baking visual transforms",
        default=False,
    )


CLASSES = (VRMControlRigSettings,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.vrm_control_rig = bpy.props.PointerProperty(type=VRMControlRigSettings)


def unregister():
    if hasattr(bpy.types.Scene, "vrm_control_rig"):
        del bpy.types.Scene.vrm_control_rig
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
