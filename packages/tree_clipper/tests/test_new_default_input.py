import bpy

from .util import make_test_node_tree, round_trip_without_external, save_failed

if (bpy.app.version[0] == 5 and bpy.app.version[1] >= 2) or bpy.app.version[0] > 5:

    def test_new_default_input():
        try:
            tree = make_test_node_tree()

            socket = tree.interface.new_socket("test")
            socket.default_input = "SCENE_FRAME"

            round_trip_without_external(tree.name)

            assert tree.interface.items_tree[0].default_input == "SCENE_FRAME"

        except:
            # store in case of failure for easy debugging
            save_failed(f"{test_new_default_input.__name__}")

            raise
