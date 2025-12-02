from tests.util import make_test_object, make_test_collection, make_test_node_tree
import bpy

from typing import Callable

from tree_clipper.common import EXTERNAL_SERIALIZATION
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters

from tree_clipper.specific_handlers import BUILT_IN_EXPORTER, BUILT_IN_IMPORTER
from tree_clipper.export_nodes import ExportIntermediate, ExportParameters, External


_EXTERNAL_ITEM_MAKER: dict[str, Callable[[], bpy.types.ID]] = {
    "Image": lambda: bpy.data.images.new(name="test", width=10, height=10),
    "Material": lambda: bpy.data.materials.new(name="test"),
    "Text": lambda: bpy.data.texts.new(name="test"),
    "Annotation": lambda: bpy.data.annotations.new(name="test"),
    # special: they can cause something like ERROR ID user decrement error: GRtest (from '[Main]'): 0 <= 0
    "Object": make_test_object,
    "Collection": make_test_collection,
    "NodeTree": make_test_node_tree,
}


def _create_setup():
    tree = make_test_node_tree()

    tree.annotation = _EXTERNAL_ITEM_MAKER["Annotation"]()  # ty: ignore[invalid-assignment]

    name = tree.name
    nodes = tree.nodes

    node = nodes.new("GeometryNodeGroup")
    node.node_tree = _EXTERNAL_ITEM_MAKER["NodeTree"]()  # ty: ignore[invalid-assignment, unresolved-attribute]

    node = nodes.new("GeometryNodeInputObject")
    node.object = _EXTERNAL_ITEM_MAKER["Object"]()  # ty: ignore[invalid-assignment, unresolved-attribute]

    node = nodes.new("GeometryNodeInputImage")
    node.image = _EXTERNAL_ITEM_MAKER["Image"]()  # ty: ignore[invalid-assignment, unresolved-attribute]

    node = nodes.new("GeometryNodeInputMaterial")
    node.material = _EXTERNAL_ITEM_MAKER["Material"]()  # ty: ignore[invalid-assignment, unresolved-attribute]

    node = nodes.new("GeometryNodeInputCollection")
    node.collection = _EXTERNAL_ITEM_MAKER["Collection"]()  # ty: ignore[invalid-assignment, unresolved-attribute]

    node = nodes.new("NodeFrame")
    node.text = _EXTERNAL_ITEM_MAKER["Text"]()  # ty: ignore[invalid-assignment, unresolved-attribute]

    return name


def _check_before_export(external_items: list[External]):
    for external_item in external_items:
        prop = external_item.pointed_to_by.obj.bl_rna.properties[
            external_item.pointed_to_by.identifier
        ]
        assert isinstance(prop, bpy.types.PointerProperty)

        obj = getattr(
            external_item.pointed_to_by.obj,
            external_item.pointed_to_by.identifier,
        )
        assert isinstance(obj, bpy.types.ID)

        assert prop.fixed_type is not None
        assert (
            prop.fixed_type.bl_rna.identifier  # ty: ignore[unresolved-attribute]
            == external_item.pointed_to_by.fixed_type_name
        )

    for expected_external_type in _EXTERNAL_ITEM_MAKER.keys():
        assert (
            len(
                [
                    external_item
                    for external_item in external_items
                    if external_item.pointed_to_by.fixed_type_name
                    == expected_external_type
                ]
            )
            == 1
        )


def _make_some_description(fixed_type_name: str) -> str:
    return f"Set to a thing you have in your scene with type: {fixed_type_name}"


def _check_before_import(external_items: list[EXTERNAL_SERIALIZATION]):
    for external_item in external_items:
        assert external_item["description"] == _make_some_description(
            external_item["fixed_type_name"]  # ty: ignore[invalid-argument-type]
        )

    for expected_external_type in _EXTERNAL_ITEM_MAKER.keys():
        assert (
            len(
                [
                    external_item
                    for external_item in external_items
                    if external_item["fixed_type_name"] == expected_external_type
                ]
            )
            == 1
        )


def _check_after_import(name: str):
    tree = bpy.data.node_groups[name]
    assert tree.annotation is not None
    assert tree.nodes["Group"].node_tree is not None  # ty: ignore[unresolved-attribute]
    assert tree.nodes["Frame"].text is not None  # ty: ignore[unresolved-attribute]
    assert tree.nodes["Image"].image is not None  # ty: ignore[unresolved-attribute]
    assert tree.nodes["Material"].material is not None  # ty: ignore[unresolved-attribute]
    assert tree.nodes["Object"].object is not None  # ty: ignore[unresolved-attribute]
    assert tree.nodes["Collection"].collection is not None  # ty: ignore[unresolved-attribute]
    assert len(tree.nodes) == 6, "if this fails the lines above must also change"


def test_external_items():
    try:
        name = _create_setup()

        export_intermediate = ExportIntermediate(
            parameters=ExportParameters(
                is_material=False,
                name=name,
                specific_handlers=BUILT_IN_EXPORTER,
                export_sub_trees=False,  # this is important otherwise the group won't be an external item
                skip_defaults=True,
                debug_prints=True,
                write_from_roots=False,
            )
        )

        _check_before_export(list(export_intermediate.get_external().values()))

        export_intermediate.set_external(
            (
                external_id,
                _make_some_description(external_item.pointed_to_by.fixed_type_name),
            )
            for external_id, external_item in export_intermediate.get_external().items()
        )

        string = export_intermediate.export_to_str(compress=False, json_indent=4)
        print(string)

        bpy.data.node_groups.remove(bpy.data.node_groups[name])

        import_intermediate = ImportIntermediate()
        import_intermediate.from_str(string)

        _check_before_import(list(import_intermediate.get_external().values()))

        import_intermediate.set_external(
            (
                int(external_id),
                _EXTERNAL_ITEM_MAKER[external_item["fixed_type_name"]](),  # ty: ignore[invalid-argument-type]
            )
            for external_id, external_item in import_intermediate.get_external().items()
        )

        import_intermediate.import_nodes(
            parameters=ImportParameters(
                specific_handlers=BUILT_IN_IMPORTER,
                allow_version_mismatch=False,
                overwrite=True,
                debug_prints=True,
            )
        )

        _check_after_import(name)

    except:
        # store in case of failure for easy debugging
        bpy.ops.wm.save_as_mainfile(filepath=f"{test_external_items.__name__}.blend")
        raise
