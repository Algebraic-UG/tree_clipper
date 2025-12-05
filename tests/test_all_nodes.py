import bpy

from typing import Type

from .util import make_test_node_tree, round_trip_without_external


def test_all_nodes(node_type: Type[bpy.types.Node]):
    try:
        # these can't be instantiated
        if node_type == bpy.types.GeometryNodeCustomGroup:
            return

        node_type_str: str = node_type.bl_rna.identifier  # ty: ignore[unresolved-attribute]

        if issubclass(node_type, bpy.types.CompositorNode):
            tree = make_test_node_tree(name=node_type_str, ty="CompositorNodeTree")
        elif issubclass(node_type, bpy.types.ShaderNode):
            tree = make_test_node_tree(name=node_type_str, ty="ShaderNodeTree")
        elif issubclass(node_type, bpy.types.TextureNode):
            tree = make_test_node_tree(name=node_type_str, ty="TextureNodeTree")
        else:  # other types should be available in the geometry node tree
            tree = make_test_node_tree(name=node_type_str, ty="GeometryNodeTree")

        tree.nodes.new(type=node_type_str)

        round_trip_without_external(tree.name)
    except:
        # store in case of failure for easy debugging
        bpy.ops.wm.save_as_mainfile(
            filepath=f"{test_all_nodes.__name__}_{node_type_str}.blend"
        )
        raise
