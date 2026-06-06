"""VRM Control Rig addon.

Creates lightweight animation controls on an existing VRM humanoid armature
without replacing or reorganizing the source skeleton.
"""

bl_info = {
    "name": "VRM Control Rig",
    "author": "OpenAI",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > VRM Control Rig",
    "description": "Generate lightweight IK controls on top of a VRM humanoid skeleton.",
    "category": "Animation",
}

from . import operators, properties, ui


MODULES = (
    properties,
    operators,
    ui,
)


def register():
    for module in MODULES:
        module.register()


def unregister():
    for module in reversed(MODULES):
        module.unregister()

