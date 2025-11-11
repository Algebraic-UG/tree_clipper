import bpy

import json
from pathlib import Path


def export_node_tree(node_tree):
    # oof
    type = {
        "GEOMETRY": "GeometryNodeTree",
        "COMPOSITING": "CompositorNodeTree",
        "SHADER": "ShaderNodeTree",
        "TEXTURE": "TextureNodeTree",
    }[node_tree.type]

    return {"type": type}


def export_nodes(self, _context):

    if self.material:
        root = bpy.data.materials[self.name].node_tree
    else:
        root = bpy.data.node_groups[self.name]

    d = {
        "material": self.material,
        "name": self.name,
        "root": export_node_tree(root),
    }

    with Path(self.output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))

    return {"FINISHED"}
