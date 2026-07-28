import base64
import gzip
import json
from collections.abc import Iterator
from operator import xor
from pathlib import Path
from types import NoneType
from typing import Any

import bpy

from .common import (
    BL_IDNAME,
    BL_RNA,
    BLENDER_VERSION,
    CURRENT_TREE_CLIPPER_VERSION,
    DATA,
    DEFAULT_VALUE,
    DESERIALIZER,
    EXTERNAL,
    EXTERNAL_DESCRIPTION,
    EXTERNAL_SCENE_ID,
    EXTERNAL_SERIALIZATION,
    FORBIDDEN_PROPERTIES,
    GETTER,
    ID,
    ITEMS,
    MAGIC_STRING,
    MATERIAL_NAME,
    NAME,
    PROP_TYPE_COLLECTION,
    PROP_TYPE_ENUM,
    PROP_TYPE_POINTER,
    RNA_TYPE,
    SCENES,
    SIMPLE_DATA_TYPE,
    SIMPLE_PROP_TYPE,
    SIMPLE_PROP_TYPE_TUPLE,
    SIMPLE_PROPERTY_TYPES_AS_STRS,
    TREE_CLIPPER_VERSION,
    TREES,
    FromRoot,
    most_specific_type_handled,
    no_clobber,
)
from .id_data_getter import make_id_data_getter
from .scene_info import SceneValidationError, verify_scene


class ImportReport:
    def __init__(
        self,
    ):
        self.imported_nodes: int = 0
        self.imported_links: int = 0
        self.imported_trees: int = 0
        self.rename_material: tuple[str, str] | None = None
        self.renames_node_group: dict[str, str] = {}
        self.warnings: list[str] = []

        self.last_getter: GETTER | None = None


class Importer:
    def __init__(
        self,
        *,
        blender_version: list[int],
        specific_handlers: dict[type, DESERIALIZER],
        getters: dict[int, GETTER],
        debug_prints: bool,
    ) -> None:
        self.blender_version = blender_version

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

        # this is for backward compatibilty
        # in some cases, disabled sockets do not exist in newer versions
        # and we remove them from the serialization
        # if links (or anything) reference them it we can avoid failure by
        # checking that it's been removed intentionally
        self.disabled_ids = set()

        self.report = ImportReport()

    ################################################################################
    # helper functions to be used in specific handlers
    ################################################################################

    def import_all_simple_writable_properties(
        self,
        *,
        getter: GETTER,
        serialization: dict[str, Any],
        assumed_type: type[bpy.types.bpy_struct],
        forbidden: list[str],
        from_root: FromRoot,
    ) -> None:
        for prop in assumed_type.bl_rna.properties:
            if prop.identifier in forbidden:
                if self.debug_prints:
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

    def register_as_deserialized(self, *, ident: int, getter: GETTER):
        if ident in self.getters:
            raise RuntimeError("Double deserialization: {ident}")
        self.getters[ident] = getter

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
            isinstance(
                getter(), (bpy.types.NodeSocket, bpy.types.NodeTreeInterfaceSocket)
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

        self._import_obj(
            getter=lambda: getattr(getter(), identifier),
            serialization=serialization,
            from_root=from_root,
        )

        attribute = getattr(getter(), identifier)
        serialized_items = serialization[DATA][ITEMS]

        if len(serialized_items) != len(attribute):
            raise RuntimeError(
                f"expected {len(serialized_items)} to be ready but deserialized {len(attribute)}"
            )

        def make_getter(i: int) -> GETTER:
            return lambda: getattr(getter(), identifier)[i]

        for i, item in enumerate(serialized_items):
            name = item[DATA].get(NAME, "unnamed")
            self._import_obj(
                getter=make_getter(i),
                serialization=item,
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

        # hack for inserting fake stuff for backward compat
        if serialization[ID] != -1:
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
        if isinstance(getter(), bpy.types.Node):
            self.report.imported_nodes += 1
        if isinstance(getter(), bpy.types.NodeLink):
            self.report.imported_links += 1
        if isinstance(getter(), bpy.types.NodeTree):
            self.report.imported_trees += 1

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
            specific_handler(importer, getter, serialization, from_root)

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

                    # https://github.com/Algebraic-UG/tree_clipper/issues/161
                    if prop.type in [
                        PROP_TYPE_POINTER,
                        PROP_TYPE_COLLECTION,
                    ] and prop.fixed_type.__module__ not in ["_bpy_types", "bpy.types"]:  # ty:ignore[unresolved-attribute]
                        self.report.warnings.append(
                            f"""This property is missing in serialization.
It appears to be from a third-party addon: {prop.fixed_type.__module__}

Tree Clipper is skipping it.
{prop_from_root.to_str()}"""  # ty:ignore[unresolved-attribute]
                        )
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
        material_name: str | None = None,
    ) -> None:
        original_name = (
            material_name if material_name is not None else serialization[DATA][NAME]
        )

        if material_name is None:
            node_tree = bpy.data.node_groups.new(
                type=serialization[DATA][BL_IDNAME],
                name=original_name,
            )

            from_root = FromRoot([f"Tree ({node_tree.name})"])

            name = node_tree.name
            self.report.renames_node_group[original_name] = name

            def getter() -> bpy.types.NodeTree:
                return bpy.data.node_groups[name]

        else:
            mat = bpy.data.materials.new(material_name)

            mat.use_nodes = True
            node_tree = mat.node_tree

            from_root = FromRoot([f"Material ({mat.name})"])

            name = mat.name
            self.report.rename_material = (original_name, name)

            def getter() -> bpy.types.ShaderNodeTree:
                return bpy.data.materials[name].node_tree

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

        self.report.last_getter = getter


def _check_version(data: dict) -> None:
    exporter_blender_version = [
        int(v) for v in data[BLENDER_VERSION].split(" ")[0].split(".")
    ]
    importer_blender_version = bpy.app.version

    if (
        exporter_blender_version[0] != importer_blender_version[0]
        or exporter_blender_version[1] > importer_blender_version[1]
    ):
        raise RuntimeError(
            f"Blender version mismatch. File version: {exporter_blender_version}, but running {importer_blender_version}"
        )

    exporter_version = data[TREE_CLIPPER_VERSION]
    importer_version = CURRENT_TREE_CLIPPER_VERSION

    ex_major, ex_minor, _ex_patch = [int(n) for n in exporter_version.split(".")]
    im_major, im_minor, _im_patch = [int(n) for n in importer_version.split(".")]

    if ex_major != im_major or ex_minor > im_minor:
        raise RuntimeError(
            f"Version mismatch. File version: {exporter_version}, but running {importer_version}"
        )


################################################################################
# entry points
################################################################################


class ImportParameters:
    def __init__(
        self,
        *,
        specific_handlers: dict[type, DESERIALIZER],
        debug_prints: bool,
    ) -> None:
        self.specific_handlers = specific_handlers
        self.debug_prints = debug_prints


def _from_str(string: str) -> dict[str, Any]:
    compressed = string.startswith(MAGIC_STRING)
    if compressed:
        base64_str = string[len(MAGIC_STRING) :]
        gzipped = base64.b64decode(base64_str)
        json_str = gzip.decompress(gzipped).decode("utf-8")
        return json.loads(json_str)
    else:
        return json.loads(string)


def _from_file(file_path: Path) -> dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as file:
        compressed = file.read(len(MAGIC_STRING)) == MAGIC_STRING

    with file_path.open("r", encoding="utf-8") as file:
        if compressed:
            full = file.read()
            return _from_str(full)
        else:
            return json.load(file)


class ImportIntermediate:
    def __init__(
        self,
        *,
        string: str | None = None,
        file_path: Path | None = None,
    ) -> None:
        if not xor(string is None, file_path is None):
            raise RuntimeError("Either provide string xor file_path")

        if string is not None:
            self.data = _from_str(string)
        if file_path is not None:
            self.data = _from_file(file_path)

        _check_version(self.data)

        if not self.data[TREES]:
            raise RuntimeError("There appear to be no trees to be imported")

        self.getters: dict[int, GETTER] = {}
        self.total_steps = len(self.data[TREES])

    def get_external(self) -> dict[str, EXTERNAL_SERIALIZATION]:
        assert isinstance(self.data, dict)
        return self.data[EXTERNAL]

    def set_external(
        self,
        ids_and_references: Iterator[tuple[int, bpy.types.ID | None]],
    ) -> None:
        for external_id, external_item in ids_and_references:
            scene_id = self.get_external()[str(external_id)][EXTERNAL_SCENE_ID]
            if scene_id is not None:
                assert isinstance(external_item, bpy.types.Scene), (
                    f"External Scene item {external_id} must be set to a valid Scene"
                )
                try:
                    verify_scene(
                        info=self.data[SCENES][str(scene_id)], scene=external_item
                    )
                except SceneValidationError as e:
                    raise RuntimeError(
                        f"Failed to validate external Scene {external_id} against info in {scene_id}\n{e}"
                    ) from e

            no_clobber(
                self.getters,
                external_id,
                make_id_data_getter(external_item),  # ty:ignore[invalid-argument-type]
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

    def start_import(self, parameters: ImportParameters) -> None:
        version_cycle = self.data[BLENDER_VERSION].split(" ")
        blender_version = [int(v) for v in version_cycle[0].split(".")]
        self.importer = Importer(
            blender_version=blender_version,
            specific_handlers=parameters.specific_handlers,
            getters=self.getters,
            debug_prints=parameters.debug_prints,
        )
        if len(version_cycle) > 1 and version_cycle[1] != "LTS":
            self.importer.report.warnings.append(
                f"This was exported from a Blender {version_cycle[1]} version."
            )

    def step(self) -> bool:
        assert isinstance(self.importer, Importer)
        if not self.data[TREES]:
            return False

        tree = self.data[TREES].pop(0)

        # root tree needs special treatment, might be material
        if not self.data[TREES] and MATERIAL_NAME in self.data:
            material_name = self.data[MATERIAL_NAME]
        else:
            material_name = None

        self.importer._import_node_tree(
            serialization=tree,
            material_name=material_name,
        )

        return True

    def progress(self) -> int:
        return self.total_steps - len(self.data[TREES])

    def import_all(self, parameters: ImportParameters) -> ImportReport:
        self.start_import(parameters)
        while self.step():
            pass
        return self.importer.report
