import bpy

from typing import Callable

_ID_TYPE_TO_DATA_BLOCK: dict[str, bpy.types.bpy_prop_collection] = {
    "ACTION": bpy.data.actions,
    "ARMATURE": bpy.data.armatures,
    "BRUSH": bpy.data.brushes,
    "CACHEFILE": bpy.data.cache_files,
    "CAMERA": bpy.data.cameras,
    "COLLECTION": bpy.data.collections,
    "CURVE": bpy.data.curves,
    # "CURVES": ???,
    "FONT": bpy.data.fonts,
    # "GREASEPENCIL": ???,
    "GREASEPENCIL_V3": bpy.data.grease_pencils,
    "IMAGE": bpy.data.images,
    "KEY": bpy.data.shape_keys,
    "LATTICE": bpy.data.lattices,
    "LIBRARY": bpy.data.libraries,
    "LIGHT": bpy.data.lights,
    "LIGHT_PROBE": bpy.data.lightprobes,
    "LINESTYLE": bpy.data.linestyles,
    "MASK": bpy.data.masks,
    "MATERIAL": bpy.data.materials,
    "MESH": bpy.data.meshes,
    "META": bpy.data.metaballs,
    "MOVIECLIP": bpy.data.movieclips,
    "NODETREE": bpy.data.node_groups,
    "OBJECT": bpy.data.objects,
    "PAINTCURVE": bpy.data.paint_curves,
    "PALETTE": bpy.data.palettes,
    "PARTICLE": bpy.data.particles,
    "POINTCLOUD": bpy.data.pointclouds,
    "SCENE": bpy.data.scenes,
    "SCREEN": bpy.data.screens,
    "SOUND": bpy.data.sounds,
    "SPEAKER": bpy.data.speakers,
    "TEXT": bpy.data.texts,
    "TEXTURE": bpy.data.textures,
    "VOLUME": bpy.data.volumes,
    "WINDOWMANAGER": bpy.data.window_managers,
    "WORKSPACE": bpy.data.workspaces,
    "WORLD": bpy.data.worlds,
}


def _make_getter(
    block: bpy.types.bpy_prop_collection, name: str
) -> Callable[[], bpy.types.ID]:
    return lambda: block[name]  # ty: ignore[non-subscriptable]


def make_id_data_getter(ptr: bpy.types.PointerProperty) -> Callable[[], bpy.types.ID]:
    if ptr is None:
        return lambda: None
    assert isinstance(ptr, bpy.types.ID)
    if ptr.id_type not in _ID_TYPE_TO_DATA_BLOCK:
        raise RuntimeError(f"Can not create getter for pointer to {ptr.id_type}")

    return _make_getter(_ID_TYPE_TO_DATA_BLOCK[ptr.id_type], ptr.name)
