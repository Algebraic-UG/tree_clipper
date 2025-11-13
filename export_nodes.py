import bpy

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


def _is_built_in(obj):
    return getattr(obj, "__module__", "").startswith("bpy.types")


class _Exporter:
    def __init__(self, skip_built_in_defaults: bool):
        self.skip_built_in_defaults = skip_built_in_defaults

    def _export_property(
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
            FIXED_TYPE: None if prop.fixed_type is None else prop.fixed_type.name,
        }

        if prop.type == "POINTER":
            if skip_defaults and attribute is None:
                return None
            d[REFERENCE] = None if attribute is None else attribute.name
        elif prop.type == "COLLECTION":
            if skip_defaults and len(attribute) == 0:
                return None
            d[REFERENCES] = [element.name for element in attribute]
        else:
            raise RuntimeError(f"Unknown property type: {prop.type}")

        return d

    def _export_all_writable_properties(self, obj: bpy.types.bpy_struct):
        d = {}
        for prop in obj.bl_rna.properties:
            if obj.is_property_readonly(prop.identifier):
                continue
            exported_prop = self._export_property(obj, prop)
            if exported_prop is not None:
                d[prop.identifier] = exported_prop
        return d

    # we often only need the default_value, which is a writable property
    def _export_node_socket(self, socket: bpy.types.NodeSocket):
        d = self._export_all_writable_properties(socket)

        # not sure when one has to add sockets, but the following would be needed
        d[SOCKET_TYPE] = socket.bl_idname  # will be used as 'type' arg in 'new'
        # d["name"] = socket.name # name is writable, so we already have it
        d[SOCKET_IDENTIFIER] = socket.identifier
        d[USE_MULTI_INPUT] = socket.is_multi_input

        return d

    def _export_node_link(self, link: bpy.types.NodeLink):
        d = self._export_all_writable_properties(link)

        # link in second pass
        d[FROM_NODE] = link.from_node.name
        d[FROM_SOCKET] = link.from_socket.identifier
        d[TO_NODE] = link.to_node.name
        d[TO_SOCKET] = link.to_socket.identifier

        return d

    def _export_node(self, node: bpy.types.Node):
        d = self._export_all_writable_properties(node)

        d[NODE_TYPE] = node.bl_idname  # will be used as 'type' arg in 'new'

        d[INPUTS] = [self._export_node_socket(socket) for socket in node.inputs]
        d[OUTPUTS] = [self._export_node_socket(socket) for socket in node.outputs]

        return d

    def _export_interface_tree_socket(self, socket: bpy.types.NodeTreeInterfaceSocket):
        d = self._export_all_writable_properties(socket)
        d[INTERFACE_SOCKET_TYPE] = (
            socket.bl_socket_idname
        )  # will be used as 'socket_type' arg in 'new_socket'
        d[IN_OUT] = socket.in_out
        return d

    def _export_interface_tree_panel(self, panel: bpy.types.NodeTreeInterfacePanel):
        d = self._export_all_writable_properties(panel)
        d[INTERFACE_ITEMS] = [
            self._export_interface_item(item) for item in panel.interface_items
        ]
        return d

    def _export_interface_item(self, item: bpy.types.NodeTreeInterfaceItem):
        if item.item_type == "SOCKET":
            return self._export_interface_tree_socket(item)
        elif item.item_type == "PANEL":
            return self._export_interface_tree_panel(item)
        else:
            raise RuntimeError(f"Unknown item type: {item.item_type}")

    def _export_interface(self, interface: bpy.types.NodeTreeInterface):
        d = self._export_all_writable_properties(interface)

        d[INTERFACE_ITEMS_TREE] = [
            self._export_interface_item(item) for item in interface.items_tree
        ]

        return d

    def export_node_tree(self, node_tree: bpy.types.NodeTree):
        # pylint: disable=missing-function-docstring

        d = self._export_all_writable_properties(node_tree)

        # d["name"] = node_tree.name # name is writable, so we already have it
        d[NODE_TREE_TYPE] = node_tree.bl_idname  # will be used as 'type' arg in 'new'

        d[NODE_TREE_INTERFACE] = self._export_interface(node_tree.interface)
        d[NODE_TREE_LINKS] = [self._export_node_link(link) for link in node_tree.links]
        d[NODE_TREE_NODES] = [self._export_node(node) for node in node_tree.nodes]

        return d


def _collect_sub_trees(node_tree: bpy.types.NodeTree, sub_trees: list):
    for node in node_tree.nodes:
        if hasattr(node, "node_tree"):
            if node.node_tree.name not in sub_trees:
                sub_trees.append(node.node_tree.name)
                _collect_sub_trees(node.node_tree, sub_trees)


def export_nodes(
    is_material: bool,
    name: str,
    output_file: str,
    export_sub_trees=True,
    skip_built_in_defaults=True,
):
    exporter = _Exporter(skip_built_in_defaults)

    if is_material:
        root = bpy.data.materials[name].node_tree
    else:
        root = bpy.data.node_groups[name]

    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        blender_manifest = tomllib.load(f)

    d = {
        BLENDER_VERSION: bpy.app.version_string,
        NODES_AS_JSON_VERSION: blender_manifest["version"],
        ROOT: exporter.export_node_tree(root),
    }

    if is_material:
        d[MATERIAL_NAME] = name

    if export_sub_trees:
        sub_trees = []
        _collect_sub_trees(root, sub_trees)
        d[SUB_TREES] = [
            exporter.export_node_tree(bpy.data.node_groups[tree]) for tree in sub_trees
        ]

    with Path(output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))
