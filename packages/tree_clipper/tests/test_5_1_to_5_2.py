import bpy

from .util import (
    BACKWARDS_COMPATIBILITY_FILES_DIR,
    import_and_check_export,
    save_failed,
)

_DIR = BACKWARDS_COMPATIBILITY_FILES_DIR / "blender_5_1_to_5_2"
if bpy.app.version[0] == 5 and bpy.app.version[1] == 2:

    def test_backward_compatibility_value_to_string():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_value_to_string.json",
                export_file=_DIR / "5_2_value_to_string.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_value_to_string.__name__}")
            raise

    def test_backward_compatibility_string_to_value():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_string_to_value.json",
                export_file=_DIR / "5_2_string_to_value.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_string_to_value.__name__}")
            raise

    def test_backward_compatibility_find_in_string():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_find_in_string.json",
                export_file=_DIR / "5_2_find_in_string.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_find_in_string.__name__}")
            raise

    def test_backward_compatibility_capture_attribute():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_capture_attribute.json",
                export_file=_DIR / "5_2_capture_attribute.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_capture_attribute.__name__}")
            raise

    def test_backward_compatibility_subdivision_surface():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_subdivision_surface.json",
                export_file=_DIR / "5_2_subdivision_surface.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_subdivision_surface.__name__}")
            raise

    def test_backward_compatibility_principled_bsdf():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_principled_bsdf.json",
                export_file=_DIR / "5_2_principled_bsdf.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_principled_bsdf.__name__}")
            raise

    def test_backward_compatibility_input_string():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_input_string.json",
                export_file=_DIR / "5_2_input_string.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_input_string.__name__}")
            raise

    def test_backward_compatibility_camera_info():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_camera_info.json",
                export_file=_DIR / "5_2_camera_info.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_camera_info.__name__}")
            raise

    def test_backward_compatibility_raycast():
        try:
            import_and_check_export(
                import_file=_DIR / "5_1_raycast.json",
                export_file=_DIR / "5_2_raycast.json",
            )
        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_backward_compatibility_raycast.__name__}")
            raise
