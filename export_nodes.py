import bpy

import json
from pathlib import Path

from .common import (
    COPY_MEMBERS_NODE,
    COPY_MEMBERS_NODE_LINK,
    COPY_MEMBERS_NODE_SOCKET,
    COPY_MEMBERS_NODE_TREE,
)


def export_node_socket(socket: bpy.types.NodeSocket):
    d = {}

    for m in COPY_MEMBERS_NODE_SOCKET:
        d[m] = getattr(socket, m)

    d["identifier"] = socket.identifier
    d["use_multi_input"] = socket.is_multi_input

    return d


def export_node_link(link: bpy.types.NodeLink):
    d = {}

    for m in COPY_MEMBERS_NODE_LINK:
        d[m] = getattr(link, m)

    d["from_node"] = link.from_node.name
    d["from_socket"] = link.from_socket.identifier
    d["to_node"] = link.to_node.name
    d["to_socket"] = link.to_socket.identifier

    return d


def export_node(node: bpy.types.Node):
    d = {}

    for m in COPY_MEMBERS_NODE:
        d[m] = getattr(node, m)

    # TODO
    color = {}
    location = ()
    location_absolute = ()
    parent = "TODO"

    # TODO: is this needed for custom nodes, maybe?
    inputs = [export_node_socket(socket) for socket in node.inputs]
    outputs = [export_node_socket(socket) for socket in node.outputs]

    d["color"] = color
    d["location"] = location
    d["location_absolute"] = location_absolute
    d["parent"] = parent
    d["inputs"] = inputs
    d["outputs"] = outputs

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
    links = [export_node_link(link) for link in node_tree.links]
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
