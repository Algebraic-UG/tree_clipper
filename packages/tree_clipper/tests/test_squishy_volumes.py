import bpy

from pathlib import Path

from .util import BINARY_BLEND_FILES_DIR, save_failed, round_trip_with_same_external


_DIR = BINARY_BLEND_FILES_DIR / "squishy_volumes"


def test_new_input():
    path = _DIR / "new_input.blend"
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))

        round_trip_with_same_external(name="Geometry Nodes", is_material=False)
        round_trip_with_same_external(name="Geometry Nodes.001", is_material=False)
        round_trip_with_same_external(
            name="Squishy Volumes Particle", is_material=False
        )

        round_trip_with_same_external(
            name="Squishy Volumes Colored Instances", is_material=True
        )
        round_trip_with_same_external(
            name="Squishy Volumes Display UVW", is_material=True
        )

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_new_input.__name__}")
        raise
