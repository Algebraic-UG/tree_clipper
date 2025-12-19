import bpy

from .util import BINARY_BLEND_FILES_DIR, save_failed, round_trip_with_same_external


_DIR = BINARY_BLEND_FILES_DIR / "molecular_nodes"


def test_node_data_file():
    path = _DIR / "node_data_file.blend"
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))

        round_trip_with_same_external(name="NodeStorage", is_material=False)

        round_trip_with_same_external(name="MN Ambient Occlusion", is_material=True)
        round_trip_with_same_external(name="MN Default", is_material=True)
        round_trip_with_same_external(name="MN Flat Outline", is_material=True)
        round_trip_with_same_external(name="MN Squishy", is_material=True)
        round_trip_with_same_external(name="MN Transparent Outline", is_material=True)
        round_trip_with_same_external(name="MN_micrograph_material", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_node_data_file.__name__}")
        raise
