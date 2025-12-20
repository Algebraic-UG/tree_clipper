import bpy

from .util import (
    BINARY_BLEND_FILES_DIR,
    save_failed,
    round_trip,
    make_everything_local,
)


_DIR = BINARY_BLEND_FILES_DIR / "microscopy_nodes"


def test_microscopy_nodes():
    path = _DIR / "microscopy_nodes.blend"
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))

        make_everything_local()

        round_trip(original_name="axes", is_material=False)

        round_trip(original_name="DAPI volume", is_material=True)
        round_trip(original_name="Material", is_material=True)
        round_trip(original_name="NHS-ester volume", is_material=True)
        round_trip(original_name="Slice Cube", is_material=True)
        round_trip(original_name="ab-tubulin volume", is_material=True)
        round_trip(original_name="acetylated tubulin volume", is_material=True)
        round_trip(original_name="axes", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_microscopy_nodes.__name__}")
        raise
