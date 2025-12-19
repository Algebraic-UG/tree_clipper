import bpy
from .util import round_trip_without_external, make_test_node_tree, save_failed


# https://github.com/Algebraic-UG/tree_clipper/issues/80
def test_multi_input_order():
    try:
        tree = make_test_node_tree()
        assert isinstance(tree.interface, bpy.types.NodeTreeInterface)

        panel = tree.interface.new_panel(name="test")
        bool_socket = tree.interface.new_socket(
            name="test",
            in_out="INPUT",
            socket_type="NodeSocketBool",
            parent=panel,
        )
        bool_socket.is_panel_toggle = True

        tree.interface.new_socket(
            name="test",
            in_out="OUTPUT",
            socket_type="NodeSocketFloat",
            parent=panel,
        )

        round_trip_without_external(tree.name)
    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_multi_input_order.__name__}")

        raise
