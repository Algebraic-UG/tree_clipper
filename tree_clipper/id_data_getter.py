import bpy

from typing import Callable

_ID_TYPE_TO_DATA_BLOCK: dict[str, Callable[[], bpy.types.bpy_prop_collection]] = {
    "ACTION": lambda: bpy.data.actions,
    "ARMATURE": lambda: bpy.data.armatures,
    "BRUSH": lambda: bpy.data.brushes,
    "CACHEFILE": lambda: bpy.data.cache_files,
    "CAMERA": lambda: bpy.data.cameras,
    "COLLECTION": lambda: bpy.data.collections,
    "CURVE": lambda: bpy.data.curves,
    # "CURVES": ???,
    "FONT": lambda: bpy.data.fonts,
    "GREASEPENCIL": lambda: bpy.data.annotations,
    "GREASEPENCIL_V3": lambda: bpy.data.grease_pencils,
    "IMAGE": lambda: bpy.data.images,
    "KEY": lambda: bpy.data.shape_keys,
    "LATTICE": lambda: bpy.data.lattices,
    "LIBRARY": lambda: bpy.data.libraries,
    "LIGHT": lambda: bpy.data.lights,
    "LIGHT_PROBE": lambda: bpy.data.lightprobes,
    "LINESTYLE": lambda: bpy.data.linestyles,
    "MASK": lambda: bpy.data.masks,
    "MATERIAL": lambda: bpy.data.materials,
    "MESH": lambda: bpy.data.meshes,
    "META": lambda: bpy.data.metaballs,
    "MOVIECLIP": lambda: bpy.data.movieclips,
    "NODETREE": lambda: bpy.data.node_groups,
    "OBJECT": lambda: bpy.data.objects,
    "PAINTCURVE": lambda: bpy.data.paint_curves,
    "PALETTE": lambda: bpy.data.palettes,
    "PARTICLE": lambda: bpy.data.particles,
    "POINTCLOUD": lambda: bpy.data.pointclouds,
    "SCENE": lambda: bpy.data.scenes,
    "SCREEN": lambda: bpy.data.screens,
    "SOUND": lambda: bpy.data.sounds,
    "SPEAKER": lambda: bpy.data.speakers,
    "TEXT": lambda: bpy.data.texts,
    "TEXTURE": lambda: bpy.data.textures,
    "VOLUME": lambda: bpy.data.volumes,
    "WINDOWMANAGER": lambda: bpy.data.window_managers,
    "WORKSPACE": lambda: bpy.data.workspaces,
    "WORLD": lambda: bpy.data.worlds,
}


def _make_getter(
    block: bpy.types.bpy_prop_collection, name: str
) -> Callable[[], bpy.types.ID]:
    return lambda: block[name]  # ty: ignore[non-subscriptable]


def make_id_data_getter(obj: bpy.types.ID) -> Callable[[], bpy.types.ID]:
    if obj is None:
        return lambda: None
    assert isinstance(obj, bpy.types.ID)
    if obj.id_type not in _ID_TYPE_TO_DATA_BLOCK:
        raise RuntimeError(f"Can not create getter for pointer to {obj.id_type}")

    return _make_getter(_ID_TYPE_TO_DATA_BLOCK[obj.id_type](), obj.name)
