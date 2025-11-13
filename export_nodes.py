import bpy

import json
from pathlib import Path


def _is_built_in(obj):
    return getattr(obj, "__module__", "").startswith("bpy.types")


class Exporter:
    def __init__(self, export_sub_groups=True, skip_built_in_defaults=True):
        self.export_sub_groups = export_sub_groups
        self.skip_built_in_defaults = skip_built_in_defaults

    def export_property(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
    ):
        skip_defaults = self.skip_built_in_defaults and _is_built_in(obj)

        attribute = getattr(obj, prop.identifier)

        if prop.type in ["BOOLEAN", "INT", "FLOAT"]:
            if prop.is_array:
                if skip_defaults and prop.default_array == attribute:
                    return None
                return list(attribute)
            else:
                if skip_defaults and prop.default == attribute:
                    return None
                return attribute

        if prop.type in ["STRING", "ENUM"]:
            if skip_defaults and prop.default == attribute:
                return None
            return attribute

        d = {
            "fixed_type": None if prop.fixed_type is None else prop.fixed_type.name,
        }

        if prop.type == "POINTER":
            if skip_defaults and attribute is None:
                return None
            d["name"] = None if attribute is None else attribute.name
        elif prop.type == "COLLECTION":
            if skip_defaults and len(attribute) == 0:
                return None
            d["names"] = [element.name for element in attribute]
        else:
            raise RuntimeError(f"Unknown property type: {prop.type}")

        return d

    def export_all_writable_properties(self, obj: bpy.types.bpy_struct):
        d = {}
        for prop in obj.bl_rna.properties:
            if obj.is_property_readonly(prop.identifier):
                continue
            exported_prop = self.export_property(obj, prop)
            if exported_prop is not None:
                d[prop.identifier] = exported_prop
        return d

    # we often only need the default_value, which is a writable property
    def export_node_socket(self, socket: bpy.types.NodeSocket):
        d = self.export_all_writable_properties(socket)

        # not sure when one has to add sockets, but the following would be needed
        d["bl_idname"] = socket.bl_idname  # will be used as 'type' arg in 'new'
        # d["name"] = socket.name # name is writable, so we already have it
        d["identifier"] = socket.identifier
        d["use_multi_input"] = socket.is_multi_input

        return d

    def export_node_link(self, link: bpy.types.NodeLink):
        d = self.export_all_writable_properties(link)

        # link in second pass
        d["from_node"] = link.from_node.name
        d["from_socket"] = link.from_socket.identifier
        d["to_node"] = link.to_node.name
        d["to_socket"] = link.to_socket.identifier

        return d

    def export_node(self, node: bpy.types.Node):
        d = self.export_all_writable_properties(node)

        d["bl_idname"] = node.bl_idname  # will be used as 'type' arg in 'new'

        d["inputs"] = [self.export_node_socket(socket) for socket in node.inputs]
        d["outputs"] = [self.export_node_socket(socket) for socket in node.outputs]

        return d

    def export_interface_tree_socket(self, socket: bpy.types.NodeTreeInterfaceSocket):
        d = self.export_all_writable_properties(socket)
        d["bl_socket_idname"] = (
            socket.bl_socket_idname
        )  # will be used as 'socket_type' arg in 'new_socket'
        d["in_out"] = socket.in_out
        return d

    def export_interface_tree_panel(self, panel: bpy.types.NodeTreeInterfacePanel):
        d = self.export_all_writable_properties(panel)
        d["iterface_items"] = [
            self.export_interface_item(item) for item in panel.interface_items
        ]
        return d

    def export_interface_item(self, item: bpy.types.NodeTreeInterfaceItem):
        if item.item_type == "SOCKET":
            return self.export_interface_tree_socket(item)
        elif item.item_type == "PANEL":
            return self.export_interface_tree_panel(item)
        else:
            raise RuntimeError(f"Unknown item type: {item.item_type}")

    def export_interface(self, interface: bpy.types.NodeTreeInterface):
        d = self.export_all_writable_properties(interface)

        d["items_tree"] = [
            self.export_interface_item(item) for item in interface.items_tree
        ]

        return d

    def export_node_tree(self, node_tree: bpy.types.NodeTree):
        d = self.export_all_writable_properties(node_tree)

        # d["name"] = node_tree.name # name is writable, so we already have it
        d["bl_idname"] = node_tree.bl_idname  # will be used as 'type' arg in 'new'

        d["interface"] = self.export_interface(node_tree.interface)
        d["links"] = [self.export_node_link(link) for link in node_tree.links]
        d["nodes"] = [self.export_node(node) for node in node_tree.nodes]

        return d

    def export_nodes(self, is_material: bool, name: str, output_file: str):
        if is_material:
            root = bpy.data.materials[name].node_tree
        else:
            root = bpy.data.node_groups[name]

        d = {
            "blender_version": bpy.app.version_string,
            "is_material": is_material,
            "name": name,
            "root": self.export_node_tree(root),
        }

        with Path(output_file).open("w", encoding="utf-8") as f:
            f.write(json.dumps(d, indent=4))
