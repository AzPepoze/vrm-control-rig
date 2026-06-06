"""Custom shape creation for controller bones."""

import bpy
from mathutils import Vector

from .constants import ADDON_ID, SHAPE_COLLECTION


def ensure_shapes(context):
    """Create or reuse hidden mesh objects for bone custom shapes."""

    collection = bpy.data.collections.get(SHAPE_COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(SHAPE_COLLECTION)
        context.scene.collection.children.link(collection)
    collection.hide_viewport = True
    collection.hide_render = True

    return {
        "root": _ensure_shape(collection, "VCR_Shape_Root", _cube_mesh),
        "ik": _ensure_shape(collection, "VCR_Shape_IK", _octa_mesh),
        "pole": _ensure_shape(collection, "VCR_Shape_Pole", _pyramid_mesh),
    }


def _ensure_shape(collection, name, mesh_factory):
    obj = bpy.data.objects.get(name)
    if obj is not None:
        return obj

    mesh = mesh_factory(name + "Mesh")
    obj = bpy.data.objects.new(name, mesh)
    obj.hide_viewport = True
    obj.hide_render = True
    obj[ADDON_ID] = True
    collection.objects.link(obj)
    return obj


def _cube_mesh(name):
    size = 0.5
    verts = [
        (-size, -size, -size),
        (size, -size, -size),
        (size, size, -size),
        (-size, size, -size),
        (-size, -size, size),
        (size, -size, size),
        (size, size, size),
        (-size, size, size),
    ]
    edges = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    return mesh


def _octa_mesh(name):
    verts = [
        (0, 0, 0.65),
        (0.65, 0, 0),
        (0, 0.65, 0),
        (-0.65, 0, 0),
        (0, -0.65, 0),
        (0, 0, -0.65),
    ]
    edges = [
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (5, 1),
        (5, 2),
        (5, 3),
        (5, 4),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 1),
    ]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    return mesh


def _pyramid_mesh(name):
    verts = [
        Vector((0, 0, 0.7)),
        Vector((-0.45, -0.45, -0.25)),
        Vector((0.45, -0.45, -0.25)),
        Vector((0.45, 0.45, -0.25)),
        Vector((-0.45, 0.45, -0.25)),
    ]
    edges = [(0, 1), (0, 2), (0, 3), (0, 4), (1, 2), (2, 3), (3, 4), (4, 1)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    return mesh

