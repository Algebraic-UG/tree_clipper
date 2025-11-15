from typing import Callable, Self
import bpy


import tomllib
import json
from pathlib import Path

from .common import (
    PROPERTY_TYPES_SIMPLE,
    BLENDER_VERSION,
    NODES_AS_JSON_VERSION,
    ROOT,
    SUB_TREES,
    MATERIAL_NAME,
)


class FromRoot:
    def __init__(self, path: list):
        self.path = path

    def add(self, piece: str):
        return FromRoot(self.path + [piece])

    def add_prop(self, prop: bpy.types.Property):
        return self.add(f"{prop.type} ({prop.name})")

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

    def export_all_simple_writable_properties(
        self,
        obj: bpy.types.bpy_struct,
        from_root: FromRoot,
    ):
        d = {}
        for prop in obj.bl_rna.properties:
            if prop.is_readonly or prop.type not in PROPERTY_TYPES_SIMPLE:
                continue
            d_prop = self.export_property_simple(obj, prop, from_root.add_prop(prop))
            if d_prop is not None:
                d[prop.identifier] = d_prop
        return d

    def export_properties_from_list(
        self,
        obj: bpy.types.bpy_struct,
        properties: list,
        from_root: FromRoot,
    ):
        d = {}
        for prop in [obj.bl_rna.properties[p] for p in properties]:
            prop_from_root = from_root.add_prop(prop)
            if prop.type in PROPERTY_TYPES_SIMPLE:
                d_prop = self.export_property_simple(obj, prop, prop_from_root)
            elif prop.type == "POINTER":
                d_prop = self.export_property_pointer(obj, prop, prop_from_root)
            elif prop.type == "COLLECTION":
                d_prop = self.export_property_collection(obj, prop, prop_from_root)
            else:
                raise RuntimeError(f"Unknown property type: {prop.type}")
            if d_prop is not None:
                d[prop.identifier] = d_prop
        return d

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

    def _export_obj(self, obj: bpy.types.bpy_struct, from_root: FromRoot):
        return self._export_obj_with_serializer(
            obj,
            self.special_handlers.get(type(obj), _default_obj_serializer),
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
        prop_from_root = from_root.add_prop(prop)

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
