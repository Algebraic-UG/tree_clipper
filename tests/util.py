import bpy

from tree_clipper.export_nodes import ExportIntermediate, ExportParameters
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters
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


def make_test_node_tree(name: str = "test") -> bpy.types.NodeTree:
    tree = bpy.data.node_groups.new(name=name, type="GeometryNodeTree")
    tree.use_fake_user = True
    tree.is_modifier = True  # ty: ignore[unresolved-attribute]
    return tree


def round_trip_without_external(name: str):
    export_intermediate = ExportIntermediate(
        parameters=ExportParameters(
            is_material=False,
            name=name,
            specific_handlers=BUILT_IN_EXPORTER,
            export_sub_trees=True,
            skip_defaults=True,
            debug_prints=True,
            write_from_roots=False,
        )
    )

    string = export_intermediate.export_to_str(compress=False, json_indent=4)
    print(string)

    import_intermediate = ImportIntermediate()
    import_intermediate.from_str(string)
    import_intermediate.import_nodes(
        parameters=ImportParameters(
            specific_handlers=BUILT_IN_IMPORTER,
            allow_version_mismatch=False,
            overwrite=True,
            debug_prints=True,
        )
    )
