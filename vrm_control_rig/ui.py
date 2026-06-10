"""View3D sidebar panel."""

import bpy

from .detection import detect_humanoid_bones
from .rig import has_control_rig
from .utils import active_armature
from .constants import FOLLOW_ROOT_PROPERTY


class VRMCONTROLRIG_PT_panel(bpy.types.Panel):
    bl_label = "VRM Control Rig"
    bl_idname = "VRMCONTROLRIG_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "VRM Control Rig"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.vrm_control_rig
        armature = active_armature(context)

        if not armature:
            box = layout.box()
            box.label(text="Select a VRM armature.", icon="ERROR")
            return

        mapping, missing = detect_humanoid_bones(armature)
        has_rig = has_control_rig(armature)

        status = layout.box()
        status.label(text=armature.name, icon="ARMATURE_DATA")
        if missing:
            status.label(text="Missing required bones:", icon="ERROR")
            for bone_name in missing[:8]:
                status.label(text=bone_name)
            if len(missing) > 8:
                status.label(text=f"...and {len(missing) - 8} more")
        else:
            status.label(text=f"Detected {len(mapping)} humanoid bones.", icon="CHECKMARK")

        if armature.mode == "POSE" and context.active_pose_bone:
            pb = context.active_pose_bone
            if FOLLOW_ROOT_PROPERTY in pb.keys():
                ik_box = layout.box()
                ik_box.label(text=f"IK Settings: {pb.name}", icon="CONSTRAINT_BONE")
                ik_box.prop(pb, f'["{FOLLOW_ROOT_PROPERTY}"]', text="Stick to Root", slider=True)

        layout.operator("vrm_control_rig.generate", icon="CON_ARMATURE")

        row = layout.row(align=True)
        row.enabled = has_rig
        row.operator("vrm_control_rig.regenerate", icon="FILE_REFRESH")
        row.operator("vrm_control_rig.delete", icon="TRASH")

        layout.separator()

        options = layout.box()
        options.label(text="Options")
        options.prop(settings, "controller_scale")
        options.prop(settings, "auto_hide_helpers")
        options.prop(settings, "source_bones_wireframe")
        options.prop(settings, "remove_extra_source_bones")
        options.prop(settings, "use_random_names")
        options.prop(settings, "enable_diagnostics")
        options.prop(settings, "clear_log_on_generate")

        bake = layout.box()
        bake.label(text="Bake")
        row = bake.row(align=True)
        row.prop(settings, "bake_frame_start")
        row.prop(settings, "bake_frame_end")
        bake.prop(settings, "remove_constraints_after_bake")
        bake.prop(settings, "delete_controls_after_bake")
        bake.operator("vrm_control_rig.bake_to_skeleton", icon="ACTION")

        layout.operator("vrm_control_rig.validate", icon="VIEWZOOM")


CLASSES = (VRMCONTROLRIG_PT_panel,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
