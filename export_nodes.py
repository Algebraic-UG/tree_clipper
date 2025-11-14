import bpy

from functools import wraps
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


def _no_clobber(d: dict, key: str, value):
    if key in d:
        raise RuntimeError(f"Clobbering '{key}'")
    d[key] = value


def _debug_print():
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.debug_prints:
                print(str(" -> ".join(kwargs["path"])))
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


class _Exporter:
    def __init__(self, skip_built_in_defaults: bool, debug_prints=True):
        self.skip_built_in_defaults = skip_built_in_defaults
        self.debug_prints = debug_prints
        self.pointer_to_external = []

    @_debug_print()
    def _export_property(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        *,
        path: list,
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
            self.pointer_to_external.append(
                (obj.path_from_module(prop.identifier), attribute.path_from_module())
            )

            return attribute.path_from_module()

        # is there even a use case for this at the moment?
        if prop.type == "COLLECTION":
            raise RuntimeError(
                "You have a use case for collection properties in nodes? Please tell use about this:\nhttps://github.com/Algebraic-UG/nodes_as_json/issues/new"
            )

        raise RuntimeError(f"Unknown property type: {prop.type}")

    def _export_all_writable_properties(self, obj: bpy.types.bpy_struct, *, path: list):
        d = {}
        for prop in obj.bl_rna.properties:
            if obj.is_property_readonly(prop.identifier):
                continue
            exported_prop = self._export_property(
                obj,
                prop,
                path=path + [f"{prop.type} ({prop.name})"],
            )
            if exported_prop is not None:
                d[prop.identifier] = exported_prop
        return d

    # we often only need the default_value, which is a writable property
    @_debug_print()
    def _export_node_socket(self, socket: bpy.types.NodeSocket, *, path: list):
        d = self._export_all_writable_properties(socket, path=path)

        # not sure when one has to add sockets, but the following would be needed
        # name is writable, so we already have it

        # will be used as 'type' arg in 'new'
        _no_clobber(d, SOCKET_TYPE, socket.rna_type.identifier)
        _no_clobber(d, SOCKET_IDENTIFIER, socket.identifier)
        # this technically only needed for inputs
        _no_clobber(d, USE_MULTI_INPUT, socket.is_multi_input)

        return d

    @_debug_print()
    def _export_node_link(self, link: bpy.types.NodeLink, *, path):
        d = self._export_all_writable_properties(link, path=path)

        _no_clobber(d, FROM_NODE, link.from_node.name)
        _no_clobber(d, FROM_SOCKET, link.from_socket.identifier)
        _no_clobber(d, TO_NODE, link.to_node.name)
        _no_clobber(d, TO_SOCKET, link.to_socket.identifier)

        return d

    @_debug_print()
    def _export_node(self, node: bpy.types.Node, *, path: list):
        d = self._export_all_writable_properties(node, path=path)

        # will be used as 'type' arg in 'new'
        _no_clobber(d, NODE_TYPE, node.rna_type.identifier)

        inputs = [
            self._export_node_socket(socket, path=path + [f"Input ({socket.name})"])
            for socket in node.inputs
        ]
        _no_clobber(d, INPUTS, inputs)
        outputs = [
            self._export_node_socket(socket, path=path + [f"Output ({socket.name})"])
            for socket in node.outputs
        ]
        _no_clobber(d, OUTPUTS, outputs)

        return d

    @_debug_print()
    def _export_interface_tree_socket(
        self,
        socket: bpy.types.NodeTreeInterfaceSocket,
        *,
        path: list,
    ):
        d = self._export_all_writable_properties(socket, path=path)

        # will be used as 'socket_type' arg in 'new_socket'
        _no_clobber(d, INTERFACE_SOCKET_TYPE, socket.socket_type)
        _no_clobber(d, IN_OUT, socket.in_out)

        return d

    @_debug_print()
    def _export_interface_tree_panel(
        self,
        panel: bpy.types.NodeTreeInterfacePanel,
        *,
        path: list,
    ):
        d = self._export_all_writable_properties(panel, path=path)
        items = [
            self._export_interface_item(item, path=path)
            for item in panel.interface_items
        ]
        _no_clobber(d, INTERFACE_ITEMS, items)
        return d

    def _export_interface_item(
        self,
        item: bpy.types.NodeTreeInterfaceItem,
        *,
        path: list,
    ):
        if item.item_type == "SOCKET":
            return self._export_interface_tree_socket(
                item,
                path=path + [f"Socket ({item.name})"],
            )
        elif item.item_type == "PANEL":
            return self._export_interface_tree_panel(
                item,
                path=path + [f"Panel ({item.name})"],
            )
        else:
            raise RuntimeError(f"Unknown item type: {item.item_type}")

    @_debug_print()
    def _export_interface(self, interface: bpy.types.NodeTreeInterface, *, path):
        d = self._export_all_writable_properties(interface, path=path)

        # TODO: this doesn't work here
        # this is very ugly, but we don't want to store this
        # it is a PointerProperty which we can't recreate easily
        # and it's not that important anyway
        # d.pop("active", None)

        items = [
            self._export_interface_item(item, path=path)
            for item in interface.items_tree
        ]
        _no_clobber(d, INTERFACE_ITEMS_TREE, items)

        return d

    @_debug_print()
    def export_node_tree(self, node_tree: bpy.types.NodeTree, *, path: list):
        # pylint: disable=missing-function-docstring
        d = self._export_all_writable_properties(node_tree, path=path)

        # name is writable, so we already have it

        # will be used as 'type' arg in 'new'
        _no_clobber(d, NODE_TREE_TYPE, node_tree.rna_type.identifier)

        interface = self._export_interface(node_tree.interface, path=path)
        _no_clobber(d, NODE_TREE_INTERFACE, interface)

        nodes = [
            self._export_node(node, path=path + [f"Node ({node.name})"])
            for node in node_tree.nodes
        ]
        _no_clobber(d, NODE_TREE_NODES, nodes)

        links = [
            self._export_node_link(
                link,
                path=path
                + [
                    f"Link (from {link.from_node.name}, {link.from_socket.name} to {link.to_node.name}, {link.to_socket.name})"
                ],
            )
            for link in node_tree.links
        ]
        _no_clobber(d, NODE_TREE_LINKS, links)

        return d


def _collect_sub_trees(
    node_tree: bpy.types.NodeTree, tree_names_and_paths: list, path: list
):
    for node in node_tree.nodes:
        if hasattr(node, "node_tree"):
            if all(
                tree_name != node.node_tree.name
                for (tree_name, _) in tree_names_and_paths
            ):
                subpath = path + [f"Group ({node.name})"]
                tree_names_and_paths.append((node.node_tree.name, subpath))
                _collect_sub_trees(
                    node.node_tree,
                    tree_names_and_paths,
                    subpath,
                )


def export_nodes(
    is_material: bool,
    name: str,
    output_file: str,
    export_sub_trees=True,
    skip_built_in_defaults=True,
):
    exporter = _Exporter(skip_built_in_defaults)

    if is_material:
        path = [f"Material ({name})"]
        root = bpy.data.materials[name].node_tree
    else:
        path = [f"Root Tree ({name})"]
        root = bpy.data.node_groups[name]

    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        blender_manifest = tomllib.load(f)

    d = {
        BLENDER_VERSION: bpy.app.version_string,
        NODES_AS_JSON_VERSION: blender_manifest["version"],
        ROOT: exporter.export_node_tree(root, path=path),
    }

    if is_material:
        d[MATERIAL_NAME] = name

    if export_sub_trees:
        tree_names_and_paths = []
        _collect_sub_trees(root, tree_names_and_paths, path)
        d[SUB_TREES] = [
            exporter.export_node_tree(bpy.data.node_groups[tree_name], path=sub_path)
            for (tree_name, sub_path) in tree_names_and_paths
        ]

    with Path(output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))
