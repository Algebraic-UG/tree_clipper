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
PASS_CRYPTOMATTE_DEPTH = "pass_cryptomatte_depth"
ENGINE_WORKBENCH = "BLENDER_WORKBENCH"
ENGINE_EEVEE = "BLENDER_EEVEE"
ENGINE_CYCLES = "CYCLES"
USE_PASS_COMBINED = "use_pass_combined"
USE_PASS_Z = "use_pass_z"
USE_PASS_GREASE_PENCIL = "use_pass_grease_pencil"


def _export_all_boolean_properties(
    obj: bpy.types.bpy_struct,
) -> dict[str, bool]:
    data = {}
    for prop in obj.bl_rna.properties:
        if prop.type == PROP_TYPE_BOOLEAN:
            no_clobber(data, prop.identifier, getattr(obj, prop.identifier))
    return data


def _verify_all_boolean_properties(
    info: dict[str, Any],
    obj: bpy.types.bpy_struct,
):
    for prop in obj.bl_rna.properties:
        if prop.type == PROP_TYPE_BOOLEAN:
            key = prop.identifier
            value = info[key]
            assert value == getattr(obj, key), f"Setting {key} must be {value}"


def _verify_listed_properties(
    info: dict[str, Any], obj: bpy.types.bpy_struct, ids: list[str]
):
    for prop in [obj.bl_rna.properties[i] for i in ids]:
        key = prop.identifier
        value = info[key]
        assert value == getattr(obj, key), f"Setting {key} must be {value}"


# no type hints, sad
def _export_cycles(cycles) -> dict[str, bool]:
    return _export_all_boolean_properties(cycles)


def _verify_cycles(info: dict[str, Any], cycles):
    _verify_all_boolean_properties(info, cycles)


def _export_aovs(aovs: bpy.types.AOVs) -> int:
    return len(aovs)


def _verify_aovs(info: int, aovs: bpy.types.AOVs):
    assert info == len(aovs), f"The number of Shader AOVs must be {info}"


def _export_lightgroups(lightgroups: bpy.types.Lightgroups) -> int:
    return len(lightgroups)


def _verify_lightgroups(info: int, lightgroups: bpy.types.Lightgroups):
    assert info == len(lightgroups), f"The number of Light Groups must be {info}"


def _export_render(render: bpy.types.RenderSettings) -> dict[str, Any]:
    return {ENGINE: render.engine}


def _verify_render(info: dict[str, Any], render: bpy.types.RenderSettings):
    assert info[ENGINE] == render.engine, f"Render engine must be {info[ENGINE]}"


def _export_view_layer(view_layer: bpy.types.ViewLayer) -> dict[str, Any]:
    data = _export_all_boolean_properties(view_layer)

    no_clobber(data, NAME, view_layer.name)
    no_clobber(data, PASS_CRYPTOMATTE_DEPTH, view_layer.pass_cryptomatte_depth)
    no_clobber(data, CYCLES, _export_cycles(view_layer.cycles))
    no_clobber(data, AOVS, _export_aovs(view_layer.aovs))
    no_clobber(data, LIGHTGROUPS, _export_lightgroups(view_layer.lightgroups))

    return data


def _verify_view_layer(
    info: dict[str, Any], view_layer: bpy.types.ViewLayer, engine: str
):
    _verify_listed_properties(
        info, view_layer, [USE_PASS_COMBINED, USE_PASS_Z, USE_PASS_GREASE_PENCIL]
    )

    if engine == ENGINE_WORKBENCH:
        return

    _verify_listed_properties(info, view_layer, [PASS_CRYPTOMATTE_DEPTH])
    _verify_all_boolean_properties(info, view_layer)
    _verify_aovs(info[AOVS], view_layer.aovs)

    if engine == ENGINE_EEVEE:
        return

    _verify_cycles(info[CYCLES], view_layer.cycles)
    _verify_lightgroups(info[LIGHTGROUPS], view_layer.lightgroups)

    if engine == ENGINE_CYCLES:
        return

    assert False, "unknown engine"


def export_scene_info(scene: bpy.types.Scene) -> dict[str, Any]:
    return {
        RENDER: _export_render(scene.render),
        VIEW_LAYERS: [
            _export_view_layer(view_layer) for view_layer in scene.view_layers
        ],
    }


def verify_scene(info: dict[str, Any], scene: bpy.types.Scene):
    _verify_render(info[RENDER], scene.render)

    engine = info[RENDER][ENGINE]
    for view_layer_info in info[VIEW_LAYERS]:
        view_layer = next(
            (
                view_layer
                for view_layer in scene.view_layers
                if view_layer.name == view_layer_info[NAME]
            ),
            None,
        )
        if view_layer is None:
            raise RuntimeError(f"Missing View Layer {view_layer_info[NAME]}")
        _verify_view_layer(view_layer_info, view_layer, engine)
