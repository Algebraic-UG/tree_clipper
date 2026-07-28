import argparse
from pathlib import Path

import bpy
from tree_clipper.common import NODE_TREE
from tree_clipper.export_nodes import ExportIntermediate, ExportParameters
from tree_clipper.specific_handlers import BUILT_IN_EXPORTER


def _collect_sub_trees(
    current: bpy.types.NodeTree,
    trees: list[bpy.types.NodeTree],
) -> None:
    for node in current.nodes:
        tree = getattr(node, NODE_TREE, None)
        if isinstance(tree, bpy.types.NodeTree):
            if all(tree.name != already_in.name for already_in in trees):
                _collect_sub_trees(current=tree, trees=trees)
    assert all(current.name != already_in.name for already_in in trees)
    trees.append(current)


def get_roots() -> list[tuple[str, bool]]:
    # first collect all trees that we might want to test
    # storing whether they are a material
    trees = [(tree.name, False) for tree in bpy.data.node_groups]
    for material in bpy.data.materials:
        if material.node_tree is None:
            continue
        trees.append((material.name, True))

    # then, remove all the trees that are part of another tree as a node group
    i = 0
    while i < len(trees):
        name, is_material = trees[i]
        if is_material:
            tree = bpy.data.materials[name].node_tree
        else:
            tree = bpy.data.node_groups[name]
        assert isinstance(tree, bpy.types.NodeTree)

        # get the sub trees, those are duplicate
        sub_trees = []
        _collect_sub_trees(tree, sub_trees)

        # the final element is the root
        sub_trees.pop()
        for duplicate in sub_trees:
            trees = [
                (name, is_material)
                for (name, is_material) in trees
                if is_material or duplicate.name != name
            ]

        i += 1

    return trees


parser = argparse.ArgumentParser(prog="Export all roots from blend file to directory.")
parser.add_argument("--filename", required=True)
parser.add_argument("--directory", required=True)
parser.add_argument("--debug_prints")

args = parser.parse_args()

bpy.ops.wm.open_mainfile(filepath=args.filename)
Path(args.directory).mkdir(parents=True, exist_ok=True)

trees = get_roots()
print(trees)

for name, is_material in trees:
    if is_material:
        tree = bpy.data.materials[name].node_tree
    else:
        tree = bpy.data.node_groups[name]
    assert isinstance(tree, bpy.types.NodeTree)

    export_intermediate = ExportIntermediate(
        parameters=ExportParameters(
            is_material=is_material,
            name=name,
            specific_handlers=BUILT_IN_EXPORTER,
            export_sub_trees=True,
            debug_prints=args.debug_prints,
            write_from_roots=False,
        )
    )

    while export_intermediate.step():
        pass

    export_intermediate.set_external(
        (
            external_id,
            external_item.pointed_to_by.get_pointee().name,  # ty: ignore[possibly-missing-attribute]
        )
        for external_id, external_item in export_intermediate.get_external().items()
    )

    type_directory = Path(args.directory) / tree.bl_rna.identifier  # ty:ignore[unresolved-attribute]
    type_directory.mkdir(parents=True, exist_ok=True)
    file_path = type_directory / (name + ".json")

    print(f"exporting {file_path}")
    export_intermediate.export_to_file(
        file_path=file_path,
        compress=False,
        json_indent=4,
    )
