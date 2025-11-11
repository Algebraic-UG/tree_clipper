import bpy

import json
from pathlib import Path


def import_nodes(self, context):

    with Path(self.input_file).open("r", encoding="utf-8") as f:
        d = json.load(f)

    print(d)

    return {"FINISHED"}
