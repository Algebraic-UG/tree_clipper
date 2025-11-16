import bpy

from uuid import uuid4
from types import NoneType
from typing import Callable, Self

import tomllib
import json
from pathlib import Path

from .common import (
    PROPERTY_TYPES_SIMPLE,
    BLENDER_VERSION,
    NODES_AS_JSON_VERSION,
    MATERIAL_NAME,
    TREES,
    no_clobber,
    FromRoot,
)


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
        specific_handlers: dict,
        skip_defaults: bool,
        debug_prints: bool,
    ):
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
        assumed_type: type,
        prop: bpy.types.Property,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        assert prop.type in PROPERTY_TYPES_SIMPLE
        assert any(
            prop.identifier == p.identifier for p in assumed_type.bl_rna.properties
        )

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
        assumed_type: type,
        prop: bpy.types.PointerProperty,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        assert prop.type == "POINTER"
        assert any(
            prop.identifier == p.identifier for p in assumed_type.bl_rna.properties
        )

        attribute = getattr(obj, prop.identifier)

        if attribute is None:
            return None

        if attribute.id_data == self.current_tree:
            return self._export_obj(attribute, from_root)
        else:
            d = {}
            self.pointers.setdefault(attribute.as_pointer(), []).append(
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
        assumed_type: type,
        prop: bpy.types.CollectionProperty,
        from_root: FromRoot,
    ):
        if self.debug_prints:
            print(from_root.to_str())

        assert prop.type == "COLLECTION"
        assert any(
            prop.identifier == p.identifier for p in assumed_type.bl_rna.properties
        )

        attribute = getattr(obj, prop.identifier)

        return [
            self._export_obj(element, from_root.add(f"[{i}]"))
            for i, element in enumerate(attribute)
        ]

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
                assumed_type,
                prop,
                from_root.add_prop(prop),
            )
            if d_prop is not None:
                d[prop.identifier] = d_prop
        return d

    def export_property(
        self,
        obj: bpy.types.bpy_struct,
        assumed_type: type,
        prop: bpy.types.Property,
        from_root: FromRoot,
    ):
        if prop.type in PROPERTY_TYPES_SIMPLE:
            return self.export_property_simple(obj, assumed_type, prop, from_root)
        elif prop.type == "POINTER":
            return self.export_property_pointer(obj, assumed_type, prop, from_root)
        elif prop.type == "COLLECTION":
            return self.export_property_collection(obj, assumed_type, prop, from_root)
        else:
            raise RuntimeError(f"Unknown property type: {prop.type}")

    def export_properties_from_id_list(
        self,
        obj: bpy.types.bpy_struct,
        assumed_type: type,
        properties: list,
        from_root: FromRoot,
    ):
        d = {}
        for prop in [obj.bl_rna.properties[p] for p in properties]:
            d_prop = self.export_property(
                obj,
                assumed_type,
                prop,
                from_root.add_prop(prop),
            )
            if d_prop is not None:
                d[prop.identifier] = d_prop
        return d

    ################################################################################
    # internals
    ################################################################################

    def _attempt_default_serialization_for_prop(
        self,
        obj: bpy.types.bpy_struct,
        prop: bpy.types.Property,
        from_root,
    ):
        def error_out(reason: str, prop_from_root: FromRoot):
            raise RuntimeError(
                f"""\
More specific handler needed for type: {type(obj)}
Reason: {reason}
From root: {prop_from_root.to_str()}"""
            )

        if prop.type in PROPERTY_TYPES_SIMPLE:
            if prop.is_readonly:
                return None
            return self.export_property_simple(obj, type(obj), prop, from_root)

        attribute = getattr(obj, prop.identifier)
        if attribute is None:
            return None

        if prop.type == "POINTER":
            if prop.is_readonly and attribute.id_data != self.current_tree:
                error_out("readonly pointer to external", from_root)
            return self.export_property_pointer(obj, type(obj), prop, from_root)

        if prop.type == "COLLECTION":
            if (
                hasattr(attribute, "bl_rna")
                and any(len(f.parameters) != 0 for f in attribute.bl_rna.functions)
                and type(prop.fixed_type) not in self.specific_handlers
            ):
                error_out(
                    "collection with function that requires args and the elements aren't specifically handled",
                    from_root,
                )
            return self.export_property_collection(obj, type(obj), prop, from_root)

        raise RuntimeError(f"Unknown property type: {prop.type}")

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
        self.serialized[obj.as_pointer()] = {}

        d = serializer(self, obj, from_root)
        self.serialized[obj.as_pointer()] = d

        return d

    def _most_specific_type_handled(self, t: type):
        while True:
            if t in self.specific_handlers:
                return t
            if len(t.__bases__) == 0:
                return NoneType
            if len(t.__bases__) > 1:
                raise RuntimeError(f"multiple inheritence {t}, unclear what to choose")
            t = t.__bases__[0]

    def _export_obj(self, obj: bpy.types.bpy_struct, from_root: FromRoot):
        assumed_type = self._most_specific_type_handled(type(obj))
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
                prop_d = exporter._attempt_default_serialization_for_prop(
                    obj, prop, from_root.add_prop(prop)
                )
                if prop_d is not None:
                    no_clobber(d, prop.identifier, prop_d)

            return d

        return self._export_obj_with_serializer(obj, _serializer, from_root)

    def _export_node_tree(self, node_tree: bpy.types.NodeTree, from_root: FromRoot):
        if self.debug_prints:
            print(from_root.to_str())

        self.current_tree = node_tree
        d = self._export_obj(node_tree, from_root)
        self.current_tree = None

        return d


def _collect_sub_trees(
    current: bpy.types.NodeTree,
    trees: list,
    from_root: FromRoot,
):
    for node in current.nodes:
        if hasattr(node, "node_tree"):
            tree = node.node_tree
            if all(tree != already_in[0] for already_in in trees):
                sub_root = from_root.add(f"Group ({node.name})")
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
    specific_handlers: dict = {},
    export_sub_trees: bool = True,
    skip_defaults: bool = True,
):
    exporter = Exporter(
        specific_handlers=specific_handlers,
        skip_defaults=skip_defaults,
        debug_prints=True,
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
        NODES_AS_JSON_VERSION: blender_manifest["version"],
        # pylint: disable=protected-access
        TREES: [
            # pylint: disable=protected-access
            exporter._export_node_tree(tree, from_root)
            for (tree, from_root) in trees
        ],
    }

    if is_material:
        d[MATERIAL_NAME] = name

    for ptr, pointers_to_same in exporter.pointers.items():
        if ptr in exporter.serialized:
            uuid = str(uuid4())
            exporter.serialized[ptr]["nodes_as_json_uuid"] = uuid
            for pointer in pointers_to_same:
                pointer.in_serialization["serialized_as"] = uuid
        else:
            # TODO
            pass

    with Path(output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))
