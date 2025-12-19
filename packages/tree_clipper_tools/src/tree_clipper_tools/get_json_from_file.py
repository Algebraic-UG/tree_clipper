from tree_clipper.specific_handlers import BUILT_IN_EXPORTER
from tree_clipper.export_nodes import ExportIntermediate, ExportParameters
import argparse
import bpy

parser = argparse.ArgumentParser(prog="Get JSON from tree in file")
parser.add_argument("--filename", required=True)
parser.add_argument("--name", required=True)
parser.add_argument("--is_material", required=True)
parser.add_argument("--debug_prints")

args = parser.parse_args()

bpy.ops.wm.open_mainfile(filepath=args.filename)


export_intermediate = ExportIntermediate(
    parameters=ExportParameters(
        is_material=args.is_material,
        name=args.name,
        specific_handlers=BUILT_IN_EXPORTER,
        export_sub_trees=True,
        debug_prints=args.debug_prints,
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

print(export_intermediate.export_to_str(compress=False, json_indent=4))
