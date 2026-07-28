import bpy

from .util import (
    BACKWARDS_COMPATIBILITY_FILES_DIR,
    import_and_check_export,
    save_failed,
)

_DIR = BACKWARDS_COMPATIBILITY_FILES_DIR / "blender_5_0_to_5_1"
if bpy.app.version[0] == 5 and bpy.app.version[1] == 1:

    def test_backward_compatibility_string_to_curves():
        try:
            import_and_check_export(
                import_file=_DIR / "5_0_string_to_curves.json",
                export_file=_DIR / "5_1_string_to_curves.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_string_to_curves.__name__}")
            raise

    def test_backward_compatibility_uv_unwrap():
        try:
            import_and_check_export(
                import_file=_DIR / "5_0_uv_unwrap.json",
                export_file=_DIR / "5_1_uv_unwrap.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_uv_unwrap.__name__}")
            raise

    def test_backward_compatibility_pack_uv_islands():
        try:
            import_and_check_export(
                import_file=_DIR / "5_0_pack_uv_islands.json",
                export_file=_DIR / "5_1_pack_uv_islands.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_pack_uv_islands.__name__}")
            raise

    def test_backward_compatibility_fill_curve():
        try:
            import_and_check_export(
                import_file=_DIR / "5_0_fill_curve.json",
                export_file=_DIR / "5_1_fill_curve.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_fill_curve.__name__}")
            raise
