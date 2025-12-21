import deepdiff
import json
from pathlib import Path
from typing import Literal
import bpy

from tree_clipper.common import (
    EXTERNAL_FIXED_TYPE_NAME,
    EXTERNAL_DESCRIPTION,
    EXTERNAL_SERIALIZATION,
    DATA,
    MATERIAL_NAME,
    TREES,
    NAME,
)
from tree_clipper.id_data_getter import get_data_block_from_id_name
from tree_clipper.export_nodes import ExportIntermediate, ExportParameters
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters, ImportReport
from tree_clipper.specific_handlers import BUILT_IN_EXPORTER, BUILT_IN_IMPORTER


def make_test_object() -> bpy.types.Object:
    obj = bpy.data.objects.new(name="test", object_data=None)
    bpy.context.scene.collection.objects.link(  # ty :ignore[possibly-missing-attribute]
        obj
    )
    return obj


def make_test_collection() -> bpy.types.Collection:
    collection = bpy.data.collections.new(name="test")
    bpy.context.scene.collection.children.link(  # ty :ignore[possibly-missing-attribute]
        collection
    )
    return collection


def make_test_node_tree(
    name: str = "test",
    ty: Literal[
        "GeometryNodeTree",
        "CompositorNodeTree",
        "ShaderNodeTree",
        "TextureNodeTree",
    ] = "GeometryNodeTree",
) -> bpy.types.NodeTree:
    tree = bpy.data.node_groups.new(name=name, type=ty)
    tree.use_fake_user = True  # otherwise it might not be in the save file
    if isinstance(tree, bpy.types.GeometryNodeTree):
        tree.is_modifier = True  # makes it easier to inspect
    return tree


def save_failed(name: str):
    test_failures = Path("test_failures")
    test_failures.mkdir(exist_ok=True)
    path = str(test_failures / f"{name}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)


def diff_exports(
    *,
    before: str,
    import_report: ImportReport,
    after: str,
):
    data_before = json.loads(before)
    data_after = json.loads(after)

    # we need to make sure that we "fix" the names as they're expected to change on import
    if import_report.rename_material is not None:
        original_name, new_name = import_report.rename_material
        data_after[MATERIAL_NAME] = original_name
    for original_name, new_name in import_report.renames_node_group.items():
        tree = next(tree for tree in data_after[TREES] if tree[DATA][NAME] == new_name)
        tree[DATA][NAME] = original_name

    diff = deepdiff.DeepDiff(data_before, data_after, math_epsilon=0.01)

    print(diff.pretty())
    assert diff == {}


def round_trip_without_external(original_name: str):
    def export_to_string(name: str) -> str:
        export_intermediate = ExportIntermediate(
            parameters=ExportParameters(
                is_material=False,
                name=name,
                specific_handlers=BUILT_IN_EXPORTER,
                export_sub_trees=True,
                debug_prints=True,
                write_from_roots=False,
            )
        )

        string = export_intermediate.export_to_str(compress=False, json_indent=4)
        print(string)
        return string

    before = export_to_string(original_name)

    import_intermediate = ImportIntermediate()
    import_intermediate.from_str(before)
    import_report = import_intermediate.import_nodes(
        parameters=ImportParameters(
            specific_handlers=BUILT_IN_IMPORTER,
            debug_prints=True,
        )
    )

    after = export_to_string(import_report.renames_node_group[original_name])

    diff_exports(before=before, import_report=import_report, after=after)


def round_trip(
    *,
    original_name: str,
    is_material: bool,
    debug_prints: bool = False,
):
    def export_to_string(name: str) -> str:
        export_intermediate = ExportIntermediate(
            parameters=ExportParameters(
                is_material=is_material,
                name=name,
                specific_handlers=BUILT_IN_EXPORTER,
                export_sub_trees=True,
                debug_prints=debug_prints,
                write_from_roots=False,
            )
        )

        export_intermediate.set_external(
            (
                external_id,
                external_item.pointed_to_by.get_pointee().name,  # ty: ignore[possibly-missing-attribute]
            )
            for external_id, external_item in export_intermediate.get_external().items()
        )

        string = export_intermediate.export_to_str(compress=False, json_indent=4)
        if debug_prints:
            print(string)
        return string

    before = export_to_string(original_name)

    import_intermediate = ImportIntermediate()
    import_intermediate.from_str(before)

    def get_same_external_item(external_item: EXTERNAL_SERIALIZATION):
        fixed_type_name = external_item[EXTERNAL_FIXED_TYPE_NAME]
        assert isinstance(fixed_type_name, str)
        data_block = get_data_block_from_id_name(fixed_type_name)
        name = external_item[EXTERNAL_DESCRIPTION]
        return data_block[name]  # ty: ignore[invalid-argument-type]

    import_intermediate.set_external(
        (int(external_id), get_same_external_item(external_item))
        for external_id, external_item in import_intermediate.get_external().items()
    )

    import_report = import_intermediate.import_nodes(
        parameters=ImportParameters(
            specific_handlers=BUILT_IN_IMPORTER,
            debug_prints=debug_prints,
        )
    )

    after = export_to_string(
        import_report.rename_material[1]  # ty:ignore[non-subscriptable]
        if is_material
        else import_report.renames_node_group[original_name]
    )

    diff_exports(before=before, import_report=import_report, after=after)


def make_everything_local():
    for node_group in bpy.data.node_groups:
        if node_group.library:
            node_group.make_local(clear_liboverride=True)

    for material in bpy.data.materials:
        if material.library:
            material.make_local(clear_liboverride=True)


BINARY_BLEND_FILES_DIR = Path(__file__).parent / "binary_blend_files"
