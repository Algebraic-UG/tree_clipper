import bpy

from typing import Type

from .util import make_test_node_tree, round_trip_without_external


def test_all_nodes(node_type: Type[bpy.types.Node]):
    try:
        node_type_str: str = node_type.bl_rna.identifier  # ty: ignore[unresolved-attribute]

        tree = make_test_node_tree(node_type_str)

        tree.nodes.new(type=node_type_str)

        round_trip_without_external(tree.name)
    except:
        # store in case of failure for easy debugging
        bpy.ops.wm.save_as_mainfile(
            filepath=f"{test_all_nodes.__name__}_{node_type_str}.blend"
        )
        raise
