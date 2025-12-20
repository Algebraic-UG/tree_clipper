import bpy

from typing import Type

from .util import make_test_node_tree, save_failed, round_trip

_PAIRED_NODE_TYPES = {
    bpy.types.GeometryNodeForeachGeometryElementInput: bpy.types.GeometryNodeForeachGeometryElementOutput,
    bpy.types.GeometryNodeRepeatInput: bpy.types.GeometryNodeRepeatOutput,
    bpy.types.GeometryNodeSimulationInput: bpy.types.GeometryNodeSimulationOutput,
    bpy.types.NodeClosureInput: bpy.types.NodeClosureOutput,
}


def test_all_nodes(node_type: Type[bpy.types.Node]):
    try:
        # these can't be instantiated
        if node_type in [
            bpy.types.NodeGroup,
            bpy.types.NodeCustomGroup,
            bpy.types.GeometryNodeCustomGroup,
            bpy.types.ShaderNodeCustomGroup,
            bpy.types.CompositorNodeCustomGroup,
            # TODO: this might be a left-over, i.e. something to fix in Blender
            bpy.types.TextureNodeCompose,
            bpy.types.TextureNodeDecompose,
            # TODO: there is a "Gamma" node in the compositor, but it's the "shader version"
            bpy.types.CompositorNodeGamma,
        ]:
            return
        # skip the output types of the pairs
        if node_type in _PAIRED_NODE_TYPES.values():
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

        # these need to be tested in combination with the outputs
        if node_type in _PAIRED_NODE_TYPES.keys():
            output_type = _PAIRED_NODE_TYPES[node_type]
            output_node = tree.nodes.new(type=output_type.bl_rna.identifier)  # ty: ignore[possibly-missing-attribute]
            tree.nodes[0].pair_with_output(output_node)  # ty: ignore[unresolved-attribute]

        round_trip(original_name=tree.name, is_material=False)
    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_all_nodes.__name__}_{node_type_str}")
        raise
