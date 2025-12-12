import bpy

import base64
import gzip
import json
from types import NoneType

from typing import Any, Type, Tuple, Iterator

import sys
import tomllib
from pathlib import Path

from .common import (
    DATA,
    DESERIALIZER,
    FORBIDDEN_PROPERTIES,
    GETTER,
    ID,
    MATERIAL_NAME,
    SIMPLE_PROP_TYPE,
    SIMPLE_PROPERTY_TYPES_AS_STRS,
    BLENDER_VERSION,
    SIMPLE_DATA_TYPE,
    SIMPLE_PROP_TYPE_TUPLE,
    TREE_CLIPPER_VERSION,
    TREES,
    FromRoot,
    most_specific_type_handled,
    MAGIC_STRING,
    EXTERNAL_SERIALIZATION,
    PROP_TYPE_ENUM,
    DEFAULT_VALUE,
    PROP_TYPE_POINTER,
    PROP_TYPE_COLLECTION,
    ITEMS,
    NAME,
    BL_RNA,
    RNA_TYPE,
    BL_IDNAME,
    EXTERNAL_DESCRIPTION,
    EXTERNAL,
)

from .id_data_getter import make_id_data_getter


class Importer:
    def __init__(
        self,
        specific_handlers: dict[type, DESERIALIZER],
        getters: dict[int, GETTER],
        debug_prints: bool,
    ) -> None:
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
        self.defer_after_nodes_before_links = []

        # we need to lookup nodes and their sockets for linking them
        self.current_tree = None

    ################################################################################
    # helper functions to be used in specific handlers
    ################################################################################

    def import_all_simple_writable_properties(
        self,
        *,
        getter: GETTER,
        serialization: dict[str, Any],
        assumed_type: Type[bpy.types.bpy_struct],
        forbidden: list[str],
        from_root: FromRoot,
    ) -> None:
        for prop in assumed_type.bl_rna.properties:
            if prop.identifier in forbidden:
                print(f"{from_root.add_prop(prop).to_str()}: explicitly forbidden")
                continue
            if prop.is_readonly or prop.type not in SIMPLE_PROPERTY_TYPES_AS_STRS:
                continue
            if prop.identifier not in serialization:
                if self.debug_prints:
                    print(
                        f"{from_root.add_prop(prop).to_str()}: missing, assuming default"
                    )
                continue
            assert isinstance(prop, SIMPLE_PROP_TYPE_TUPLE)
            self._import_property_simple(
                getter=getter,
                prop=prop,
                serialization=serialization[prop.identifier],
                from_root=from_root.add_prop(prop),
            )

    def import_properties_from_id_list(
        self,
        *,
        getter: GETTER,
        serialization: dict[str, Any],
        properties: list[str],
        from_root: FromRoot,
    ) -> None:
        for identifier in properties:
            prop = getter().bl_rna.properties[identifier]
            self._import_property(
                getter=getter,
                prop=prop,
                serialization=serialization[identifier],
                from_root=from_root.add_prop(prop),
            )

    ################################################################################
    # internals
    ################################################################################

    def _import_property_simple(
        self,
        *,
        getter: GETTER,
        prop: SIMPLE_PROP_TYPE,
        serialization: SIMPLE_DATA_TYPE,
        from_root: FromRoot,
    ) -> None:
        if self.debug_prints:
            print(f"{from_root.to_str()}: importing simple")

        assert prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS
        assert not prop.is_readonly

        identifier = prop.identifier

        if identifier in FORBIDDEN_PROPERTIES:
            if self.debug_prints:
                print(f"{from_root.to_str()}: forbidden")
            return

        if (
            (
                isinstance(getter(), bpy.types.NodeSocket)
                or isinstance(getter(), bpy.types.NodeTreeInterfaceSocket)
            )
            and prop.type == PROP_TYPE_ENUM
            and identifier == DEFAULT_VALUE
        ):
            if self.debug_prints:
                print(f"{from_root.to_str()}: defer setting enum default for now")
            self.set_socket_enum_defaults.append(
                lambda: setattr(getter(), identifier, serialization)
            )
            return

        if prop.type == PROP_TYPE_ENUM and prop.is_enum_flag:
            assert isinstance(serialization, list)
            setattr(getter(), identifier, set(serialization))
        else:
            setattr(getter(), identifier, serialization)

    def _import_property_pointer(
        self,
        *,
        getter: GETTER,
        prop: bpy.types.PointerProperty,
        serialization: dict[str, Any] | int,
        from_root: FromRoot,
    ) -> None:
        if self.debug_prints:
            print(f"{from_root.to_str()}: importing pointer")

        assert prop.type == PROP_TYPE_POINTER
        identifier = prop.identifier

        if serialization is None:
            if prop.is_readonly:
                assert getattr(getter(), identifier) is None
            else:
                setattr(getter(), identifier, None)
        elif isinstance(serialization, int):
            if prop.is_readonly:
                raise RuntimeError("Readonly pointer can't deferred in json")
            if serialization not in self.getters:
                raise RuntimeError(
                    f"Id {serialization} not deserialized or provided yet"
                )
            if self.debug_prints:
                print(f"{from_root.to_str()}: resolving {serialization}")
            setattr(getter(), identifier, self.getters[serialization]())
        else:
            attribute = getattr(getter(), identifier)
            if attribute is None:
                raise RuntimeError("None pointer without deferring doesn't work")
            self._import_obj(
                getter=lambda: getattr(getter(), identifier),
                serialization=serialization,
                from_root=from_root,
            )

    def _import_property_collection(
        self,
        *,
        getter: GETTER,
        prop: bpy.types.CollectionProperty,
        serialization: dict[str, Any],
        from_root: FromRoot,
    ) -> None:
        if self.debug_prints:
            print(f"{from_root.to_str()}: importing collection")

        assert prop.type == PROP_TYPE_COLLECTION
        assert "items" in serialization[DATA]

        identifier = prop.identifier
        attribute = getattr(getter(), identifier)

        self._import_obj(
            getter=lambda: getattr(getter(), identifier),
            serialization=serialization,
            from_root=from_root,
        )

        serialized_items = serialization[DATA][ITEMS]

        if len(serialized_items) != len(attribute):
            raise RuntimeError(
                f"expected {len(serialized_items)} to be ready but deserialized {len(attribute)}"
            )

        def make_getter(i: int) -> GETTER:
            return lambda: getattr(getter(), identifier)[i]

        for i, item in enumerate(serialized_items):
            name = item.get(NAME, "unnamed")
            self._import_obj(
                getter=make_getter(i),
                serialization=serialized_items[i],
                from_root=from_root.add(f"[{i}] ({name})"),
            )

    def _import_property(
        self,
        *,
        getter: GETTER,
        prop: bpy.types.Property,
        serialization: SIMPLE_DATA_TYPE | dict[str, Any],
        from_root: FromRoot,
    ) -> None:
        if prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS:
            assert isinstance(prop, SIMPLE_PROP_TYPE_TUPLE)
            return self._import_property_simple(
                getter=getter,
                prop=prop,
                serialization=serialization,  # type: ignore
                from_root=from_root,
            )
        elif prop.type == PROP_TYPE_POINTER:
            assert isinstance(prop, bpy.types.PointerProperty)
            return self._import_property_pointer(
                getter=getter,
                prop=prop,
                serialization=serialization,  # type: ignore
                from_root=from_root,
            )
        elif prop.type == PROP_TYPE_COLLECTION:
            assert isinstance(prop, bpy.types.CollectionProperty)
            return self._import_property_collection(
                getter=getter,
                prop=prop,
                serialization=serialization,  # type: ignore
                from_root=from_root,
            )
        else:
            raise RuntimeError(f"Unknown property type: {prop.type}")

    def _error_out(
        self,
        *,
        getter: GETTER,
        reason: str,
        from_root: FromRoot,
    ) -> None:
        raise RuntimeError(
            f"""\
More specific handler needed for type: {type(getter())}
Reason: {reason}
From root: {from_root.to_str()}"""
        )

    def _import_obj_with_deserializer(
        self,
        *,
        getter: GETTER,
        serialization: dict[str, Any],
        deserializer: DESERIALIZER,
        from_root: FromRoot,
    ) -> None:
        if self.debug_prints:
            print(f"{from_root.to_str()}: importing")

        if serialization[ID] in self.getters:
            raise RuntimeError(f"Double deserialization: {from_root.to_str()}")
        self.getters[serialization[ID]] = getter

        deserializer(
            self,
            getter,
            serialization[DATA],
            from_root,
        )

    def _import_obj(
        self,
        *,
        getter: GETTER,
        serialization: dict[str, Any],
        from_root: FromRoot,
    ) -> None:
        # edge case for things like bpy_prop_collection that aren't real RNA types?
        if not hasattr(getter(), BL_RNA):
            assert isinstance(getter(), bpy.types.bpy_prop_collection)
            return self._import_obj_with_deserializer(
                getter=getter,
                serialization=serialization,
                deserializer=self.specific_handlers[NoneType],
                from_root=from_root,
            )

        assumed_type = most_specific_type_handled(self.specific_handlers, getter())
        if (
            isinstance(getter(), bpy.types.bpy_prop_collection)
            and assumed_type is NoneType
        ):
            self._error_out(
                getter=getter,
                reason="collections must be handled *specifically*",
                from_root=from_root,
            )

        specific_handler = self.specific_handlers[assumed_type]
        handled_prop_ids = (
            [prop.identifier for prop in assumed_type.bl_rna.properties]  # type: ignore
            if assumed_type is not NoneType
            else []
        )
        unhandled_prop_ids = [
            prop.identifier
            for prop in getter().bl_rna.properties
            if prop.identifier not in handled_prop_ids
            and prop.identifier not in [RNA_TYPE]
        ]

        def deserializer(
            importer: "Importer",
            getter: GETTER,
            serialization: dict[str, Any],
            from_root: FromRoot,
        ) -> None:
            for identifier in unhandled_prop_ids:
                prop = getter().bl_rna.properties[identifier]
                prop_from_root = from_root.add_prop(prop)
                if prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS:
                    if prop.is_readonly:
                        if self.debug_prints:
                            print(f"{prop_from_root.to_str()}: skipping readonly")
                        continue

                if prop.identifier not in serialization:
                    if prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS:
                        if self.debug_prints:
                            print(f"{prop_from_root.to_str()}: missing, assume default")
                        continue
                    if prop.type == PROP_TYPE_POINTER and not prop.is_readonly:
                        if self.debug_prints:
                            print(f"{prop_from_root.to_str()}: missing, assume not set")
                        continue
                    self._error_out(
                        getter=getter,
                        reason="missing property in serialization",
                        from_root=prop_from_root,
                    )

                # pylint: disable=protected-access
                self._import_property(
                    getter=getter,
                    prop=prop,
                    serialization=serialization[identifier],
                    from_root=prop_from_root,
                )

            specific_handler(importer, getter, serialization, from_root)

        self._import_obj_with_deserializer(
            getter=getter,
            serialization=serialization,
            deserializer=deserializer,
            from_root=from_root,
        )

    def _import_node_tree(
        self,
        *,
        serialization: dict[str, Any],
        overwrite: bool,
        material_name: str | None = None,
    ) -> Tuple[bool, str]:
        original_name = serialization[DATA][NAME]

        if material_name is None:
            can_overwrite = (
                overwrite
                and original_name in bpy.data.node_groups
                # we can't write properties of library items
                # https://github.com/Algebraic-UG/tree_clipper/issues/83
                and bpy.data.node_groups[original_name].library is None
                and bpy.data.node_groups[original_name].library_weak_reference is None
            )
            if can_overwrite:
                node_tree = bpy.data.node_groups[original_name]
            else:
                node_tree = bpy.data.node_groups.new(
                    type=serialization[DATA][BL_IDNAME],
                    name=original_name,
                )

            from_root = FromRoot([f"Tree ({node_tree.name})"])

            name = node_tree.name

            def getter() -> bpy.types.NodeTree:
                return bpy.data.node_groups[name]

        else:
            # this can only happen for the top level

            can_overwrite = (
                overwrite
                and original_name in bpy.data.materials
                # we can't write properties of library items
                # https://github.com/Algebraic-UG/tree_clipper/issues/83
                and bpy.data.materials[original_name].library is None
                and bpy.data.materials[original_name].library_weak_reference is None
            )
            if can_overwrite:
                mat = bpy.data.materials[material_name]
            else:
                mat = bpy.data.materials.new(material_name)

            mat.use_nodes = True
            node_tree = mat.node_tree

            from_root = FromRoot([f"Material ({mat.name})"])

            name = mat.name

            def getter() -> bpy.types.ShaderNodeTree:
                return bpy.data.materials[name].node_tree  # type: ignore

        if self.debug_prints:
            print(f"{from_root.to_str()}: entering")

        self.current_tree = node_tree
        self._import_obj(
            getter=getter,
            serialization=serialization,
            from_root=from_root,
        )
        self.current_tree = None

        for func in self.set_socket_enum_defaults:
            func()
        self.set_socket_enum_defaults.clear()

        return (material_name is None, name)


def _check_version(data: dict) -> None | str:
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
        overwrite: bool,
        debug_prints: bool,
    ) -> None:
        self.specific_handlers = specific_handlers
        self.allow_version_mismatch = allow_version_mismatch
        self.overwrite = overwrite
        self.debug_prints = debug_prints


def _import_nodes_from_dict(
    *,
    data: dict[str, Any],
    getters: dict[int, GETTER],
    parameters: ImportParameters,
) -> Tuple[bool, str]:
    importer = Importer(
        specific_handlers=parameters.specific_handlers,
        getters=getters,
        debug_prints=parameters.debug_prints,
    )

    version_mismatch = _check_version(data)
    if version_mismatch is not None:
        if parameters.allow_version_mismatch:
            print(version_mismatch, file=sys.stderr)
        else:
            raise RuntimeError(version_mismatch)

    for tree in data[TREES][:-1]:
        # pylint: disable=protected-access
        importer._import_node_tree(serialization=tree, overwrite=parameters.overwrite)

    # root tree needs special treatment, might be material
    # pylint: disable=protected-access
    return importer._import_node_tree(
        serialization=data[TREES][-1],
        overwrite=parameters.overwrite,
        material_name=None if MATERIAL_NAME not in data else data[MATERIAL_NAME],
    )


class ImportIntermediate:
    def __init__(self) -> None:
        self.data: dict[str, Any] = None
        self.getters: dict[int, GETTER] = {}

    def from_str(self, string: str) -> None:
        compressed = string.startswith(MAGIC_STRING)
        if compressed:
            base64_str = string[len(MAGIC_STRING) :]
            gzipped = base64.b64decode(base64_str)
            json_str = gzip.decompress(gzipped).decode("utf-8")
            data = json.loads(json_str)
        else:
            data = json.loads(string)

        self.data = data

    def from_file(self, file_path: Path) -> None:
        with file_path.open("r", encoding="utf-8") as file:
            compressed = file.read(len(MAGIC_STRING)) == MAGIC_STRING

        with file_path.open("r", encoding="utf-8") as file:
            if compressed:
                full = file.read()
                self.from_str(full)
            else:
                data = json.load(file)
                self.data = data

    def get_external(self) -> dict[int, EXTERNAL_SERIALIZATION]:
        assert isinstance(self.data, dict)
        return self.data[EXTERNAL]

    def set_external(
        self,
        ids_and_references: Iterator[Tuple[int, bpy.types.ID]],
    ) -> None:
        self.getters = dict(
            (external_id, make_id_data_getter(obj))
            for external_id, obj in ids_and_references
        )

        # double check that only skipped ones are missing
        for (
            external_id,
            external_item,
        ) in self.get_external().items():
            if external_item[EXTERNAL_DESCRIPTION] is None:
                self.getters[int(external_id)] = lambda: None
            else:
                assert int(external_id) in self.getters

    def import_nodes(self, parameters: ImportParameters) -> Tuple[bool, str]:
        return _import_nodes_from_dict(
            data=self.data,
            getters=self.getters,
            parameters=parameters,
        )
