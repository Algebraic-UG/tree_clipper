import bpy

import json
from pathlib import Path


def export_nodes(self, context):
    d = {"test": "test"}

    with Path(self.output_file).open("w", encoding="utf-8") as f:
        f.write(json.dumps(d, indent=4))

    return {"FINISHED"}
