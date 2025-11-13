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
    FROM_NODE,
    FROM_SOCKET,
    NODES_AS_JSON_VERSION,
    ROOT,
    SUB_TREES,
    TO_NODE,
    TO_SOCKET,
    USE_MULTI_INPUT,
)


def _is_built_in(obj):
    return getattr(obj, "__module__", "").startswith("bpy.types")


def no_clobber(d: dict, key: str, value):
    if key in d:
        raise RuntimeError(f"Clobbering '{key}'")
    d[key] = value


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

        # hmm, kinda tricky, `path_from_module` appears to contain enough info
        if prop.type == "POINTER":
            if attribute is None:
                return None
            return attribute.path_from_module()

        # is there even a use case for this at the moment?
        if prop.type == "COLLECTION":
            raise RuntimeError(
                "You have a use case for collection properties in nodes? Please tell use about this:\nhttps://github.com/Algebraic-UG/nodes_as_json/issues/new"
            )

        raise RuntimeError(f"Unknown property type: {prop.type}")

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
        # name is writable, so we already have it

        # will be used as 'type' arg in 'new'
        no_clobber(d, SOCKET_TYPE, socket.rna_type.identifier)
        no_clobber(d, SOCKET_IDENTIFIER, socket.identifier)
        # this technically only needed for inputs
        no_clobber(d, USE_MULTI_INPUT, socket.is_multi_input)

        return d

    def _export_node_link(self, link: bpy.types.NodeLink):
        d = self._export_all_writable_properties(link)

        no_clobber(d, FROM_NODE, link.from_node.name)
        no_clobber(d, FROM_SOCKET, link.from_socket.identifier)
        no_clobber(d, TO_NODE, link.to_node.name)
        no_clobber(d, TO_SOCKET, link.to_socket.identifier)

        return d

    def _export_node(self, node: bpy.types.Node):
        d = self._export_all_writable_properties(node)

        # will be used as 'type' arg in 'new'
        no_clobber(d, NODE_TYPE, node.rna_type.identifier)

        no_clobber(
            d,
            INPUTS,
            [self._export_node_socket(socket) for socket in node.inputs],
        )
        no_clobber(
            d,
            OUTPUTS,
            [self._export_node_socket(socket) for socket in node.outputs],
        )

        return d

    def _export_interface_tree_socket(self, socket: bpy.types.NodeTreeInterfaceSocket):
        d = self._export_all_writable_properties(socket)

        # will be used as 'socket_type' arg in 'new_socket'
        no_clobber(d, INTERFACE_SOCKET_TYPE, socket.socket_type)
        no_clobber(d, IN_OUT, socket.in_out)

        return d

    def _export_interface_tree_panel(self, panel: bpy.types.NodeTreeInterfacePanel):
        d = self._export_all_writable_properties(panel)
        no_clobber(
            d,
            INTERFACE_ITEMS,
            [self._export_interface_item(item) for item in panel.interface_items],
        )
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

        no_clobber(
            d,
            INTERFACE_ITEMS_TREE,
            [self._export_interface_item(item) for item in interface.items_tree],
        )

        return d

    def export_node_tree(self, node_tree: bpy.types.NodeTree):
        # pylint: disable=missing-function-docstring

        d = self._export_all_writable_properties(node_tree)

        # name is writable, so we already have it

        # will be used as 'type' arg in 'new'
        no_clobber(d, NODE_TREE_TYPE, node_tree.rna_type.identifier)

        no_clobber(d, NODE_TREE_INTERFACE, self._export_interface(node_tree.interface))
        no_clobber(
            d,
            NODE_TREE_LINKS,
            [self._export_node_link(link) for link in node_tree.links],
        )
        no_clobber(
            d,
            NODE_TREE_NODES,
            [self._export_node(node) for node in node_tree.nodes],
        )

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
