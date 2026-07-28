import bpy

from .util import (
    NODE_ASSETS_DIR,
    round_trip,
    save_failed,
)

if (bpy.app.version[0] == 5 and bpy.app.version[1] >= 2) or bpy.app.version[0] > 5:

    def test_geometry_nodes_dynamics_assets():
        try:
            bpy.ops.wm.open_mainfile(
                filepath=str(NODE_ASSETS_DIR / "geometry_nodes_dynamics_assets.blend")
            )

            round_trip(original_name="Cloth Dynamics (Experimental)", is_material=False)
            round_trip(original_name="Collider", is_material=False)
            round_trip(original_name="Hair Dynamics", is_material=False)

        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_geometry_nodes_dynamics_assets.__name__}")
            raise

    def test_procedural_hair_node_assets():
        try:
            bpy.ops.wm.open_mainfile(
                filepath=str(NODE_ASSETS_DIR / "procedural_hair_node_assets.blend")
            )

            round_trip(original_name="Attach Hair Curves to Surface", is_material=False)
            round_trip(original_name="Blend Hair Curves", is_material=False)
            round_trip(original_name="Braid Hair Curves", is_material=False)
            round_trip(original_name="Clump Hair Curves", is_material=False)
            round_trip(original_name="Create Guide Index Map", is_material=False)
            round_trip(original_name="Curl Hair Curves", is_material=False)
            round_trip(original_name="Displace Hair Curves", is_material=False)
            round_trip(original_name="Duplicate Hair Curves", is_material=False)
            round_trip(original_name="Frizz Hair Curves", is_material=False)
            round_trip(original_name="Generate Hair Curves", is_material=False)
            round_trip(original_name="Hair Curves Noise", is_material=False)
            round_trip(original_name="Interpolate Hair Curves", is_material=False)
            round_trip(original_name="Redistribute Curve Points", is_material=False)
            round_trip(original_name="Restore Curve Segment Length", is_material=False)
            round_trip(original_name="Roll Hair Curves", is_material=False)
            round_trip(original_name="Rotate Hair Curves", is_material=False)
            round_trip(original_name="Set Hair Curve Profile", is_material=False)
            round_trip(original_name="Shrinkwrap Hair Curves", is_material=False)
            round_trip(original_name="Smooth Hair Curves", is_material=False)
            round_trip(original_name="Straighten Hair Curves", is_material=False)
            round_trip(original_name="Trim Hair Curves", is_material=False)

        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_procedural_hair_node_assets.__name__}")
            raise

    # TODO:
    # def test_principal_components():

    def test_compositing_nodes_essentials():
        try:
            bpy.ops.wm.open_mainfile(
                filepath=str(NODE_ASSETS_DIR / "compositing_nodes_essentials.blend")
            )

            round_trip(original_name=".Halation 3.021", is_material=False)
            round_trip(
                original_name=".Multisample Displace Group 2.010", is_material=False
            )
            round_trip(original_name=".Noise Maschine 3.021", is_material=False)
            round_trip(original_name=".Noisegroup Internal 3.021", is_material=False)
            round_trip(original_name="3D to Screen Space", is_material=False)
            round_trip(original_name="Cheap Blur 2.001", is_material=False)
            round_trip(original_name="Chromatic Aberration", is_material=False)
            round_trip(original_name="Combine Cylindrical", is_material=False)
            round_trip(original_name="Combine Spherical", is_material=False)
            round_trip(original_name="Film Grain", is_material=False)
            round_trip(original_name="log space >1.001", is_material=False)
            round_trip(original_name="Project with Depth", is_material=False)
            round_trip(original_name="Retime", is_material=False)
            round_trip(original_name="Rounded Square Mask", is_material=False)
            round_trip(original_name="Screen to 3D Space", is_material=False)
            round_trip(original_name="Sensor Noise", is_material=False)
            round_trip(original_name="Separate Cylindrical", is_material=False)
            round_trip(original_name="Separate Spherical", is_material=False)
            round_trip(original_name="Sepia", is_material=False)
            round_trip(original_name="Split Toning", is_material=False)
            round_trip(original_name="Transform and Project", is_material=False)
            round_trip(original_name="Tune Image", is_material=False)
            round_trip(original_name="Unsharp Mask", is_material=False)
            round_trip(original_name="Vignette", is_material=False)

        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_compositing_nodes_essentials.__name__}")
            raise

    def test_geometry_nodes_essentials():
        try:
            bpy.ops.wm.open_mainfile(
                filepath=str(NODE_ASSETS_DIR / "geometry_nodes_essentials.blend")
            )

            round_trip(original_name="Array", is_material=False)
            round_trip(original_name="Capture Rest Geometry", is_material=False)
            round_trip(original_name="Curve to Tube", is_material=False)
            round_trip(original_name="Geometry Input", is_material=False)
            round_trip(original_name="Instance on Elements", is_material=False)
            round_trip(original_name="Randomize Transforms", is_material=False)
            round_trip(original_name="Scatter on Surface", is_material=False)
            round_trip(original_name="Smooth by Angle", is_material=False)

        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_geometry_nodes_essentials.__name__}")
            raise

    # TODO:
    # def test_shading_nodes_essentials:
