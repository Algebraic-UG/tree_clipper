import bpy

from typing import Callable, Self

import functools
import sys
import tomllib
import json
from pathlib import Path

from .common import (
    ID,
    IN_OUT,
    INPUTS,
    INTERFACE_ITEMS,
    INTERFACE_ITEMS_TREE,
    MATERIAL_NAME,
    NODE_TREE_INTERFACE,
    NODE_TREE_LINKS,
    NODE_TREE_NODES,
    NODE_TREE_TYPE,
    OUTPUTS,
    PROPERTY_TYPES_SIMPLE,
    REFERENCE,
    SOCKET_IDENTIFIER,
    BLENDER_VERSION,
    FROM_NODE,
    FROM_SOCKET,
    NODES_AS_JSON_VERSION,
    TREES,
    TO_NODE,
    TO_SOCKET,
    IS_MULTI_INPUT,
    INTERFACE_ITEMS_ACTIVE,
    FromRoot,
    most_specific_type_handled,
)


class _Importer:
    def __init__(
        self,
        references: dict[Callable[[], bpy.types.bpy_struct]],
        debug_prints: bool,
    ):
        self.references = references
        self.debug_prints = debug_prints
        self.deserialzed = {}
        self.unresolved = {}

    ################################################################################
    # helper functions to be used in specific handlers
    ################################################################################

    def import_property_simple(
        self,
        obj: bpy.types.bpy_struct,
        assumed_type: type,
        prop: bpy.types.Property,
        attribute,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        assert prop.type in PROPERTY_TYPES_SIMPLE
        assert prop.identifier in [p.identifier for p in assumed_type.bl_rna.properties]

        # should just work^tm
        setattr(obj, prop.identifier, attribute)

    def import_property_pointer(
        self,
        obj: bpy.types.bpy_struct,
        assumed_type: type,
        prop: bpy.types.PointerProperty,
        attribute: dict,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        assert prop.type == "POINTER"
        assert prop.identifier in [p.identifier for p in assumed_type.bl_rna.properties]

        if REFERENCE in attribute:
            id = attribute[REFERENCE]
            if id not in self.references:
                raise RuntimeError(
                    f"{id} must be constructed before {from_root.to_str()}"
                )
            self.references[id]()
        else:
            self.references

    ################################################################################
    # internals
    ################################################################################

    def _import_obj_with_deserializer(
        self,
        accessor: Callable[[], bpy.types.bpy_struct],
        parent: bpy.types.bpy_struct,
        d: dict,
        deserializer: Callable[
            [Self, bpy.types.bpy_struct, dict, FromRoot], bpy.types.bpy_struct
        ],
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())
        if ID in d:
            if d[ID] in self.deserialzed:
                raise RuntimeError(f"Double deserialization: {from_root.to_str()}")
            self.deserialzed[d[ID]] = accessor

            return deserializer(self, accessor, parent, d, from_root)

    def _import_obj(
        self,
        accessor: Callable[[], bpy.types.bpy_struct],
        parent: bpy.types.bpy_struct,
        d: dict,
        from_root: FromRoot,
    ):
        assumed_type = most_specific_type_handled(self.specific_handlers, type(obj))
        specific_handler = self.specific_handlers[assumed_type]
        pass


def _check_version(d: dict):
    exporter_blender_version = d[BLENDER_VERSION]
    importer_blender_version = bpy.app.version_string
    if exporter_blender_version != importer_blender_version:
        return f"Blender version mismatch. File version: {exporter_blender_version}, but running {importer_blender_version}"

    exporter_node_as_json_version = d[NODES_AS_JSON_VERSION]
    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        blender_manifest = tomllib.load(f)
    importer_node_as_json_version = blender_manifest["version"]
    name = blender_manifest["name"]

    if exporter_node_as_json_version != importer_node_as_json_version:
        return f"{name} version mismatch. File version: {exporter_node_as_json_version}, but running {importer_node_as_json_version}"


def import_nodes(
    input_file: str,
    to_reference: set,
    allow_version_mismatch=False,
    overwrite=False,
):

    references = {}
    for reference in to_reference:
        lookup = reference.path_from_module()
        references[lookup] = functools.partial(eval, lookup)

    importer = _Importer(
        references=references,
        debug_prints=True,
    )

    with Path(input_file).open("r", encoding="utf-8") as f:
        d = json.load(f)

    version_mismatch = _check_version(d)
    if version_mismatch is not None:
        if allow_version_mismatch:
            print(version_mismatch, file=sys.stderr)
        else:
            raise RuntimeError(version_mismatch)

    # important to construct in reverse order
    for tree in reversed(d[TREES]):
        importer.import_node_tree(tree, overwrite)


#    def _import_property(
#        self,
#        attribute,
#        obj: bpy.types.bpy_struct,
#        prop: bpy.types.Property,
#    ):
#        # should just work^tm
#        if prop.type in ["BOOLEAN", "INT", "FLOAT", "STRING", "ENUM"]:
#            setattr(obj, prop.identifier, attribute)
#            return
#
#        # TODO: this might not work
#        # wow this is really tricky!
#        # the key is the result from `path_from_module` but the value can't be a handle
#        # because that might become invalidated as we're modifying the underlying containers?
#        if prop.type == "POINTER":
#            # setattr(obj, prop.identifier, self.references[attribute]())
#            return
#
#        if prop.type == "COLLECTION":
#            raise RuntimeError(
#                "You have a use case for collection properties in nodes? Please tell use about this:\nhttps://github.com/Algebraic-UG/nodes_as_json/issues/new"
#            )
#
#        raise RuntimeError(f"Unknown property type: {prop.type}")
#
#    def _import_all_writable_properties(self, d: dict, obj: bpy.types.bpy_struct):
#        for prop in obj.bl_rna.properties:
#            if obj.is_property_readonly(prop.identifier):
#                continue
#            if prop.identifier in d:
#                self._import_property(d[prop.identifier], obj, prop)
#
#    def _import_node_socket(
#        self,
#        d: dict,
#        sockets: bpy.types.NodeInputs | bpy.types.NodeOutputs,
#    ):
#        socket = next(
#            (socket for socket in sockets if socket.identifier == d[SOCKET_IDENTIFIER]),
#            None,
#        )
#        if socket is None:
#            print(
#                "You have a use case for socket creation? Please tell use about this:\nhttps://github.com/Algebraic-UG/nodes_as_json/issues/new",
#                file=sys.stderr,
#            )
#            socket = sockets.new(
#                type=d["bl_idname"],
#                name=d["name"],
#                identifier=d[SOCKET_IDENTIFIER],
#                # this technically only needed for inputs
#                use_multi_input=d[IS_MULTI_INPUT],
#            )
#        self._import_all_writable_properties(d, socket)
#
#    def _import_nodes(self, l: list, node_tree: bpy.types.NodeTree):
#        node_tree.nodes.clear()
#        for d in l:
#            node = node_tree.nodes.new(d["bl_idname"])
#            self._import_all_writable_properties(d, node)
#
#    def _import_node_sockets(self, l: list, node_tree: bpy.types.NodeTree):
#        for d in l:
#            node = node_tree.nodes[d["name"]]
#            for i in d[INPUTS]:
#                self._import_node_socket(i, node.inputs)
#            for o in d[OUTPUTS]:
#                self._import_node_socket(o, node.outputs)
#
#    def _import_node_links(self, l: list, node_tree: bpy.types.NodeTree):
#        node_tree.links.clear()
#        for d in l:
#            from_node = next(n for n in node_tree.nodes if n.name == d[FROM_NODE])
#            from_socket = next(
#                s for s in from_node.outputs if s.identifier == d[FROM_SOCKET]
#            )
#            to_node = next(n for n in node_tree.nodes if n.name == d[TO_NODE])
#            to_socket = next(s for s in to_node.inputs if s.identifier == d[TO_SOCKET])
#
#            link = node_tree.links.new(input=from_socket, output=to_socket)
#            self._import_all_writable_properties(d, link)
#
#    def import_node_tree(self, d: dict, overwrite: bool, material_name: str = None):
#        original_name = d["name"]
#
#        if material_name is None:
#            if overwrite and original_name in bpy.data.node_groups:
#                node_tree = bpy.data.node_groups[original_name]
#            else:
#                node_tree = bpy.data.node_groups.new(
#                    type=d[NODE_TREE_TYPE],
#                    name=original_name,
#                )
#        else:
#            # this can only happen for the top level
#            if overwrite:
#                mat = bpy.data.materials[material_name]
#            else:
#                mat = bpy.data.materials.new(material_name)
#            mat.use_nodes = True
#            node_tree = mat.node_tree
#
#        self._import_all_writable_properties(d, node_tree)
#
#        # if not overriding, the name might be different
#        self.references[f'bpy.data.node_groups["{original_name}"]'] = (
#            lambda: bpy.data.node_groups[node_tree.name]
#        )
#
#        self._import_nodes(d[NODE_TREE_NODES], node_tree)
#        self._import_node_links(d[NODE_TREE_LINKS], node_tree)
#
#        # the links can affect what default enum values can be set
#        # so we have to do nodes -> links -> sockets
#        self._import_node_sockets(d[NODE_TREE_NODES], node_tree)
#
#
