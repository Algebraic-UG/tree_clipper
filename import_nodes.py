import base64
import gzip
import json
from types import NoneType
import bpy

from typing import Self

import sys
import tomllib
from pathlib import Path

from .common import (
    DATA,
    DESERIALIZER,
    GETTER,
    ID,
    MATERIAL_NAME,
    PROPERTY_TYPES_SIMPLE,
    BLENDER_VERSION,
    TREE_CLIPPER_VERSION,
    TREES,
    FromRoot,
    most_specific_type_handled,
    MAGIC_STRING,
)


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

    def import_all_simple_writable_properties(
        self,
        *,
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
            self._import_property_simple(
                obj=obj,
                getter=getter,
                prop=prop,
                serialization=serialization[prop.identifier],
                from_root=from_root.add_prop(prop),
            )

    def import_properties_from_id_list(
        self,
        *,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        serialization: dict,
        properties: list[str],
        from_root: FromRoot,
    ):
        def make_getter(identifier: str):
            return lambda: getattr(getter(), identifier)

        for prop in [obj.bl_rna.properties[p] for p in properties]:
            self._import_property(
                obj=obj,
                getter=make_getter(prop.identifier),
                prop=prop,
                serialization=serialization[prop.identifier],
                from_root=from_root.add_prop(prop),
            )

    ################################################################################
    # internals
    ################################################################################

    def _import_property_simple(
        self,
        *,
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
                print(f"{from_root.to_str()}: defer setting enum default for now")
            self.set_socket_enum_defaults.append(
                lambda: setattr(getter(), prop.identifier, serialization)
            )
            return

        if prop.type == "ENUM" and prop.is_enum_flag:
            assert isinstance(serialization, list)
            setattr(obj, prop.identifier, set(serialization))
        else:
            setattr(obj, prop.identifier, serialization)

    def _import_property_pointer(
        self,
        *,
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
                obj=attribute,
                getter=getter,
                serialization=serialization,
                from_root=from_root,
            )

    def _import_property_collection(
        self,
        *,
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
            obj=attribute,
            getter=getter,
            serialization=serialization,
            from_root=from_root,
        )

        serialized_items = serialization[DATA]["items"]

        if len(serialized_items) != len(attribute):
            raise RuntimeError(
                f"expected {len(serialized_items)} to be ready but deserialized {len(attribute)}"
            )

        def make_getter(i: int):
            return lambda: getter()[i]

        for i, item in enumerate(attribute):
            current_name = getattr(item, "name", "unnamed")
            final_name = serialized_items[i][DATA].get("name", current_name)
            self._import_obj(
                obj=item,
                getter=make_getter(i),
                serialization=serialized_items[i],
                from_root=from_root.add(f"[{i}] ({final_name})"),
            )

    def _import_property(
        self,
        *,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        prop: bpy.types.CollectionProperty,
        serialization: dict,
        from_root: FromRoot,
    ):
        if prop.type in PROPERTY_TYPES_SIMPLE:
            return self._import_property_simple(
                obj=obj,
                getter=getter,
                prop=prop,
                serialization=serialization,
                from_root=from_root,
            )
        elif prop.type == "POINTER":
            return self._import_property_pointer(
                obj=obj,
                getter=getter,
                prop=prop,
                serialization=serialization,
                from_root=from_root,
            )
        elif prop.type == "COLLECTION":
            return self._import_property_collection(
                obj=obj,
                getter=getter,
                prop=prop,
                serialization=serialization,
                from_root=from_root,
            )
        else:
            raise RuntimeError(f"Unknown property type: {prop.type}")

    def _error_out(
        self,
        *,
        obj: bpy.types.bpy_struct,
        reason: str,
        from_root: FromRoot,
    ):
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
            self._error_out(
                obj=obj, reason="missing property in serialization", from_root=from_root
            )

        self._import_property(
            obj=obj,
            getter=getter,
            prop=prop,
            serialization=obj_serialization[prop.identifier],
            from_root=from_root,
        )

    def _import_obj_with_deserializer(
        self,
        *,
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
        *,
        obj: bpy.types.bpy_struct,
        getter: GETTER,
        serialization: dict,
        from_root: FromRoot,
    ):
        # edge case for things like bpy_prop_collection that aren't real RNA types?
        if not hasattr(obj, "bl_rna"):
            assert isinstance(obj, bpy.types.bpy_prop_collection)
            return self._import_obj_with_deserializer(
                obj=obj,
                getter=getter,
                serialization=serialization,
                deserializer=self.specific_handlers[NoneType],
                from_root=from_root,
            )

        assumed_type = most_specific_type_handled(self.specific_handlers, obj)
        if isinstance(obj, bpy.types.bpy_prop_collection) and assumed_type is NoneType:
            self._error_out(
                obj=obj,
                reason="collections must be handled *specifically*",
                from_root=from_root,
            )

        specific_handler = self.specific_handlers[assumed_type]
        handled_prop_ids = (
            [prop.identifier for prop in assumed_type.bl_rna.properties]
            if assumed_type is not NoneType
            else []
        )
        unhandled_properties = [
            prop
            for prop in obj.bl_rna.properties
            if prop.identifier not in handled_prop_ids
            and prop.identifier not in ["rna_type"]
        ]

        def deserializer(
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
            obj=obj,
            getter=getter,
            serialization=serialization,
            deserializer=deserializer,
            from_root=from_root,
        )

    def _import_node_tree(
        self,
        *,
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
            obj=node_tree,
            getter=getter,
            serialization=serialization,
            from_root=from_root,
        )
        self.current_tree = None

        for func in self.set_socket_enum_defaults:
            func()
        self.set_socket_enum_defaults.clear()


def _check_version(data: dict):
    exporter_blender_version = data[BLENDER_VERSION]
    importer_blender_version = bpy.app.version_string
    if exporter_blender_version != importer_blender_version:
        return f"Blender version mismatch. File version: {exporter_blender_version}, but running {importer_blender_version}"

    exporter_node_as_json_version = data[TREE_CLIPPER_VERSION]
    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as file:
        blender_manifest = tomllib.load(file)
    importer_node_as_json_version = blender_manifest["version"]
    name = blender_manifest["name"]

    if exporter_node_as_json_version != importer_node_as_json_version:
        return f"{name} version mismatch. File version: {exporter_node_as_json_version}, but running {importer_node_as_json_version}"


################################################################################
# entry points
################################################################################


class ImportParameters:
    def __init__(
        self,
        *,
        specific_handlers: dict[type, DESERIALIZER],
        allow_version_mismatch: bool,
        getters: dict[int, GETTER],
        overwrite: bool,
        debug_prints: bool,
    ):
        self.specific_handlers = specific_handlers
        self.allow_version_mismatch = allow_version_mismatch
        self.getters = getters
        self.overwrite = overwrite
        self.debug_prints = debug_prints


def _import_nodes_from_dict(*, data: dict, parameters: ImportParameters):
    importer = Importer(
        specific_handlers=parameters.specific_handlers,
        getters=parameters.getters,
        debug_prints=parameters.debug_prints,
    )

    version_mismatch = _check_version(data)
    if version_mismatch is not None:
        if parameters.allow_version_mismatch:
            print(version_mismatch, file=sys.stderr)
        else:
            raise RuntimeError(version_mismatch)

    # important to construct in reverse order
    for tree in reversed(data[TREES][1:]):
        # pylint: disable=protected-access
        importer._import_node_tree(serialization=tree, overwrite=parameters.overwrite)

    # root tree needs special treatment, might be material
    # pylint: disable=protected-access
    importer._import_node_tree(
        serialization=data[TREES][0],
        overwrite=parameters.overwrite,
        material_name=None if MATERIAL_NAME not in data else data[MATERIAL_NAME],
    )


class ImportIntermediate:
    def __init__(self, paremeters: ImportParameters):
        self.parameters = paremeters
        self.data = None

    def from_str(self, string: str):
        compressed = string.startswith(MAGIC_STRING)
        if compressed:
            base64_str = string[len(MAGIC_STRING) :]
            gzipped = base64.b64decode(base64_str)
            json_str = gzip.decompress(gzipped).decode("utf-8")
            data = json.loads(json_str)
        else:
            data = json.loads(string)

        self.data = data

    def from_file(self, file_path: Path):
        with file_path.open("r", encoding="utf-8") as file:
            compressed = file.read(len(MAGIC_STRING)) == MAGIC_STRING

        with file_path.open("r", encoding="utf-8") as file:
            if compressed:
                full = file.read()
                self.from_str(full)
            else:
                data = json.load(file)
                self.data = data

    def import_nodes(self):
        _import_nodes_from_dict(data=self.data, parameters=self.parameters)
