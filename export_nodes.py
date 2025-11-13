import bpy

import json
from pathlib import Path


# this handles all the writable properties except for sub trees
def export_property(obj: bpy.types.bpy_struct, prop: bpy.types.Property):
    attribute = getattr(obj, prop.identifier)

    if prop.type in ["BOOLEAN", "INT", "FLOAT"]:
        return list(attribute) if prop.is_array else attribute

    elif prop.type in ["STRING", "ENUM"]:
        return attribute

    d = {
        "type": prop.type,
        "fixed_type": None if prop.fixed_type is None else prop.fixed_type.name,
    }

    if prop.type == "POINTER":
        d["name"] = None if attribute is None else attribute.name
    elif prop.type == "COLLECTION":
        d["names"] = [element.name for element in attribute]
    else:
        raise RuntimeError(f"Unknown property type: {prop.type}")

    return d


def export_all_writable_properties(obj: bpy.types.bpy_struct):
    d = {}
    for prop in obj.bl_rna.properties:
        if obj.is_property_readonly(prop.identifier):
            continue
        d[prop.identifier] = export_property(obj, prop)
    return d


# we often only need the default_value, which is a property
def export_node_socket(socket: bpy.types.NodeSocket):
    d = export_all_writable_properties(socket)

    # not sure when one has to add sockets, but the following would be needed
    d["bl_idname"] = socket.bl_idname  # will be used as 'type' arg in 'new'
    # d["name"] = socket.name # name is writable, so we already have it
    d["identifier"] = socket.identifier
    d["use_multi_input"] = socket.is_multi_input

    return d


def export_node_link(link: bpy.types.NodeLink):
    d = export_all_writable_properties(link)

    # link in second pass
    d["from_node"] = link.from_node.name
    d["from_socket"] = link.from_socket.identifier
    d["to_node"] = link.to_node.name
    d["to_socket"] = link.to_socket.identifier

    return d


def export_node(node: bpy.types.Node):
    d = export_all_writable_properties(node)

    d["bl_idname"] = node.bl_idname  # will be used as 'type' arg in 'new'

    d["inputs"] = [export_node_socket(socket) for socket in node.inputs]
    d["outputs"] = [export_node_socket(socket) for socket in node.outputs]

    return d


def export_interface_tree_socket(socket: bpy.types.NodeTreeInterfaceSocket):
    d = export_all_writable_properties(socket)
    d["bl_socket_idname"] = (
        socket.bl_socket_idname
    )  # will be used as 'socket_type' arg in 'new_socket'
    d["in_out"] = socket.in_out
    return d


def export_interface_tree_panel(panel: bpy.types.NodeTreeInterfacePanel):
    d = export_all_writable_properties(panel)
    d["iterface_items"] = [
        export_interface_item(item) for item in panel.interface_items
    ]
    return d


def export_interface_item(item: bpy.types.NodeTreeInterfaceItem):
    if item.item_type == "SOCKET":
        return export_interface_tree_socket(item)
    elif item.item_type == "PANEL":
        return export_interface_tree_panel(item)
    else:
        raise RuntimeError(f"Unknown item type: {item.item_type}")


def export_interface(interface: bpy.types.NodeTreeInterface):
    d = export_all_writable_properties(interface)

    d["items_tree"] = [export_interface_item(item) for item in interface.items_tree]

    return d


def export_node_tree(node_tree: bpy.types.NodeTree):
    d = export_all_writable_properties(node_tree)

    # d["name"] = node_tree.name # name is writable, so we already have it
    d["bl_idname"] = node_tree.bl_idname  # will be used as 'type' arg in 'new'

    d["interface"] = export_interface(node_tree.interface)
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
