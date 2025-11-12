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

    # this will be useful for setting the defaults
    d["identifier"] = socket.identifier

    # only needed for recreating the socket, possibly useful in custom nodes?
    d["use_multi_input"] = socket.is_multi_input

    # all of these can just be stored in JSON
    if socket.type in [
        "VALUE",
        "INT",
        "BOOLEAN",
        "STRING",
        "MENU",  # this also ends up being a string
    ]:
        d["default_value"] = socket.default_value

    # both of these work by with a 3-float-array
    if socket.type in [
        "VECTOR",
        "ROTATION",  # always XYZ ordering
    ]:
        d["default_value"] = [
            socket.default_value[0],
            socket.default_value[1],
            socket.default_value[2],
        ]

    # here it's 4 floats
    if socket.type == "RGBA":
        d["default_value"] = [
            socket.default_value[0],
            socket.default_value[1],
            socket.default_value[2],
            socket.default_value[3],
        ]

    # best we can do here is record the name?
    if socket.type in [
        "OBJECT",
        "MATERIAL",
        "TEXTURE",
        "IMAGE",
        "COLLECTION",
    ]:
        d["default_value"] = (
            None if socket.default_value is None else socket.default_value.name
        )

    # seems (currently) not possible to set a default value
    if socket.type in [
        "MATRIX",
        "SHADER",
        "BUNDLE",
        "CLOSURE",
        "GEOMETRY",
    ]:
        pass

    # the group input has virtual sockets that fall into here
    if socket.type == "CUSTOM":
        pass

    return d


def export_node_link(link: bpy.types.NodeLink):
    d = {}

    for m in COPY_MEMBERS_NODE_LINK:
        d[m] = getattr(link, m)

    # link in second pass
    d["from_node"] = link.from_node.name
    d["from_socket"] = link.from_socket.identifier
    d["to_node"] = link.to_node.name
    d["to_socket"] = link.to_socket.identifier

    return d


def export_node(node: bpy.types.Node):
    d = {}

    for m in COPY_MEMBERS_NODE:
        d[m] = getattr(node, m)

    # these are just a bit special
    d["color"] = [node.color.r, node.color.g, node.color.b]
    d["location"] = [node.location.x, node.location.y]
    d["location_absolute"] = [node.location_absolute.x, node.location_absolute.y]

    # use this in the second pass
    d["parent"] = None if node.parent is None else node.parent.name

    d["inputs"] = [export_node_socket(socket) for socket in node.inputs]
    d["outputs"] = [export_node_socket(socket) for socket in node.outputs]

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
    d["interface"] = {}
    d["links"] = [export_node_link(link) for link in node_tree.links]
    d["nodes"] = [export_node(node) for node in node_tree.nodes]

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
