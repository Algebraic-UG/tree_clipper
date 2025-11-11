import bpy

import json
from pathlib import Path

from .common import COPY_MEMBERS_NODE, COPY_MEMBERS_NODE_TREE


def export_node(node: bpy.types.Node):
    d = {}

    for m in COPY_MEMBERS_NODE:
        d[m] = getattr(node, m)

    # TODO
    color = {}
    location = ()
    location_absolute = ()
    parent = "TODO"

    d["color"] = color
    d["location"] = color
    d["location_absolute"] = location_absolute
    d["parent"] = parent

    return d


def export_node_tree(node_tree: bpy.types.NodeTree):
    d = {}

    for m in COPY_MEMBERS_NODE_TREE:
        # different types of tree have different attributes
        if hasattr(node_tree, m):
            d[m] = getattr(node_tree, m)

    # Skip: animation_data, annotation
    # TODO: grease_pencil

    # TODO
    interface = {}
    links = []
    nodes = [export_node(node) for node in node_tree.nodes]

    d["interface"] = interface
    d["links"] = links
    d["nodes"] = nodes

    return d


def export_nodes(self, _context):

    if self.material:
        root = bpy.data.materials[self.name].node_tree
    else:
        root = bpy.data.node_groups[self.name]

    d = {
        "material": self.material,
        "name": self.name,
        "root": export_node_tree(root),
    }

    with Path(self.output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))

    return {"FINISHED"}
