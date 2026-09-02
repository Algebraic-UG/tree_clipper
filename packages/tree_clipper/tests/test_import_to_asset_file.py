from pathlib import Path

import bpy
from tree_clipper.export_nodes import ExportIntermediate, ExportParameters
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters
from tree_clipper.import_to_asset_file import import_to_asset_file
from tree_clipper.specific_handlers import BUILT_IN_EXPORTER, BUILT_IN_IMPORTER

from tests.util import export_to_string, make_test_node_tree


def test_import_to_asset_file(tmp_path: Path):
    tree = make_test_node_tree()
    original_name = tree.name

    before = export_to_string(original_name)

    # start fresh, as if importing into a different file
    bpy.data.node_groups.remove(tree)

    asset_file_path = tmp_path / "asset.blend"

    import_intermediate = ImportIntermediate(string=before)
    report, _file_path = import_to_asset_file(
        import_intermediate=import_intermediate,
        parameters=ImportParameters(
            specific_handlers=BUILT_IN_IMPORTER,
            debug_prints=False,
        ),
        asset_file_path=asset_file_path,
    )

    imported_name = report.renames_node_group[original_name]

    assert imported_name not in bpy.data.node_groups
    assert asset_file_path.exists()

    with bpy.data.libraries.load(str(asset_file_path)) as (data_from, _data_to):
        assert imported_name in data_from.node_groups


def test_import_to_asset_file_material(tmp_path: Path):
    mat = bpy.data.materials.new("test_material")
    mat.use_nodes = True
    original_name = mat.name

    export_intermediate = ExportIntermediate(
        parameters=ExportParameters(
            is_material=True,
            name=original_name,
            specific_handlers=BUILT_IN_EXPORTER,
            export_sub_trees=True,
            debug_prints=False,
            write_from_roots=False,
        )
    )
    while export_intermediate.step():
        pass
    before = export_intermediate.export_to_str(compress=False, json_indent=4)

    bpy.data.materials.remove(mat)

    asset_file_path = tmp_path / "asset.blend"

    import_intermediate = ImportIntermediate(string=before)
    report, _file_path = import_to_asset_file(
        import_intermediate=import_intermediate,
        parameters=ImportParameters(
            specific_handlers=BUILT_IN_IMPORTER,
            debug_prints=False,
        ),
        asset_file_path=asset_file_path,
    )

    assert report.rename_material is not None
    _original_name, imported_name = report.rename_material

    assert imported_name not in bpy.data.materials
    assert asset_file_path.exists()

    with bpy.data.libraries.load(str(asset_file_path)) as (data_from, _data_to):
        assert imported_name in data_from.materials
