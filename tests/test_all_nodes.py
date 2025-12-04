import bpy

from typing import Type


def test_all_nodes(node_type: Type[bpy.types.Node]):
    node_type_str: str = node_type.bl_rna.identifier  # ty: ignore[unresolved-attribute]
    print(f"testing: {node_type_str}")
    assert False
