import bpy

import base64
import gzip

from types import NoneType
from typing import Any, Callable, Self

import tomllib
import json
from pathlib import Path

from .common import (
    DATA,
    ID,
    PROPERTY_TYPES_SIMPLE,
    BLENDER_VERSION,
    TREE_CLIPPER_VERSION,
    MATERIAL_NAME,
    TREES,
    most_specific_type_handled,
    no_clobber,
    FromRoot,
)


class Pointer:
    def __init__(
        self,
        *,
        from_root: FromRoot,
    ):
        self.from_root = from_root
        self.id = None


# Any is actually the exporter below
SERIALIZER = Callable[[Any, bpy.types.bpy_struct, FromRoot], dict]


class Exporter:
    def __init__(
        self,
        *,
        specific_handlers: dict[type, SERIALIZER],
        skip_defaults: bool,
        debug_prints: bool,
    ):
        self.next_id = 0
        self.specific_handlers = specific_handlers
        self.skip_defaults = skip_defaults
        self.debug_prints = debug_prints
        self.pointers = {}
        self.serialized = {}
        self.current_tree = None

    ################################################################################
    # helper functions to be used in specific handlers
    ################################################################################

    def export_property_simple(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting simple")

        assert prop.type in PROPERTY_TYPES_SIMPLE

        attribute = getattr(obj, prop.identifier)

        if prop.type in ["BOOLEAN", "INT", "FLOAT"]:
            if prop.is_array:
                if self.skip_defaults and prop.default_array == attribute:
                    if self.debug_prints:
                        print(f"{from_root.to_str()}: skipping default")
                    return None
                return list(attribute)

        if self.skip_defaults and prop.default == attribute:
            if self.debug_prints:
                print(f"{from_root.to_str()}: skipping default")
            return None
        return attribute

    def export_property_pointer(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.PointerProperty,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting pointer")

        assert prop.type == "POINTER"

        attribute = getattr(obj, prop.identifier)

        if attribute is None:
            if self.debug_prints:
                print(f"{from_root.to_str()}: skipping not set")
            return None

        if attribute.id_data == self.current_tree and prop.is_readonly:
            return self._export_obj(attribute, from_root)
        else:
            pointer = Pointer(from_root=from_root)
            self.pointers.setdefault(attribute, []).append(pointer)
            if self.debug_prints:
                print(f"{from_root.to_str()}: deferring")
            return pointer

    def export_property_collection(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.CollectionProperty,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting collection")

        assert prop.type == "COLLECTION"

        attribute = getattr(obj, prop.identifier)

        d = self._export_obj(attribute, from_root)
        items = [
            self._export_obj(element, from_root.add(f"[{i}]"))
            for i, element in enumerate(attribute)
        ]
        no_clobber(d[DATA], "items", items)

        return d

    def export_all_simple_writable_properties(
        self,
        obj: bpy.types.bpy_struct,
        assumed_type: type,
        from_root: FromRoot,
    ):
        d = {}
        for prop in assumed_type.bl_rna.properties:
            if prop.is_readonly or prop.type not in PROPERTY_TYPES_SIMPLE:
                continue
            d_prop = self.export_property_simple(
                obj,
                prop,
                from_root.add_prop(prop),
            )
            if d_prop is not None:
                d[prop.identifier] = d_prop
        return d

    def export_property(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        from_root: FromRoot,
    ):
        if prop.type in PROPERTY_TYPES_SIMPLE:
            return self.export_property_simple(obj, prop, from_root)
        elif prop.type == "POINTER":
            return self.export_property_pointer(obj, prop, from_root)
        elif prop.type == "COLLECTION":
            return self.export_property_collection(obj, prop, from_root)
        else:
            raise RuntimeError(f"Unknown property type: {prop.type}")

    def export_properties_from_id_list(
        self,
        obj: bpy.types.bpy_struct,
        properties: list[str],
        from_root: FromRoot,
    ):
        d = {}
        for prop in [obj.bl_rna.properties[p] for p in properties]:
            d_prop = self.export_property(
                obj,
                prop,
                from_root.add_prop(prop),
            )
            if d_prop is not None:
                d[prop.identifier] = d_prop
        return d

    ################################################################################
    # internals
    ################################################################################

    def _attempt_export_property(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        from_root,
    ):
        def error_out(reason: str):
            raise RuntimeError(
                f"""\
More specific handler needed for type: {type(obj)}
Reason: {reason}
From root: {from_root.to_str()}"""
            )

        if prop.type in PROPERTY_TYPES_SIMPLE:
            if prop.is_readonly:
                return None
            return self.export_property_simple(obj, prop, from_root)

        attribute = getattr(obj, prop.identifier)
        if attribute is None:
            return None

        if prop.type == "POINTER":
            if prop.is_readonly and attribute.id_data != self.current_tree:
                error_out("readonly pointer to external")
            return self.export_property_pointer(obj, prop, from_root)

        if prop.type == "COLLECTION":
            if (
                hasattr(attribute, "bl_rna")
                and any(len(f.parameters) != 0 for f in attribute.bl_rna.functions)
                and type(prop.fixed_type) not in self.specific_handlers
            ):
                error_out(
                    "collection with function that requires args and the elements aren't specifically handled"
                )
            return self.export_property_collection(obj, prop, from_root)

        raise RuntimeError(f"Unknown property type: {prop.type}")

    def _export_obj_with_serializer(
        self,
        obj: bpy.types.bpy_struct,
        serializer: SERIALIZER,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(f"{from_root.to_str()}: exporting")

        this_id = self.next_id
        self.next_id += 1

        if obj in self.serialized:
            raise RuntimeError(f"Double serialization: {from_root.to_str()}")
        self.serialized[obj] = this_id

        return {ID: this_id, DATA: serializer(self, obj, from_root)}

    def _export_obj(self, obj: bpy.types.bpy_struct, from_root: FromRoot):
        # edge case for things like bpy_prop_collection that aren't real RNA types?
        if not hasattr(obj, "bl_rna"):
            assert isinstance(obj, bpy.types.bpy_prop_collection)
            return self._export_obj_with_serializer(
                obj, self.specific_handlers[NoneType], from_root
            )

        assumed_type = most_specific_type_handled(self.specific_handlers, obj)
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

        def _serializer(exporter: Self, obj: bpy.types.bpy_struct, from_root: FromRoot):
            d = specific_handler(exporter, obj, from_root)
            for prop in unhandled_properties:
                # pylint: disable=protected-access
                prop_d = exporter._attempt_export_property(
                    obj, prop, from_root.add_prop(prop)
                )
                if prop_d is not None:
                    no_clobber(d, prop.identifier, prop_d)

            return d

        return self._export_obj_with_serializer(obj, _serializer, from_root)

    def _export_node_tree(self, node_tree: bpy.types.NodeTree, from_root: FromRoot):
        if self.debug_prints:
            print(f"{from_root.to_str()}: entering")

        self.current_tree = node_tree
        d = self._export_obj(node_tree, from_root)
        self.current_tree = None

        return d


def _collect_sub_trees(
    current: bpy.types.NodeTree,
    trees: list[(bpy.types.NodeTree, FromRoot)],
    from_root: FromRoot,
):
    for node in current.nodes:
        if hasattr(node, "node_tree"):
            tree = node.node_tree
            if all(tree != already_in[0] for already_in in trees):
                sub_root = from_root.add(f"Group ({node.name}, {tree.name})")
                trees.append((tree, sub_root))
                _collect_sub_trees(tree, trees, sub_root)


################################################################################
# entry point
################################################################################


def export_nodes(
    *,
    is_material: bool,
    name: str,
    output_file: str,
    specific_handlers: dict[type, SERIALIZER],
    export_sub_trees: bool = True,
    skip_defaults: bool = True,
    debug_prints: bool
):
    exporter = Exporter(
        specific_handlers=specific_handlers,
        skip_defaults=skip_defaults,
        debug_prints=debug_prints,
    )

    if is_material:
        from_root = FromRoot([f"Material ({name})"])
        root = bpy.data.materials[name].node_tree
    else:
        from_root = FromRoot([f"Root ({name})"])
        root = bpy.data.node_groups[name]

    trees = [(root, from_root)]
    if export_sub_trees:
        _collect_sub_trees(root, trees, from_root)

    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        blender_manifest = tomllib.load(f)

    d = {
        BLENDER_VERSION: bpy.app.version_string,
        TREE_CLIPPER_VERSION: blender_manifest["version"],
        TREES: [
            # pylint: disable=protected-access
            exporter._export_node_tree(tree, from_root)
            for (tree, from_root) in trees
        ],
    }

    if is_material:
        d[MATERIAL_NAME] = name

    for obj, pointers in exporter.pointers.items():
        if obj in exporter.serialized:
            for pointer in pointers:
                pointer.id = exporter.serialized[obj]
        else:
            # TODO
            pass

    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Pointer):
                return obj.id
            return super().default(obj)

    with Path(output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, cls=Encoder, indent=4))

        # json_str = json.dumps(d, cls=Encoder)
        # gzipped = gzip.compress(json_str.encode("utf-8"))
        # base64_str = base64.b64encode(gzipped).decode("utf-8")

        # f.write(base64_str)
