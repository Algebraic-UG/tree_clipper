import bpy

import base64
import gzip
import json
from pathlib import Path
from types import NoneType
from typing import Any, cast, Type, Iterator, Tuple

import tomllib

from .common import (
    BLENDER_VERSION,
    DATA,
    DISPLAY_SHAPE,
    EXTERNAL_DESCRIPTION,
    FORBIDDEN_PROPERTIES,
    ID,
    MAGIC_STRING,
    MATERIAL_NAME,
    SIMPLE_PROPERTY_TYPES_AS_STRS,
    SERIALIZER,
    SIMPLE_DATA_TYPE,
    SIMPLE_PROP_TYPE,
    TREE_CLIPPER_VERSION,
    TREES,
    FromRoot,
    most_specific_type_handled,
    no_clobber,
    EXTERNAL_SERIALIZATION,
    PROP_TYPE_BOOLEAN,
    PROP_TYPE_INT,
    PROP_TYPE_FLOAT,
    PROP_TYPE_ENUM,
    PROP_TYPE_POINTER,
    PROP_TYPE_COLLECTION,
    NAME,
    ITEMS,
    BL_RNA,
    FROM_ROOT,
    RNA_TYPE,
    EXTERNAL,
    EXTERNAL_FIXED_TYPE_NAME,
    NODE_TREE,
)

from .id_data_getter import canonical_reference


class Pointer:
    def __init__(
        self,
        *,
        obj: bpy.types.bpy_struct,
        identifier: str,
        pointer_id: int,
        fixed_type_name: str,
        from_root: FromRoot,
    ) -> None:
        # we need these to show a pointer property in the UI
        self.obj = obj
        self.identifier = identifier

        # so the user can find the pointer it the tree and serialization
        self.from_root = from_root
        self.pointer_id = pointer_id

        # this is determined after everything is serialized and is used in deserialization
        self.pointee_id = None

        # needed for the selection on import
        self.fixed_type_name = fixed_type_name


class Exporter:
    def __init__(
        self,
        *,
        specific_handlers: dict[type, SERIALIZER],
        write_from_roots: bool,
        debug_prints: bool,
    ) -> None:
        self.next_id = 0
        self.specific_handlers = specific_handlers
        self.debug_prints = debug_prints
        self.write_from_roots = write_from_roots
        self.pointers = {}
        self.serialized = {}
        self.current_tree = None

    ################################################################################
    # helper functions to be used in specific handlers
    ################################################################################

    def export_all_simple_writable_properties(
        self,
        *,
        obj: bpy.types.bpy_struct,
        assumed_type: Type[bpy.types.bpy_struct],
        from_root: FromRoot,
    ) -> dict[str, SIMPLE_DATA_TYPE]:
        data = {}
        for prop in assumed_type.bl_rna.properties:
            if prop.is_readonly or prop.type not in SIMPLE_PROPERTY_TYPES_AS_STRS:
                continue
            prop_from_root = from_root.add_prop(prop)
            if bpy.app.version == (5, 0, 0):
                # https://github.com/Algebraic-UG/tree_clipper/issues/48
                if (
                    isinstance(obj, bpy.types.NodeSocket)
                    and prop.identifier == DISPLAY_SHAPE
                ):
                    if self.debug_prints:
                        print(f"{prop_from_root.to_str()}: skipping broken")
                    continue

            if prop.identifier in FORBIDDEN_PROPERTIES:
                if self.debug_prints:
                    print(f"{prop_from_root.to_str()}: forbidden")
                continue
            data[prop.identifier] = self._export_property_simple(
                obj=obj,
                prop=prop,  # type: ignore
                from_root=prop_from_root,
            )
        return data

    def export_properties_from_id_list(
        self,
        *,
        obj: bpy.types.bpy_struct,
        properties: list[str],
        serialize_pointees: bool,
        from_root: FromRoot,
    ) -> dict[str, Any]:
        data = {}
        for prop in [obj.bl_rna.properties[p] for p in properties]:
            data[prop.identifier] = self._export_property(
                obj=obj,
                prop=prop,
                serialize_pointee=serialize_pointees,
                from_root=from_root.add_prop(prop),
            )
        return data

    ################################################################################
    # internals
    ################################################################################

    def _export_property_simple(
        self,
        *,
        obj: bpy.types.bpy_struct,
        prop: SIMPLE_PROP_TYPE,
        from_root: FromRoot,
    ) -> SIMPLE_DATA_TYPE:
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting simple")

        assert prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS

        attribute = getattr(obj, prop.identifier)
        if prop.type in [PROP_TYPE_BOOLEAN, PROP_TYPE_INT, PROP_TYPE_FLOAT]:
            assert isinstance(
                prop,
                (
                    bpy.types.BoolProperty,
                    bpy.types.IntProperty,
                    bpy.types.FloatProperty,
                ),
            )

            if prop.is_array:
                return list(attribute)

        if prop.type == PROP_TYPE_ENUM:
            assert isinstance(prop, bpy.types.EnumProperty)

            if prop.is_enum_flag:
                assert isinstance(attribute, set)
                return list(attribute)

        return attribute

    def _export_property_pointer(
        self,
        *,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.PointerProperty,
        serialize_pointee: bool,
        from_root: FromRoot,
    ) -> None | Pointer | dict[str, Any]:
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting pointer")

        assert prop.type == PROP_TYPE_POINTER

        attribute = getattr(obj, prop.identifier)

        if attribute is None:
            if self.debug_prints:
                print(f"{from_root.to_str()}: skipping not set")
            return None

        if serialize_pointee:
            return self._export_obj(obj=attribute, from_root=from_root)

        assert prop.fixed_type is not None
        pointer = Pointer(
            obj=obj,
            identifier=prop.identifier,
            pointer_id=self.next_id - 1,
            fixed_type_name=prop.fixed_type.bl_rna.identifier,  # ty: ignore[unresolved-attribute]
            from_root=from_root,
        )
        ref = canonical_reference(attribute)
        self.pointers.setdefault(ref, []).append(pointer)

        if self.debug_prints:
            print(f"{from_root.to_str()}: deferring")
        return pointer

    def _export_property_collection(
        self,
        *,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.CollectionProperty,
        from_root: FromRoot,
    ) -> dict[str, Any]:
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting collection")

        assert prop.type == PROP_TYPE_COLLECTION

        attribute = getattr(obj, prop.identifier)

        data = self._export_obj(obj=attribute, from_root=from_root)
        items = [
            self._export_obj(
                obj=element,
                from_root=from_root.add(
                    f"[{i}] ({getattr(attribute[i], NAME, 'unnamed')})"
                ),
            )
            for i, element in enumerate(attribute)
        ]
        no_clobber(data[DATA], ITEMS, items)

        return data

    def _export_property(
        self,
        *,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        serialize_pointee: bool,
        from_root: FromRoot,
    ) -> None | SIMPLE_DATA_TYPE | Pointer | dict[str, Any]:
        if prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS:
            return self._export_property_simple(
                obj=obj,
                prop=prop,  # type: ignore
                from_root=from_root,
            )
        elif prop.type == PROP_TYPE_POINTER:
            assert isinstance(prop, bpy.types.PointerProperty)
            return self._export_property_pointer(
                obj=obj,
                prop=prop,
                serialize_pointee=serialize_pointee,
                from_root=from_root,
            )
        elif prop.type == PROP_TYPE_COLLECTION:
            assert isinstance(prop, bpy.types.CollectionProperty)
            return self._export_property_collection(
                obj=obj,
                prop=prop,
                from_root=from_root,
            )
        else:
            raise RuntimeError(f"Unknown property type: {prop.type}")

    def _attempt_export_property(
        self,
        *,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        from_root,
    ) -> None | SIMPLE_DATA_TYPE | Pointer | dict[str, Any]:
        def error_out(reason: str):
            raise RuntimeError(
                f"""\
More specific handler needed for type: {type(obj)}
Reason: {reason}
From root: {from_root.to_str()}"""
            )

        if prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS:
            if prop.is_readonly:
                return None
            return self._export_property_simple(
                obj=obj,
                prop=prop,  # type: ignore
                from_root=from_root,
            )

        attribute = getattr(obj, prop.identifier)
        if attribute is None:
            if self.debug_prints:
                print(f"{from_root.to_str()}: skipping not set")
            return None

        if prop.type == PROP_TYPE_POINTER:
            if prop.is_readonly and attribute.id_data != self.current_tree:
                error_out("readonly pointer to external")
            serialize_pointee = (
                attribute.id_data == self.current_tree and prop.is_readonly
            )
            return self._export_property_pointer(
                obj=obj,
                prop=cast(bpy.types.PointerProperty, prop),
                serialize_pointee=serialize_pointee,
                from_root=from_root,
            )

        if prop.type == PROP_TYPE_COLLECTION:
            prop = cast(bpy.types.CollectionProperty, prop)
            if (
                hasattr(attribute, BL_RNA)
                and any(
                    len(func.parameters) != 0 for func in attribute.bl_rna.functions
                )
                and type(prop.fixed_type) not in self.specific_handlers
            ):
                error_out(
                    "collection with function that requires args and the elements aren't specifically handled"
                )
            return self._export_property_collection(
                obj=obj,
                prop=prop,
                from_root=from_root,
            )

        raise RuntimeError(f"Unknown property type: {prop.type}")

    def _export_obj_with_serializer(
        self,
        *,
        obj: bpy.types.bpy_struct,
        serializer: SERIALIZER,
        from_root: FromRoot,
    ) -> dict[str, Any]:
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting")

        this_id = self.next_id
        self.next_id += 1

        ref = canonical_reference(obj)
        if ref in self.serialized:
            raise RuntimeError(f"Double serialization: {from_root.to_str()}")
        self.serialized[ref] = this_id

        data = {
            ID: this_id,
            DATA: serializer(self, obj, from_root),
        }
        if self.write_from_roots:
            data[FROM_ROOT] = from_root.to_str()
        return data

    def _export_obj(
        self,
        *,
        obj: bpy.types.bpy_struct,
        from_root: FromRoot,
    ) -> dict[str, Any]:
        # edge case for things like bpy_prop_collection that aren't real RNA types?
        # https://projects.blender.org/blender/blender/issues/150092
        if not hasattr(obj, BL_RNA):
            assert isinstance(obj, bpy.types.bpy_prop_collection)
            return self._export_obj_with_serializer(
                obj=obj,
                serializer=self.specific_handlers[NoneType],
                from_root=from_root,
            )

        assumed_type = most_specific_type_handled(self.specific_handlers, obj)
        specific_handler = self.specific_handlers[assumed_type]
        handled_prop_ids = (
            [prop.identifier for prop in assumed_type.bl_rna.properties]  # type: ignore
            if assumed_type is not NoneType
            else []
        )
        unhandled_properties = [
            prop
            for prop in obj.bl_rna.properties
            if prop.identifier not in handled_prop_ids
            and prop.identifier not in [RNA_TYPE]
        ]

        def serializer(
            exporter: "Exporter",
            obj: bpy.types.bpy_struct,
            from_root: FromRoot,
        ) -> dict[str, Any]:
            data = specific_handler(exporter, obj, from_root)
            for prop in unhandled_properties:
                # pylint: disable=protected-access
                prop_data = exporter._attempt_export_property(
                    obj=obj,
                    prop=prop,
                    from_root=from_root.add_prop(prop),
                )
                no_clobber(data, prop.identifier, prop_data)

            return data

        return self._export_obj_with_serializer(
            obj=obj,
            serializer=serializer,
            from_root=from_root,
        )

    def _export_node_tree(
        self,
        *,
        node_tree: bpy.types.NodeTree,
        from_root: FromRoot,
    ) -> dict[str, Any]:
        if self.debug_prints:
            print(f"{from_root.to_str()}: entering")

        self.current_tree = node_tree
        data = self._export_obj(obj=node_tree, from_root=from_root)
        self.current_tree = None

        return data


def _collect_sub_trees(
    *,
    current: bpy.types.NodeTree,
    trees: list[tuple[bpy.types.NodeTree, FromRoot]],
    from_root: FromRoot,
) -> None:
    for node in current.nodes:
        tree = getattr(node, NODE_TREE, None)
        if isinstance(tree, bpy.types.NodeTree):
            if all(tree.name != already_in[0].name for already_in in trees):
                sub_root = from_root.add(f"Group ({node.name}, {tree.name})")
                _collect_sub_trees(current=tree, trees=trees, from_root=sub_root)
    assert all(current.name != already_in[0].name for already_in in trees)
    trees.append((current, from_root))


################################################################################
# entry points
################################################################################


class ExportParameters:
    def __init__(
        self,
        *,
        is_material: bool,
        name: str,
        specific_handlers: dict[type, SERIALIZER],
        export_sub_trees: bool = True,
        debug_prints: bool,
        write_from_roots: bool,
    ) -> None:
        self.is_material = is_material
        self.name = name
        self.specific_handlers = specific_handlers
        self.export_sub_trees = export_sub_trees
        self.debug_prints = debug_prints
        self.write_from_roots = write_from_roots


class External:
    def __init__(
        self,
        *,
        pointed_to_by: Pointer,
    ) -> None:
        self.pointed_to_by = pointed_to_by

        # this should be further specified by user of the export
        # if it remains none, it'll be skipped on import
        self.description = None

        # if the user decides this doesn't need setting by the importer
        self.skip = False


def _export_nodes_to_dict(parameters: ExportParameters) -> dict[str, Any]:
    exporter = Exporter(
        specific_handlers=parameters.specific_handlers,
        debug_prints=parameters.debug_prints,
        write_from_roots=parameters.write_from_roots,
    )

    if parameters.is_material:
        from_root = FromRoot([f"Material ({parameters.name})"])
        root = bpy.data.materials[parameters.name].node_tree
    else:
        from_root = FromRoot([f"Root ({parameters.name})"])
        root = bpy.data.node_groups[parameters.name]

    assert root is not None

    trees = []
    if parameters.export_sub_trees:
        _collect_sub_trees(current=root, trees=trees, from_root=from_root)
    else:
        trees.append((root, from_root))

    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as file:
        blender_manifest = tomllib.load(file)

    data = {
        BLENDER_VERSION: bpy.app.version_string,
        TREE_CLIPPER_VERSION: blender_manifest["version"],
        TREES: [
            # pylint: disable=protected-access
            exporter._export_node_tree(node_tree=tree, from_root=from_root)
            for (tree, from_root) in trees
        ],
    }

    if parameters.is_material:
        data[MATERIAL_NAME] = parameters.name

    external = {}
    for obj, pointers in exporter.pointers.items():
        if obj in exporter.serialized:
            for pointer in pointers:
                pointer.pointee_id = exporter.serialized[obj]
        else:
            assert isinstance(obj, bpy.types.ID), "Only ID types can be external items"

            # Maybe it could be beneficial in some cases to have the option to have a single external item,
            # but it's also possible to use an additional group node to avieve the same thing.
            # Let's rather keep it simple here for now.
            for pointer in pointers:
                external_id = exporter.next_id
                exporter.next_id += 1
                external[external_id] = External(pointed_to_by=pointer)
                pointer.pointee_id = external_id

    data[EXTERNAL] = external

    return data


def _encode_external(obj: External) -> EXTERNAL_SERIALIZATION:
    return {
        EXTERNAL_DESCRIPTION: obj.description,
        EXTERNAL_FIXED_TYPE_NAME: obj.pointed_to_by.fixed_type_name,
    }


class _Encoder(json.JSONEncoder):
    def default(self, o) -> int | str | Any:
        if isinstance(o, Pointer):
            return o.pointee_id
        if isinstance(o, External):
            return _encode_external(o)
        return super().default(o)


class ExportIntermediate:
    def __init__(self, parameters: ExportParameters) -> None:
        self.data = _export_nodes_to_dict(parameters=parameters)

    def export_to_str(self, *, compress: bool, json_indent: int) -> str:
        if compress:
            json_str = json.dumps(self.data, cls=_Encoder)
            gzipped = gzip.compress(json_str.encode("utf-8"))
            base64_str = base64.b64encode(gzipped).decode("utf-8")
            return MAGIC_STRING + base64_str
        else:
            return json.dumps(self.data, cls=_Encoder, indent=json_indent)

    def export_to_file(
        self,
        *,
        file_path: Path,
        compress: bool,
        json_indent: int,
    ) -> None:
        with file_path.open("w", encoding="utf-8") as file:
            if compress:
                string = self.export_to_str(compress=compress, json_indent=json_indent)
                file.write(string)
            else:
                json.dump(self.data, file, cls=_Encoder, indent=json_indent)

    def get_external(self) -> dict[int, External]:
        return self.data[EXTERNAL]

    def set_external(
        self,
        ids_and_descriptions: Iterator[Tuple[int, str]],
    ) -> None:
        for external_id, description in ids_and_descriptions:
            self.data[EXTERNAL][external_id].description = description
