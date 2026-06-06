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
        "root": _ensure_shape(collection, "VCR_Shape_Root_Floor_Box", _root_floor_box_mesh),
        "box": _ensure_shape(collection, "VCR_Shape_Box", _box_mesh),
        "hand": _ensure_shape(collection, "VCR_Shape_Hand_D", _rounded_d_mesh),
        "foot": _ensure_shape(collection, "VCR_Shape_Foot_D", _rounded_d_mesh),
        "finger": _ensure_shape(collection, "VCR_Shape_Finger_Curl", _finger_curl_mesh),
        "pole": _ensure_shape(collection, "VCR_Shape_Pole", _pyramid_mesh),
        "eye": _ensure_shape(collection, "VCR_Shape_Eye", _eye_mesh),
    }


def _ensure_shape(collection, name, mesh_factory):
    obj = bpy.data.objects.get(name)
    if obj is not None:
        mesh = mesh_factory(name + "Mesh")
        obj.data = mesh
        return obj

    mesh = mesh_factory(name + "Mesh")
    obj = bpy.data.objects.new(name, mesh)
    obj.hide_viewport = True
    obj.hide_render = True
    obj[ADDON_ID] = True
    collection.objects.link(obj)
    return obj


def _root_floor_box_mesh(name):
    verts = []
    edges = []
    radius = 1.15
    segments = 48

    for index in range(segments):
        angle = (index / segments) * 6.283185307179586
        verts.append((math.cos(angle) * radius, math.sin(angle) * radius, 0.0))
        edges.append((index, (index + 1) % segments))

    def add_polyline(points, closed=False):
        start_index = len(verts)
        verts.extend(points)
        for offset in range(len(points) - 1):
            edges.append((start_index + offset, start_index + offset + 1))
        if closed:
            edges.append((start_index + len(points) - 1, start_index))
        return start_index

    box = 0.42
    add_polyline(
        [
            (-box, -box, 0.0),
            (box, -box, 0.0),
            (box, box, 0.0),
            (-box, box, 0.0),
        ],
        closed=True,
    )

    arrow = 1.55
    head = 0.22
    for end, left, right in (
        ((arrow, 0, 0), (arrow - head, head, 0), (arrow - head, -head, 0)),
        ((-arrow, 0, 0), (-arrow + head, head, 0), (-arrow + head, -head, 0)),
        ((0, arrow, 0), (head, arrow - head, 0), (-head, arrow - head, 0)),
        ((0, -arrow, 0), (head, -arrow + head, 0), (-head, -arrow + head, 0)),
    ):
        line_index = add_polyline([(0, 0, 0), end])
        end_index = line_index + 1
        left_index = add_polyline([left, right])
        edges.extend([(left_index, end_index), (end_index, left_index + 1)])

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    return mesh


def _box_mesh(name):
    half = 0.5
    verts = [
        (-half, -half, -half),
        (half, -half, -half),
        (half, half, -half),
        (-half, half, -half),
        (-half, -half, half),
        (half, -half, half),
        (half, half, half),
        (-half, half, half),
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


def _rounded_d_mesh(name):
    verts = []
    edges = []
    width = 1.2
    height = 0.78
    straight = -0.35
    radius = height * 0.5
    segments = 16

    verts.append((straight, -radius, 0.0))
    verts.append((straight, radius, 0.0))
    edges.append((0, 1))

    start_index = len(verts)
    for index in range(segments + 1):
        angle = math.pi * 0.5 - (math.pi * index / segments)
        verts.append((straight + width * 0.5 + math.cos(angle) * radius, math.sin(angle) * radius, 0.0))
        if index:
            edges.append((start_index + index - 1, start_index + index))
    edges.append((1, start_index))
    edges.append((start_index + segments, 0))

    center_index = len(verts)
    verts.append((0.0, 0.0, 0.0))
    edges.extend([(center_index, 0), (center_index, 1), (center_index, start_index + segments // 2)])

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    return mesh


def _finger_curl_mesh(name):
    verts = []
    edges = []
    segments = 20
    radius = 0.45

    for index in range(segments + 1):
        angle = math.pi * 1.25 - (math.pi * 1.5 * index / segments)
        verts.append((math.cos(angle) * radius, math.sin(angle) * radius, 0.0))
        if index:
            edges.append((index - 1, index))

    tip = verts[-1]
    head = 0.12
    tip_index = len(verts) - 1
    left_index = len(verts)
    verts.extend([(tip[0] - head, tip[1] + head, 0.0), (tip[0] - head, tip[1] - head, 0.0)])
    edges.extend([(tip_index, left_index), (tip_index, left_index + 1)])

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
