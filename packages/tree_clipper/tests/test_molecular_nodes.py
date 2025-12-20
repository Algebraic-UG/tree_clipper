import bpy

from .util import BINARY_BLEND_FILES_DIR, save_failed, round_trip


_DIR = BINARY_BLEND_FILES_DIR / "molecular_nodes"


def test_node_data_file():
    path = _DIR / "node_data_file.blend"
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))

        # https://github.com/Algebraic-UG/tree_clipper/issues/115
        bpy.data.node_groups["Style Preset 3"].nodes["Group.004"].inputs[
            2
        ].default_value = "Instance"  # ty:ignore[unresolved-attribute]
        bpy.data.node_groups["Style Preset 4"].nodes["Group.011"].inputs[
            2
        ].default_value = "Instance"  # ty:ignore[unresolved-attribute]

        round_trip(original_name="NodeStorage", is_material=False)

        round_trip(original_name="MN Ambient Occlusion", is_material=True)
        round_trip(original_name="MN Default", is_material=True)
        round_trip(original_name="MN Flat Outline", is_material=True)
        round_trip(original_name="MN Squishy", is_material=True)
        round_trip(original_name="MN Transparent Outline", is_material=True)
        round_trip(original_name="MN_micrograph_material", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_node_data_file.__name__}")
        raise
