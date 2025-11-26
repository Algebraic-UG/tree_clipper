import base64
import gzip
import json
from pathlib import Path
from types import NoneType
from typing import Any, cast, Type

import bpy
import tomllib

from .common import (
    BLENDER_VERSION,
    DATA,
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
)


class Pointer:
    def __init__(
        self,
        *,
        obj: bpy.types.bpy_struct,
        identifier: str,
        pointer_id: int,
        from_root: FromRoot,
    ) -> None:
        self.obj = obj
        self.identifier = identifier
        self.from_root = from_root
        self.pointer_id = pointer_id
        # this is determined after all trees are serialized
        self.pointee_id = None


class Exporter:
    def __init__(
        self,
        *,
        specific_handlers: dict[type, SERIALIZER],
        skip_defaults: bool,
        write_from_roots: bool,
        debug_prints: bool,
    ) -> None:
        self.next_id = 0
        self.specific_handlers = specific_handlers
        self.skip_defaults = skip_defaults
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
            data_prop = self._export_property_simple(
                obj=obj,
                prop=prop,  # type: ignore
                from_root=from_root.add_prop(prop),
            )
            if data_prop is not None:
                data[prop.identifier] = data_prop
        return data

    def export_properties_from_id_list(
        self,
        *,
        obj: bpy.types.bpy_struct,
        properties: list[str],
        from_root: FromRoot,
    ) -> dict[str, Any]:
        data = {}
        for prop in [obj.bl_rna.properties[p] for p in properties]:
            data_prop = self._export_property(
                obj=obj,
                prop=prop,
                from_root=from_root.add_prop(prop),
            )
            if data_prop is not None:
                data[prop.identifier] = data_prop
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
    ) -> None | SIMPLE_DATA_TYPE:
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting simple")

        assert prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS

        # we do need to export bl_idname for nodes and tree so we can construct them
        bl_idname_exception = (
            isinstance(obj, (bpy.types.Node, bpy.types.NodeTree))
            and prop.identifier == "bl_idname"
        )
        if prop.identifier in FORBIDDEN_PROPERTIES and not bl_idname_exception:
            if self.debug_prints:
                print(f"{from_root.to_str()}: forbidden")
            return None

        attribute = getattr(obj, prop.identifier)
        if prop.type in ["BOOLEAN", "INT", "FLOAT"]:
            assert isinstance(
                prop,
                (
                    bpy.types.BoolProperty,
                    bpy.types.IntProperty,
                    bpy.types.FloatProperty,
                ),
            )

            if prop.is_array:
                if self.skip_defaults and prop.default_array == attribute:
                    if self.debug_prints:
                        print(f"{from_root.to_str()}: skipping default")
                    return None
                return list(attribute)

        if prop.type == "ENUM":
            assert isinstance(prop, bpy.types.EnumProperty)

            if prop.is_enum_flag:
                if self.skip_defaults and prop.default_flag == attribute:
                    if self.debug_prints:
                        print(f"{from_root.to_str()}: skipping default")
                    return None
                assert isinstance(attribute, set)
                return list(attribute)

        if self.skip_defaults and prop.default == attribute:
            if self.debug_prints:
                print(f"{from_root.to_str()}: skipping default")
            return None
        return attribute

    def _export_property_pointer(
        self,
        *,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.PointerProperty,
        from_root: FromRoot,
    ) -> None | Pointer | dict[str, Any]:
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting pointer")

        assert prop.type == "POINTER"

        attribute = getattr(obj, prop.identifier)

        if attribute is None:
            if self.debug_prints:
                print(f"{from_root.to_str()}: skipping not set")
            return None

        if attribute.id_data == self.current_tree and prop.is_readonly:
            return self._export_obj(obj=attribute, from_root=from_root)
        else:
            pointer = Pointer(
                obj=obj,
                identifier=prop.identifier,
                pointer_id=self.next_id - 1,
                from_root=from_root,
            )
            self.pointers.setdefault(attribute, []).append(pointer)
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

        assert prop.type == "COLLECTION"

        attribute = getattr(obj, prop.identifier)

        data = self._export_obj(obj=attribute, from_root=from_root)
        items = [
            self._export_obj(
                obj=element,
                from_root=from_root.add(
                    f"[{i}] ({getattr(attribute[i], 'name', 'unnamed')})"
                ),
            )
            for i, element in enumerate(attribute)
        ]
        no_clobber(data[DATA], "items", items)

        return data

    def _export_property(
        self,
        *,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        from_root: FromRoot,
    ) -> None | SIMPLE_DATA_TYPE | Pointer | dict[str, Any]:
        if prop.type in SIMPLE_PROPERTY_TYPES_AS_STRS:
            return self._export_property_simple(
                obj=obj,
                prop=prop,  # type: ignore
                from_root=from_root,
            )
        elif prop.type == "POINTER":
            assert isinstance(prop, bpy.types.PointerProperty)
            return self._export_property_pointer(
                obj=obj,
                prop=prop,
                from_root=from_root,
            )
        elif prop.type == "COLLECTION":
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
            return None

        if prop.type == "POINTER":
            if prop.is_readonly and attribute.id_data != self.current_tree:
                error_out("readonly pointer to external")
            return self._export_property_pointer(
                obj=obj,
                prop=cast(bpy.types.PointerProperty, prop),
                from_root=from_root,
            )

        if prop.type == "COLLECTION":
            prop = cast(bpy.types.CollectionProperty, prop)
            if (
                hasattr(attribute, "bl_rna")
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

        if obj in self.serialized:
            raise RuntimeError(f"Double serialization: {from_root.to_str()}")
        self.serialized[obj] = this_id

        data = {
            ID: this_id,
            DATA: serializer(self, obj, from_root),
        }
        if self.write_from_roots:
            data["from_root"] = from_root.to_str()
        return data

    def _export_obj(
        self,
        *,
        obj: bpy.types.bpy_struct,
        from_root: FromRoot,
    ) -> dict[str, Any]:
        # edge case for things like bpy_prop_collection that aren't real RNA types?
        # https://projects.blender.org/blender/blender/issues/150092
        if not hasattr(obj, "bl_rna"):
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
            and prop.identifier not in ["rna_type"]
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
                if prop_data is not None:
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
        if isinstance(node, bpy.types.GeometryNodeGroup) and node.node_tree is not None:
            tree = node.node_tree
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
        skip_defaults: bool = True,
        debug_prints: bool,
        write_from_roots: bool,
    ) -> None:
        self.is_material = is_material
        self.name = name
        self.specific_handlers = specific_handlers
        self.export_sub_trees = export_sub_trees
        self.skip_defaults = skip_defaults
        self.debug_prints = debug_prints
        self.write_from_roots = write_from_roots


class External:
    def __init__(
        self,
        *,
        pointed_to_by: list[Pointer],
    ) -> None:
        self.pointed_to_by = pointed_to_by
        self.description = None


def _export_nodes_to_dict(parameters: ExportParameters) -> dict[str, Any]:
    exporter = Exporter(
        specific_handlers=parameters.specific_handlers,
        skip_defaults=parameters.skip_defaults,
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
            external_id = exporter.next_id
            exporter.next_id += 1
            external[external_id] = External(pointed_to_by=pointers)
            for pointer in pointers:
                pointer.pointee_id = external_id

    data["external"] = external

    return data


class _Encoder(json.JSONEncoder):
    def default(self, obj) -> int | str | Any:
        if isinstance(obj, Pointer):
            return obj.pointee_id
        if isinstance(obj, External):
            return obj.description
        return super().default(obj)


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
        return self.data["external"]
