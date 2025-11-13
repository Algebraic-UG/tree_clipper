import bpy

import sys
import tomllib
import json
from pathlib import Path

from .common import (
    IN_OUT,
    INPUTS,
    INTERFACE_ITEMS,
    INTERFACE_ITEMS_TREE,
    INTERFACE_SOCKET_TYPE,
    MATERIAL_NAME,
    NODE_TREE_INTERFACE,
    NODE_TREE_LINKS,
    NODE_TREE_NODES,
    NODE_TREE_TYPE,
    NODE_TYPE,
    OUTPUTS,
    SOCKET_IDENTIFIER,
    SOCKET_TYPE,
    BLENDER_VERSION,
    FIXED_TYPE,
    FROM_NODE,
    FROM_SOCKET,
    NODES_AS_JSON_VERSION,
    REFERENCE,
    REFERENCES,
    ROOT,
    SUB_TREES,
    TO_NODE,
    TO_SOCKET,
    USE_MULTI_INPUT,
)


class _Importer:
    def __init__(self, overwrite: bool):
        self.overwrite = overwrite
        self.created_trees = {}

    def _import_nodes(self, d: dict):
        pass

    def _import_nodes(self, d: dict):
        pass

    def _import_nodes(self, d: dict):
        pass

    def import_node_tree(self, d: dict, material_name: str = None):
        if material_name is None:
            if self.overwrite and d["name"] in bpy.data.node_groups:
                node_tree = bpy.data.node_groups[d["name"]]
            else:
                node_tree = bpy.data.node_groups.new(
                    type=d[NODE_TREE_TYPE],
                    name=d["name"],
                )
        else:
            # this can only happen for the top level
            if self.overwrite:
                mat = bpy.data.materials[material_name]
            else:
                mat = bpy.data.materials.new(material_name)
            mat.use_nodes = True
            node_tree = mat.node_tree

        # if not overriding, the name might be different
        self.created_trees[d["name"]] = node_tree.name

        node_tree.nodes.clear()


def _check_version(d: dict):
    exporter_blender_version = d[BLENDER_VERSION]
    importer_blender_version = bpy.app.version_string
    if exporter_blender_version != importer_blender_version:
        return f"Blender version mismatch. File version: {exporter_blender_version}, but running {importer_blender_version}"

    exporter_node_as_json_version = d[NODES_AS_JSON_VERSION]
    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        blender_manifest = tomllib.load(f)
    importer_node_as_json_version = blender_manifest["version"]
    name = blender_manifest["name"]

    if exporter_node_as_json_version != importer_node_as_json_version:
        return f"{name} version mismatch. File version: {exporter_node_as_json_version}, but running {importer_node_as_json_version}"


def import_nodes(input_file: str, allow_version_mismatch=False, overwrite=False):
    importer = _Importer(overwrite)

    with Path(input_file).open("r", encoding="utf-8") as f:
        d = json.load(f)

    version_mismatch = _check_version(d)
    if version_mismatch is not None:
        if allow_version_mismatch:
            print(version_mismatch, file=sys.stderr)
        else:
            raise RuntimeError(version_mismatch)

    # important to construct in reverse order
    if SUB_TREES in d:
        for sub_tree in reversed(d[SUB_TREES]):
            importer.import_node_tree(sub_tree)

    importer.import_node_tree(d[ROOT], d.get(MATERIAL_NAME))
