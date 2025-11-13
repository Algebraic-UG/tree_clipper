import bpy

import tomllib
import json
from pathlib import Path


def _check_version(d):
    exporter_blender_version = d["blender_version"]
    importer_blender_version = bpy.app.version_string
    if exporter_blender_version != importer_blender_version:
        return f"Blender version mismatch. File version: {exporter_blender_version}, but running {importer_blender_version}"

    exporter_node_as_json_version = d["node_as_json_version"]
    manifest_path = Path(__file__).parent / "blender_manifest.toml"
    with manifest_path.open("rb") as f:
        blender_manifest = tomllib.load(f)
    importer_node_as_json_version = blender_manifest["version"]
    name = blender_manifest["name"]

    if exporter_node_as_json_version != importer_node_as_json_version:
        return f"{name} version mismatch. File version: {exporter_node_as_json_version}, but running {importer_node_as_json_version}"


def import_nodes(self, allow_version_mismatch=False):
    with Path(self.input_file).open("r", encoding="utf-8") as f:
        d = json.load(f)

    version_mismatch = _check_version(d)
    if version_mismatch is not None:
        if allow_version_mismatch:
            self.report({"WARNING"}, version_mismatch)
        else:
            raise RuntimeError(version_mismatch)

    if d["material"]:
        if self.overwrite:
            mat = bpy.data.materials[d["name"]]
        else:
            mat = bpy.data.materials.new(name=d["name"])
            mat.use_nodes = True
        root = mat.node_tree
    else:
        if self.overwrite:
            root = bpy.data.node_groups[d["name"]]
        else:
            root = bpy.data.node_groups.new(type=d["root"]["type"], name=d["name"])

    for node in root.nodes:
        root.nodes.remove(node)

    print(d)

    return {"FINISHED"}
