import uuid
from pathlib import Path
from typing import Literal

import bpy

from .import_nodes import ImportIntermediate, ImportParameters, ImportReport


def _collect_created_datablocks(report: ImportReport) -> set[bpy.types.ID]:
    datablocks: set[bpy.types.ID] = {
        bpy.data.node_groups[name] for name in report.renames_node_group.values()
    }
    if report.rename_material is not None:
        _original_name, name = report.rename_material
        datablocks.add(bpy.data.materials[name])
    return datablocks


def _remove_created_datablocks(datablocks: set[bpy.types.ID]) -> None:
    for datablock in datablocks:
        if isinstance(datablock, bpy.types.NodeTree):
            bpy.data.node_groups.remove(datablock)
        else:
            assert isinstance(datablock, bpy.types.Material)
            bpy.data.materials.remove(datablock)


def move_import_to_asset_file(
    *,
    report: ImportReport,
    asset_directory: Path | None = None,
    asset_file_path: Path | None = None,
    path_remap: str = "NONE",
    mark_as_asset: bool = True,
    fake_user: bool = False,
    compress: bool = False,
) -> Path:
    datablocks = _collect_created_datablocks(report)

    if report.rename_material is not None:
        _original_name, root_name = report.rename_material
        bpy.data.materials[root_name].asset_mark()
    else:
        root_name = report.last_getter().name  # ty:ignore[unresolved-attribute, call-non-callable]
        bpy.data.node_groups[root_name].asset_mark()

    if asset_file_path is None:
        assert asset_directory is not None
        asset_file_path = (
            asset_directory
            / f"{bpy.path.clean_name(root_name)}-{uuid.uuid4().hex[:8]}.blend"
        )

    bpy.data.libraries.write(
        str(asset_file_path),
        datablocks,
        path_remap=path_remap,
        fake_user=fake_user,
        compress=compress,
    )

    # bpy.data.libraries.write() expands indirectly referenced datablocks (e.g. externals)
    # into the asset file on its own; only the ones tree_clipper created here get moved out.
    _remove_created_datablocks(datablocks)

    return asset_file_path


def import_to_asset_file(
    *,
    import_intermediate: ImportIntermediate,
    parameters: ImportParameters,
    asset_directory: Path | None = None,
    asset_file_path: Path | None = None,
    path_remap: str = "NONE",
    mark_as_asset: bool = True,
    fake_user: bool = False,
    compress: bool = False,
) -> tuple[ImportReport, Path]:
    report = import_intermediate.import_all(parameters)

    asset_file_path = move_import_to_asset_file(
        report=report,
        asset_file_path=asset_file_path,
        path_remap=path_remap,
        fake_user=fake_user,
        compress=compress,
    )

    return report, asset_file_path
