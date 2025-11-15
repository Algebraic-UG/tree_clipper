from typing import Callable, Self
import bpy


import uuid as uuid_gen
from functools import wraps
import tomllib
import json
from pathlib import Path

from .common import (
    IN_OUT,
    INPUTS,
    INTERFACE_ITEMS,
    INTERFACE_ITEMS_ACTIVE,
    INTERFACE_ITEMS_TREE,
    INTERFACE_SOCKET_TYPE,
    MATERIAL_NAME,
    NODE_TREE_INTERFACE,
    NODE_TREE_LINKS,
    NODE_TREE_NODES,
    NODE_TREE_TYPE,
    NODE_TYPE,
    OUTPUTS,
    PROPERTY_TYPES_SIMPLE,
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


class FromRoot:
    def __init__(self, path: list):
        self.path = path

    def add(self, piece: str):
        return FromRoot(self.path + [piece])

    def to_str(self):
        return str(" -> ".join(self.path))


class Pointer:
    def __init__(
        self,
        *,
        from_root: FromRoot,
        in_serialization: dict,
        points_to: bpy.types.bpy_struct,
    ):
        self.from_root = from_root
        self.in_serialization = in_serialization
        self.points_to = points_to


class Exporter:
    def __init__(
        self,
        *,
        special_handlers: dict,
        skip_defaults: bool,
        debug_prints: bool,
    ):
        self.special_handlers = special_handlers
        self.skip_defaults = (skip_defaults,)
        self.debug_prints = debug_prints
        self.pointers = []
        self.serialized = {}
        self.current_tree = None

    def export_property_simple(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        assert prop.type in PROPERTY_TYPES_SIMPLE

        attribute = getattr(obj, prop.identifier)

        if prop.type in ["BOOLEAN", "INT", "FLOAT"]:
            if prop.is_array:
                if self.skip_defaults and prop.default_array == attribute:
                    return None
                return list(attribute)
        else:
            if self.skip_defaults and prop.default == attribute:
                return None
            return attribute

    def export_property_pointer(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.PointerProperty,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        assert prop.type == "POINTER"
        attribute = getattr(obj, prop.identifier)

        if attribute is None:
            return None

        if attribute.id_data == self.current_tree:
            return self._export_obj(attribute, from_root)
        else:
            d = {}
            self.pointers.append(
                Pointer(
                    from_root=from_root,
                    in_serialization=d,
                    points_to=attribute,
                )
            )
            return d

    def export_property_collection(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.CollectionProperty,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        assert prop.type == "COLLECTION"
        attribute = getattr(obj, prop.identifier)

        return [
            self._export_obj(element, from_root.add(f"[{i}]"))
            for i, element in enumerate(attribute)
        ]

    def _export_obj_with_serializer(
        self,
        obj: bpy.types.bpy_struct,
        serializer: Callable[[Self, bpy.types.bpy_struct, FromRoot], dict],
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        if obj.as_pointer() in self.serialized:
            raise RuntimeError(f"Double serialization: {from_root.to_str()}")

        d = serializer(self, obj, from_root)
        self.serialized[obj.as_pointer()] = d
        return d

    def _export_obj(self, obj: bpy.types.bpy_struct, from_root: FromRoot):
        return self._export_obj_with_serializer(
            obj,
            self.special_handlers.get(obj.bl_rna.identifier, _default_obj_serializer),
            from_root,
        )

    def export_node_tree(self, node_tree: bpy.types.NodeTree, from_root: FromRoot):
        if self.debug_prints:
            print(from_root.to_str())

        self.current_tree = node_tree
        d = self._export_obj(node_tree, from_root)
        self.current_tree = None

        return d


def _collect_sub_trees(
    node_tree: bpy.types.NodeTree,
    tree_names_and_paths: list,
    from_root: FromRoot,
):
    for node in node_tree.nodes:
        if hasattr(node, "node_tree"):
            if all(
                tree_name != node.node_tree.name
                for (tree_name, _) in tree_names_and_paths
            ):
                sub_root = from_root.add("Group ({node.name})")
                tree_names_and_paths.append((node.node_tree.name, sub_root))
                _collect_sub_trees(
                    node.node_tree,
                    tree_names_and_paths,
                    sub_root,
                )


def _default_obj_serializer(exporter: Exporter, obj: bpy.types.bpy_struct, from_root):
    def error_out(reason: str, prop_from_root: FromRoot):
        raise RuntimeError(
            f"""\
Special handler needed for type: {type(obj)}
Reason: {reason}
From root: {prop_from_root.to_str()}"""
        )

    id_properties = set(p.identifier for p in bpy.types.ID.bl_rna.properties)

    d = {}
    for prop in obj.bl_rna.properties:
        prop_from_root = from_root.add(f"{prop.type} ({prop.name})")

        if prop.type in PROPERTY_TYPES_SIMPLE:
            if prop.is_readonly:
                continue
            d_prop = exporter.export_property_simple(obj, prop, prop_from_root)
            if d_prop is not None:
                d[prop.identifier] = d_prop
            continue

        if prop.identifier in id_properties:
            continue

        attribute = getattr(obj, prop.identifier)
        if attribute is None:
            continue

        if prop.type == "POINTER":
            if prop.is_readonly and attribute.id_data != exporter.current_tree:
                error_out("readonly pointer to external", prop_from_root)
            d_prop = exporter.export_property_pointer(obj, prop, prop_from_root)
            if d_prop is not None:
                d[prop.identifier] = d_prop
            continue

        if prop.type == "COLLECTION":
            if hasattr(attribute, "bl_rna"):
                if any(len(f.parameters) != 0 for f in attribute.bl_rna.functions):
                    error_out(
                        "collection with function that requires args", prop_from_root
                    )
            d[prop.identifier] = exporter.export_property_collection(
                obj, prop, prop_from_root
            )

        raise RuntimeError(f"Unknown property type: {prop.type}")

    return d


def export_nodes(
    *,
    is_material: bool,
    name: str,
    output_file: str,
    special_handlers: dict = {},
    export_sub_trees: bool = True,
    skip_defaults: bool = True,
):
    exporter = Exporter(
        special_handlers=special_handlers,
        skip_defaults=skip_defaults,
        debug_prints=True,
    )

    if is_material:
        from_root = FromRoot([f"Material ({name})"])
        root = bpy.data.materials[name].node_tree
    else:
        from_root = FromRoot([f"Root ({name})"])
        root = bpy.data.node_groups[name]

    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        blender_manifest = tomllib.load(f)

    d = {
        BLENDER_VERSION: bpy.app.version_string,
        NODES_AS_JSON_VERSION: blender_manifest["version"],
        ROOT: exporter.export_node_tree(root, from_root),
    }

    if is_material:
        d[MATERIAL_NAME] = name

    if export_sub_trees:
        tree_names_and_paths = []
        _collect_sub_trees(root, tree_names_and_paths, from_root)
        d[SUB_TREES] = [
            exporter.export_node_tree(bpy.data.node_groups[tree_name], sub_root)
            for (tree_name, sub_root) in tree_names_and_paths
        ]

    with Path(output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))


def _no_clobber(d: dict, key: str, value):
    if key in d:
        raise RuntimeError(f"Clobbering '{key}'")
    d[key] = value


#    # we often only need the default_value, which is a writable property
#    def _export_node_socket(self, socket: bpy.types.NodeSocket, from_root: FromRoot):
#        if self.debug_prints:
#            print(from_root.to_str())
#
#        d = self._export_all_writable_properties(socket, path=path)
#
#        # not sure when one has to add sockets, but the following would be needed
#        # name is writable, so we already have it
#
#        # will be used as 'type' arg in 'new'
#        _no_clobber(d, SOCKET_TYPE, socket.bl_rna.identifier)
#        _no_clobber(d, SOCKET_IDENTIFIER, socket.identifier)
#        # this technically only needed for inputs
#        _no_clobber(d, USE_MULTI_INPUT, socket.is_multi_input)
#
#        return d
#
#    @_debug_print()
#    def _export_node_link(self, link: bpy.types.NodeLink, *, path):
#        d = self._export_all_writable_properties(link, path=path)
#
#        _no_clobber(d, FROM_NODE, link.from_node.name)
#        _no_clobber(d, FROM_SOCKET, link.from_socket.identifier)
#        _no_clobber(d, TO_NODE, link.to_node.name)
#        _no_clobber(d, TO_SOCKET, link.to_socket.identifier)
#
#        return d
#
#    @_debug_print()
#    def _export_node(self, node: bpy.types.Node, *, path: list):
#        d = self._export_all_writable_properties(
#            node, path=path
#        ) | self._export_specific_readonly_properties(node, path=path)
#
#        # will be used as 'type' arg in 'new'
#        _no_clobber(d, NODE_TYPE, node.bl_rna.identifier)
#
#        inputs = [
#            self._export_node_socket(socket, path=path + [f"Input ({socket.name})"])
#            for socket in node.inputs
#        ]
#        _no_clobber(d, INPUTS, inputs)
#        outputs = [
#            self._export_node_socket(socket, path=path + [f"Output ({socket.name})"])
#            for socket in node.outputs
#        ]
#        _no_clobber(d, OUTPUTS, outputs)
#
#        return d
#
#    @_debug_print()
#    def _export_interface_tree_socket(
#        self,
#        socket: bpy.types.NodeTreeInterfaceSocket,
#        *,
#        path: list,
#    ):
#        d = self._export_all_writable_properties(socket, path=path)
#
#        # will be used as 'socket_type' arg in 'new_socket'
#        _no_clobber(d, INTERFACE_SOCKET_TYPE, socket.socket_type)
#        _no_clobber(d, IN_OUT, socket.in_out)
#
#        return d
#
#    @_debug_print()
#    def _export_interface_tree_panel(
#        self,
#        panel: bpy.types.NodeTreeInterfacePanel,
#        *,
#        path: list,
#    ):
#        d = self._export_all_writable_properties(panel, path=path)
#        items = [
#            self._export_interface_item(item, path=path)
#            for item in panel.interface_items
#        ]
#        _no_clobber(d, INTERFACE_ITEMS, items)
#        return d
#
#    def _export_interface_item(
#        self,
#        item: bpy.types.NodeTreeInterfaceItem,
#        *,
#        path: list,
#    ):
#        if item.item_type == "SOCKET":
#            return self._export_interface_tree_socket(
#                item,
#                path=path + [f"{item.in_out} Socket ({item.name})"],
#            )
#        elif item.item_type == "PANEL":
#            return self._export_interface_tree_panel(
#                item,
#                path=path + [f"Panel ({item.name})"],
#            )
#        else:
#            raise RuntimeError(f"Unknown item type: {item.item_type}")
#
#    @_debug_print()
#    def _export_interface(self, interface: bpy.types.NodeTreeInterface, *, path):
#        d = self._export_all_writable_properties(interface, path=path)
#
#        items = [
#            self._export_interface_item(item, path=path)
#            for item in interface.items_tree
#        ]
#        _no_clobber(d, INTERFACE_ITEMS_TREE, items)
#        _no_clobber(d, INTERFACE_ITEMS_ACTIVE, interface.active_index)
#
#        return d
#
#    @_debug_print()
#    def export_node_tree(self, node_tree: bpy.types.NodeTree, *, path: list):
#        self.current_tree = node_tree
#
#        # pylint: disable=missing-function-docstring
#        d = self._export_all_writable_properties(node_tree, path=path)
#
#        # name is writable, so we already have it
#
#        # will be used as 'type' arg in 'new'
#        _no_clobber(d, NODE_TREE_TYPE, node_tree.bl_rna.identifier)
#
#        interface = self._export_interface(node_tree.interface, path=path)
#        _no_clobber(d, NODE_TREE_INTERFACE, interface)
#
#        nodes = [
#            self._export_node(node, path=path + [f"Node ({node.name})"])
#            for node in node_tree.nodes
#        ]
#        _no_clobber(d, NODE_TREE_NODES, nodes)
#
#        links = [
#            self._export_node_link(
#                link,
#                path=path
#                + [
#                    f"Link (from {link.from_node.name}, {link.from_socket.name} to {link.to_node.name}, {link.to_socket.name})"
#                ],
#            )
#            for link in node_tree.links
#        ]
#        _no_clobber(d, NODE_TREE_LINKS, links)
#
#        self.current_tree = None
#        return d
#
