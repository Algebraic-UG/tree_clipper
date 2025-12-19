import bpy

from pathlib import Path

from .util import (
    BINARY_BLEND_FILES_DIR,
    save_failed,
    round_trip_with_same_external,
    make_everything_local,
)


_DIR = BINARY_BLEND_FILES_DIR / "microscopy_nodes"


def test_microscopy_nodes():
    path = _DIR / "microscopy_nodes.blend"
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))

        make_everything_local()

        round_trip_with_same_external(name="axes", is_material=False)

        round_trip_with_same_external(name="DAPI volume", is_material=True)
        round_trip_with_same_external(name="Material", is_material=True)
        round_trip_with_same_external(name="NHS-ester volume", is_material=True)
        round_trip_with_same_external(name="Slice Cube", is_material=True)
        round_trip_with_same_external(name="ab-tubulin volume", is_material=True)
        round_trip_with_same_external(
            name="acetylated tubulin volume", is_material=True
        )
        round_trip_with_same_external(name="axes", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_microscopy_nodes.__name__}")
        raise
