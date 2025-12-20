import bpy

from .util import BINARY_BLEND_FILES_DIR, save_failed, round_trip


_DIR = BINARY_BLEND_FILES_DIR / "typst_importer"


def test_blender_assets():
    path = _DIR / "blender_assets.blend"
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))

        round_trip(original_name="FONT_FILL", is_material=False)
        round_trip(original_name="JUMP", is_material=False)

        round_trip(original_name="GPFILL", is_material=True)
        # doesn't have a node tree?
        # round_trip_with_same_external(name="GPStroke", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_blender_assets.__name__}")
        raise
