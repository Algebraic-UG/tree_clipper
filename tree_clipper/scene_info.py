# see https://github.com/Algebraic-UG/tree_clipper/issues/69
# we could probably re-use parts of our export logic, but the use case is completely different:
# we never intend to import this and we only want to check that the scene has the required
# parameters to reconstruct the tree around the nodes that reference it and it's view layers.
# All of this is very ad-hoc and might well break in the future.

import bpy

from typing import Any

from .common import no_clobber, PROP_TYPE_BOOLEAN, NAME

# to help prevent typos
VIEW_LAYERS = "view_layers"
RENDER = "render"
ENGINE = "engine"
CYCLES = "cycles"
AOVS = "aovs"
LIGHTGROUPS = "lightgroups"


def _export_all_writable_boolean_properties(
    obj: bpy.types.bpy_struct,
) -> dict[str, bool]:
    data = {}
    for prop in obj.bl_rna.properties:
        if prop.type == PROP_TYPE_BOOLEAN:
            no_clobber(data, prop.identifier, getattr(obj, prop.identifier))
    return data


# no type hints, sad
def _export_cycles(cycles) -> dict[str, bool]:
    return _export_all_writable_boolean_properties(cycles)


def _export_aovs(aovs: bpy.types.AOVs) -> int:
    return len(aovs)


def _export_lightgroups(lightgroups: bpy.types.Lightgroups) -> int:
    return len(lightgroups)


def _export_render(render: bpy.types.RenderSettings) -> dict[str, Any]:
    return {ENGINE: render.engine}


def _export_view_layer(view_layer: bpy.types.ViewLayer) -> dict[str, Any]:
    data = _export_all_writable_boolean_properties(view_layer)

    no_clobber(data, NAME, view_layer.name)
    no_clobber(data, CYCLES, _export_cycles(view_layer.cycles))
    no_clobber(data, AOVS, _export_aovs(view_layer.aovs))
    no_clobber(data, LIGHTGROUPS, _export_lightgroups(view_layer.lightgroups))

    return data


def export_scene_info(scene: bpy.types.Scene) -> dict[str, Any]:
    return {
        RENDER: _export_render(scene.render),
        VIEW_LAYERS: [
            _export_view_layer(view_layer) for view_layer in scene.view_layers
        ],
    }


def verify_scene_against_info(info: dict[str, Any], scene: bpy.types.Scene):
    pass
