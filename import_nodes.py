import bpy

import json
from pathlib import Path


def import_nodes(self, _context):

    with Path(self.input_file).open("r", encoding="utf-8") as f:
        d = json.load(f)

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
