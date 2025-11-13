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
    IS_MATERIAL,
    TOP_LEVEL_NAME,
    NODES_AS_JSON_VERSION,
    REFERENCE,
    REFERENCES,
    ROOT,
    SUB_TREES,
    TO_NODE,
    TO_SOCKET,
    USE_MULTI_INPUT,
)


def _check_version(d):
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


def import_nodes(overwrite: bool, input_file: str, allow_version_mismatch=False):
    with Path(input_file).open("r", encoding="utf-8") as f:
        d = json.load(f)

    version_mismatch = _check_version(d)
    if version_mismatch is not None:
        if allow_version_mismatch:
            print(version_mismatch, file=sys.stderr)
        else:
            raise RuntimeError(version_mismatch)

    if d[IS_MATERIAL]:
        if overwrite:
            mat = bpy.data.materials[d[TOP_LEVEL_NAME]]
        else:
            mat = bpy.data.materials.new(name=d[TOP_LEVEL_NAME])
            mat.use_nodes = True
        root = mat.node_tree
    else:
        if overwrite:
            root = bpy.data.node_groups[d[TOP_LEVEL_NAME]]
        else:
            root = bpy.data.node_groups.new(type=d[ROOT]["type"], name=d["name"])

    for node in root.nodes:
        root.nodes.remove(node)
