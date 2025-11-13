import bpy

import json
from pathlib import Path


# this handles all the writable properties except for sub trees
def export_property(obj: bpy.types.bpy_struct, prop: bpy.types.Property):

    d = {"type": prop.type}
    attribute = getattr(obj, prop.identifier)

    if prop.type in [
        "BOOLEAN",
        "INT",
        "FLOAT",
    ]:
        if prop.is_array:
            d["attr"] = list(attribute)
        else:
            d["attr"] = attribute

    elif prop.type in [
        "STRING",
        "ENUM",
    ]:
        d["attr"] = attribute

    elif prop.type == "POINTER":
        d["fixed_type"] = None if prop.fixed_type is None else prop.fixed_type.name
        d["attr"] = None if attribute is None else attribute.name

    elif prop.type == "COLLECTION":
        d["fixed_type"] = None if prop.fixed_type is None else prop.fixed_type.name
        d["attr"] = [element.name for element in attribute]

    else:
        raise RuntimeError(f"Unknown type: {prop.type}")

    return d


# we often only need the default_value, which is a property
def export_node_socket(socket: bpy.types.NodeSocket):
    d = {}
    for prop in socket.bl_rna.properties:
        if socket.is_property_readonly(prop.identifier):
            continue
        d[prop.identifier] = export_property(socket, prop)

    # not sure when one has to add sockets, but the following would be needed
    d["bl_idname"] = socket.bl_idname  # will be used as 'type' arg in 'new'
    # d["name"] = socket.name # name is writable, so we already have it
    d["identifier"] = socket.identifier
    d["use_multi_input"] = socket.is_multi_input

    return d


def export_node_link(link: bpy.types.NodeLink):
    d = {}
    for prop in link.bl_rna.properties:
        if link.is_property_readonly(prop.identifier):
            continue
        d[prop.identifier] = export_property(link, prop)

    # link in second pass
    d["from_node"] = link.from_node.name
    d["from_socket"] = link.from_socket.identifier
    d["to_node"] = link.to_node.name
    d["to_socket"] = link.to_socket.identifier

    return d


def export_node(node: bpy.types.Node):
    d = {}
    for prop in node.bl_rna.properties:
        if node.is_property_readonly(prop.identifier):
            continue

        if prop.type == "POINTER" and prop.fixed_type == bpy.types.NodeTree.bl_rna:
            raise RuntimeError("sub trees not implemented yet")

        d[prop.identifier] = export_property(node, prop)

    d["bl_idname"] = node.bl_idname  # will be used as 'type' arg in 'new'

    d["inputs"] = [export_node_socket(socket) for socket in node.inputs]
    d["outputs"] = [export_node_socket(socket) for socket in node.outputs]

    return d


def export_node_tree(node_tree: bpy.types.NodeTree):
    d = {}
    for prop in node_tree.bl_rna.properties:
        if node_tree.is_property_readonly(prop.identifier):
            continue
        d[prop.identifier] = export_property(node_tree, prop)

    # d["name"] = node_tree.name # name is writable, so we already have it
    d["bl_idname"] = node_tree.bl_idname  # will be used as 'type' arg in 'new'

    d["interface"] = {}  # TODO
    d["links"] = [export_node_link(link) for link in node_tree.links]
    d["nodes"] = [export_node(node) for node in node_tree.nodes]

    return d


def export_nodes(is_material: bool, name: str, output_file: str):
    if is_material:
        root = bpy.data.materials[name].node_tree
    else:
        root = bpy.data.node_groups[name]

    d = {
        "is_material": is_material,
        "name": name,
        "root": export_node_tree(root),
    }

    with Path(output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))
