from tree_clipper.export_nodes import ExportIntermediate, ExportParameters
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters
from tree_clipper.specific_handlers import BUILT_IN_EXPORTER, BUILT_IN_IMPORTER


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
