import bpy

import json
from pathlib import Path


def export_nodes(self, _context):

    d = {
        "material": self.material,
        "name": self.name,
    }

    if self.material:
        node_tree = bpy.data.materials[self.name].node_tree
    else:
        node_tree = bpy.data.node_groups[self.name]

    print(type(node_tree))

    with Path(self.output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))

    return {"FINISHED"}
