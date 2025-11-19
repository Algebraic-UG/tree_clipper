from types import NoneType
import bpy

from typing import Any, Callable, Self

import sys
import tomllib
import json
from pathlib import Path

from .common import (
    DATA,
    ID,
    MATERIAL_NAME,
    PROPERTY_TYPES_SIMPLE,
    BLENDER_VERSION,
    TREE_CLIPPER_VERSION,
    TREES,
    FromRoot,
    most_specific_type_handled,
)

GETTER = Callable[[], bpy.types.bpy_struct]


# Any is actually the importer below
DESERIALIZER = Callable[[Any, bpy.types.bpy_struct, GETTER, dict, FromRoot], None]


class Importer:
    def __init__(
        self,
        specific_handlers: dict[type, DESERIALIZER],
        getters: dict[int, GETTER],
        debug_prints: bool,
    ):
        self.specific_handlers = specific_handlers
        self.getters = getters
        self.debug_prints = debug_prints

        # for sockets' default enum values we need to defer
        # first, we link everything up, then set the default values
        self.set_socket_enum_defaults = []

        # for the viewer items we need to set auto removal
        # only after the links are there
        self.set_auto_remove = []

        # for special nodes like the ones spanniung a repeat zone
        # we must defer things until all nodes are created
        # but it must happen before constructing the links
        self.create_special_node_connections = []

        # we need to lookup nodes and their sockets for linking them
        self.current_tree = None

    ################################################################################
    # helper functions to be used in specific handlers
    ################################################################################

    def import_property_simple(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        prop: bpy.types.Property,
        serialization: int | str,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(f"{from_root.to_str()}: importing simple")

        assert prop.type in PROPERTY_TYPES_SIMPLE
        assert not prop.is_readonly

        if (
            (
                isinstance(obj, bpy.types.NodeSocket)
                or isinstance(obj, bpy.types.NodeTreeInterfaceSocket)
            )
            and prop.type == "ENUM"
            and prop.identifier == "default"
        ):
            if self.debug_prints:
                print(f"{from_root.to_str()}: skipping enum default for now")
            self.set_socket_enum_defaults.append(
                lambda: setattr(getter(), prop.identifier, serialization)
            )
            return

        # should just work^tm
        setattr(obj, prop.identifier, serialization)

    def import_property_pointer(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        prop: bpy.types.PointerProperty,
        serialization: dict | int,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(f"{from_root.to_str()}: importing pointer")

        assert prop.type == "POINTER"

        if isinstance(serialization, int):
            if prop.is_readonly:
                raise RuntimeError("Readonly pointer can't deferred in json")
            if serialization not in self.getters:
                raise RuntimeError(
                    f"Id {serialization} not deserialized or provided yet"
                )
            if self.debug_prints:
                print(f"{from_root.to_str()}: resolving {serialization}")
            setattr(obj, self.getters[serialization]())
        else:
            attribute = getattr(obj, prop.identifier)
            if attribute is None:
                raise RuntimeError("None pointer without deferring doesn't work")
            self._import_obj(
                attribute,
                getter,
                serialization,
                from_root,
            )

    def import_property_collection(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        prop: bpy.types.CollectionProperty,
        serialization: dict,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(f"{from_root.to_str()}: importing collection")

        assert prop.type == "COLLECTION"
        assert "items" in serialization[DATA]

        attribute = getattr(obj, prop.identifier)

        self._import_obj(
            attribute,
            getter,
            serialization,
            from_root,
        )

        serialized_items = serialization[DATA]["items"]

        if len(serialized_items) != len(attribute):
            raise RuntimeError(
                f"expected {len(serialized_items)} to be ready but deserialized {len(attribute)}"
            )

        def make_getter(i: int):
            return lambda: getter()[i]

        for i, item in enumerate(attribute):
            self._import_obj(
                item,
                make_getter(i),
                serialized_items[i],
                from_root.add(f"[{i}]"),
            )

    def import_property(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        prop: bpy.types.CollectionProperty,
        serialization: dict,
        from_root: FromRoot,
    ):
        if prop.type in PROPERTY_TYPES_SIMPLE:
            return self.import_property_simple(
                obj, getter, prop, serialization, from_root
            )
        elif prop.type == "POINTER":
            return self.import_property_pointer(
                obj, getter, prop, serialization, from_root
            )
        elif prop.type == "COLLECTION":
            return self.import_property_collection(
                obj, getter, prop, serialization, from_root
            )
        else:
            raise RuntimeError(f"Unknown property type: {prop.type}")

    def import_all_simple_writable_properties(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        serialization: dict,
        assumed_type: type,
        from_root: FromRoot,
    ):
        for prop in assumed_type.bl_rna.properties:
            if prop.is_readonly or prop.type not in PROPERTY_TYPES_SIMPLE:
                continue
            if prop.identifier not in serialization:
                if self.debug_prints:
                    print(
                        f"{from_root.add_prop(prop).to_str()}: missing, assuming default"
                    )
                continue
            self.import_property_simple(
                obj,
                getter,
                prop,
                serialization[prop.identifier],
                from_root.add_prop(prop),
            )

    def import_properties_from_id_list(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        serialization: dict,
        properties: list[str],
        from_root: FromRoot,
    ):
        def make_getter(identifier: str):
            return lambda: getattr(getter(), identifier)

        for prop in [obj.bl_rna.properties[p] for p in properties]:
            self.import_property(
                obj,
                make_getter(prop.identifier),
                prop,
                serialization[prop.identifier],
                from_root.add_prop(prop),
            )

    ################################################################################
    # internals
    ################################################################################

    def _error_out(self, obj: bpy.types.bpy_struct, reason: str, from_root: FromRoot):
        raise RuntimeError(
            f"""\
More specific handler needed for type: {type(obj)}
Reason: {reason}
From root: {from_root.to_str()}"""
        )

    def _attempt_import_property(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        prop: bpy.types.CollectionProperty,
        obj_serialization: dict,
        from_root: FromRoot,
    ):
        if prop.type in PROPERTY_TYPES_SIMPLE:
            if prop.is_readonly:
                if self.debug_prints:
                    print(f"{from_root.to_str()}: skipping readonly")
                return

        if prop.identifier not in obj_serialization:
            if prop.type in PROPERTY_TYPES_SIMPLE:
                if self.debug_prints:
                    print(f"{from_root.to_str()}: missing, assume default")
                return
            if prop.type == "POINTER" and not prop.is_readonly:
                if self.debug_prints:
                    print(f"{from_root.to_str()}: missing, assume not set")
                return
            self._error_out(obj, "missing property in serialization", from_root)

        self.import_property(
            obj,
            getter,
            prop,
            obj_serialization[prop.identifier],
            from_root,
        )

    def _import_obj_with_deserializer(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        serialization: dict,
        deserializer: DESERIALIZER,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(f"{from_root.to_str()}: importing")

        if serialization[ID] in self.getters:
            raise RuntimeError(f"Double deserialization: {from_root.to_str()}")
        self.getters[serialization[ID]] = getter

        deserializer(self, obj, getter, serialization[DATA], from_root)

    def _import_obj(
        self,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        serialization: dict,
        from_root: FromRoot,
    ):
        # edge case for things like bpy_prop_collection that aren't real RNA types?
        if not hasattr(obj, "bl_rna"):
            assert isinstance(obj, bpy.types.bpy_prop_collection)
            return self._import_obj_with_deserializer(
                obj,
                getter,
                serialization,
                self.specific_handlers[NoneType],
                from_root,
            )

        assumed_type = most_specific_type_handled(self.specific_handlers, obj)
        if isinstance(obj, bpy.types.bpy_prop_collection) and assumed_type is NoneType:
            self._error_out(
                obj, "collections must be handled *specifically*", from_root
            )

        specific_handler = self.specific_handlers[assumed_type]
        handled_prop_ids = (
            [p.identifier for p in assumed_type.bl_rna.properties]
            if assumed_type is not NoneType
            else []
        )
        unhandled_properties = [
            p
            for p in obj.bl_rna.properties
            if p.identifier not in handled_prop_ids and p.identifier not in ["rna_type"]
        ]

        def _deserializer(
            importer: Self,
            obj: bpy.types.bpy_struct,
            getter: GETTER,
            serialization: dict,
            from_root: FromRoot,
        ):
            def make_getter(identifier: str):
                return lambda: getattr(getter(), identifier)

            for prop in unhandled_properties:
                # pylint: disable=protected-access
                importer._attempt_import_property(
                    obj,
                    make_getter(prop.identifier),
                    prop,
                    serialization,
                    from_root.add_prop(prop),
                )

            specific_handler(importer, obj, getter, serialization, from_root)

        self._import_obj_with_deserializer(
            obj,
            getter,
            serialization,
            _deserializer,
            from_root,
        )

    def _import_node_tree(
        self,
        serialization: dict,
        overwrite: bool,
        material_name: str = None,
    ):
        original_name = serialization[DATA]["name"]

        if material_name is None:
            if overwrite and original_name in bpy.data.node_groups:
                node_tree = bpy.data.node_groups[original_name]
            else:
                node_tree = bpy.data.node_groups.new(
                    type=serialization[DATA]["bl_idname"],
                    name=original_name,
                )

            from_root = FromRoot([f"Tree ({node_tree.name})"])

            def getter():
                return bpy.data.node_groups[node_tree.name]

        else:
            # this can only happen for the top level
            if overwrite:
                mat = bpy.data.materials[material_name]
            else:
                mat = bpy.data.materials.new(material_name)

            mat.use_nodes = True
            node_tree = mat.node_tree

            from_root = FromRoot([f"Material ({mat.name})"])

            def getter():
                return bpy.data.materials[mat.name].node_tree

        if self.debug_prints:
            print(f"{from_root.to_str()}: entering")

        self.current_tree = node_tree
        self._import_obj(
            node_tree,
            getter,
            serialization,
            from_root,
        )
        self.current_tree = None

        for f in self.set_socket_enum_defaults:
            f()
        self.set_socket_enum_defaults.clear()


def _check_version(d: dict):
    exporter_blender_version = d[BLENDER_VERSION]
    importer_blender_version = bpy.app.version_string
    if exporter_blender_version != importer_blender_version:
        return f"Blender version mismatch. File version: {exporter_blender_version}, but running {importer_blender_version}"

    exporter_node_as_json_version = d[TREE_CLIPPER_VERSION]
    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        blender_manifest = tomllib.load(f)
    importer_node_as_json_version = blender_manifest["version"]
    name = blender_manifest["name"]

    if exporter_node_as_json_version != importer_node_as_json_version:
        return f"{name} version mismatch. File version: {exporter_node_as_json_version}, but running {importer_node_as_json_version}"


################################################################################
# entry point
################################################################################


def import_nodes(
    *,
    input_file: str,
    specific_handlers: dict[type, DESERIALIZER],
    allow_version_mismatch=False,
    getters: dict[int, GETTER],
    overwrite=False,
):
    importer = Importer(
        specific_handlers=specific_handlers,
        getters=getters,
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
    for tree in reversed(d[TREES][1:]):
        # pylint: disable=protected-access
        importer._import_node_tree(tree, overwrite)

    # root tree needs special treatment, might be material
    # pylint: disable=protected-access
    importer._import_node_tree(
        d[TREES][0],
        overwrite,
        None if MATERIAL_NAME not in d else d[MATERIAL_NAME],
    )


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
