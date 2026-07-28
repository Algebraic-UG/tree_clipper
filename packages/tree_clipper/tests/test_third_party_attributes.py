import bpy
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters
from tree_clipper.specific_handlers import BUILT_IN_EXPORTER, BUILT_IN_IMPORTER

from .util import (
    diff_exports,
    export_to_string,
    make_test_node_tree,
    round_trip_without_external,
)


# just to pick any node that isn't specifically handled
# that is the "worst case" scenario
def test_third_party_node_type_to_test():
    assert bpy.types.NodeGroupInput not in BUILT_IN_EXPORTER
    assert bpy.types.NodeGroupInput not in BUILT_IN_IMPORTER


class TreeClipperTest(bpy.types.PropertyGroup):
    foo: bpy.props.StringProperty()  # ty:ignore


def register_third_party_properties():
    # simple properties
    bpy.types.NodeGroupInput.tree_clipper_test_bool = bpy.props.BoolProperty()
    bpy.types.NodeGroupInput.tree_clipper_test_enum = bpy.props.EnumProperty(
        items=[("foo",) * 3]
    )
    bpy.types.NodeGroupInput.tree_clipper_test_float = bpy.props.FloatProperty()
    bpy.types.NodeGroupInput.tree_clipper_test_int = bpy.props.IntProperty()
    bpy.types.NodeGroupInput.tree_clipper_test_string = bpy.props.StringProperty()

    # pointer property
    bpy.utils.register_class(TreeClipperTest)
    bpy.types.NodeGroupInput.tree_clipper_test_pointer = bpy.props.PointerProperty(
        type=TreeClipperTest
    )

    # collection property
    bpy.types.NodeGroupInput.tree_clipper_test_collection = (
        bpy.props.CollectionProperty(type=TreeClipperTest)
    )


def unregister_third_party_properties():
    del bpy.types.NodeGroupInput.tree_clipper_test_bool
    del bpy.types.NodeGroupInput.tree_clipper_test_enum
    del bpy.types.NodeGroupInput.tree_clipper_test_float
    del bpy.types.NodeGroupInput.tree_clipper_test_int
    del bpy.types.NodeGroupInput.tree_clipper_test_string
    del bpy.types.NodeGroupInput.tree_clipper_test_pointer
    del bpy.types.NodeGroupInput.tree_clipper_test_collection

    bpy.utils.unregister_class(TreeClipperTest)


def test_third_party_both_have_it():
    try:
        register_third_party_properties()

        tree = make_test_node_tree()
        tree.nodes.new("NodeGroupInput")

        round_trip_without_external(tree.name)

    finally:
        unregister_third_party_properties()


def test_third_party_only_exporter_has_it():
    try:
        register_third_party_properties()

        tree = make_test_node_tree()
        tree.nodes.new("NodeGroupInput")
        original_name = tree.name

        before = export_to_string(original_name)

        unregister_third_party_properties()

        import_intermediate = ImportIntermediate(string=before)
        import_report = import_intermediate.import_all(
            parameters=ImportParameters(
                specific_handlers=BUILT_IN_IMPORTER,
                debug_prints=True,
            )
        )

        after = export_to_string(import_report.renames_node_group[original_name])

        try:
            diff_exports(before=before, import_report=import_report, after=after)
            assert False, "diff should be the properties"
        except AssertionError:
            pass

        register_third_party_properties()
    finally:
        unregister_third_party_properties()


def test_third_party_only_impoter_has_it():
    try:
        tree = make_test_node_tree()
        tree.nodes.new("NodeGroupInput")
        original_name = tree.name

        before = export_to_string(original_name)

        register_third_party_properties()

        import_intermediate = ImportIntermediate(string=before)
        import_report = import_intermediate.import_all(
            parameters=ImportParameters(
                specific_handlers=BUILT_IN_IMPORTER,
                debug_prints=True,
            )
        )

        after = export_to_string(import_report.renames_node_group[original_name])

        try:
            diff_exports(before=before, import_report=import_report, after=after)
            assert False, "diff should be the properties"
        except AssertionError:
            pass

    finally:
        unregister_third_party_properties()
