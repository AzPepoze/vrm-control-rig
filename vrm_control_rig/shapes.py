"""Custom shape creation for controller bones."""

import math

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
        "root": _ensure_shape(collection, "VCR_Shape_Root_Arrows", _root_arrows_mesh),
        "ik": _ensure_shape(collection, "VCR_Shape_IK", _octa_mesh),
        "pole": _ensure_shape(collection, "VCR_Shape_Pole", _pyramid_mesh),
        "eye": _ensure_shape(collection, "VCR_Shape_Eye", _eye_mesh),
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


def _root_arrows_mesh(name):
    verts = []
    edges = []
    radius = 0.75
    segments = 48

    for index in range(segments):
        angle = (index / segments) * 6.283185307179586
        verts.append((math.cos(angle) * radius, math.sin(angle) * radius, 0.0))
        edges.append((index, (index + 1) % segments))

    def add_line(start, end):
        start_index = len(verts)
        verts.extend([start, end])
        edges.append((start_index, start_index + 1))
        return start_index + 1

    arrow = 1.15
    head = 0.18
    for end, left, right in (
        ((arrow, 0, 0), (arrow - head, head, 0), (arrow - head, -head, 0)),
        ((-arrow, 0, 0), (-arrow + head, head, 0), (-arrow + head, -head, 0)),
        ((0, arrow, 0), (head, arrow - head, 0), (-head, arrow - head, 0)),
        ((0, -arrow, 0), (head, -arrow + head, 0), (-head, -arrow + head, 0)),
    ):
        end_index = add_line((0, 0, 0), end)
        left_index = len(verts)
        verts.extend([left, end, right])
        edges.extend([(left_index, end_index), (end_index, left_index + 2)])

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


def _eye_mesh(name):
    verts = [
        (-0.65, 0, 0),
        (-0.35, 0.25, 0),
        (0, 0.35, 0),
        (0.35, 0.25, 0),
        (0.65, 0, 0),
        (0.35, -0.25, 0),
        (0, -0.35, 0),
        (-0.35, -0.25, 0),
        (0, 0, 0),
    ]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 0), (8, 2), (8, 6)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    return mesh
