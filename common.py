import bpy

from types import NoneType
from typing import Callable

PROPERTY_TYPES_SIMPLE = set(
    [
        "BOOLEAN",
        "INT",
        "FLOAT",
        "STRING",
        "ENUM",
    ]
)

BLENDER_VERSION = "blender_version"
NODES_AS_JSON_VERSION = "nodes_as_json_version"
MATERIAL_NAME = "name"
TREES = "node_trees"

SOCKET_IDENTIFIER = "identifier"
IS_MULTI_INPUT = "is_multi_input"

FROM_NODE = "from_node"
FROM_SOCKET = "from_socket"
TO_NODE = "to_node"
TO_SOCKET = "to_socket"

INPUTS = "inputs"
OUTPUTS = "outputs"

IN_OUT = "in_out"

INTERFACE_ITEMS = "interface_items"
INTERFACE_ITEMS_TREE = "items_tree"
INTERFACE_ITEMS_ACTIVE = "active"

NODE_TREE_TYPE = "rna_type"
NODE_TREE_INTERFACE = "interface"
NODE_TREE_LINKS = "links"
NODE_TREE_NODES = "nodes"

REFERENCE = "nodes_as_json_reference"
ID = "nodes_as_json_id"
DATA = "nodes_as_json_data"


def no_clobber(d: dict, key: str, value):
    if key in d:
        raise RuntimeError(f"Clobbering '{key}'")
    d[key] = value


class FromRoot:
    def __init__(self, path: list):
        self.path = path

    def add(self, piece: str):
        return FromRoot(self.path + [piece])

    def add_prop(self, prop: bpy.types.Property):
        return self.add(f"{prop.type} ({prop.identifier})")

    def to_str(self):
        return str(" -> ".join(self.path))


def most_specific_type_handled(specific_handlers: dict[type, Callable], t: type):
    while True:
        if t in specific_handlers:
            return t
        if len(t.__bases__) == 0:
            return NoneType
        if len(t.__bases__) > 1:
            raise RuntimeError(f"multiple inheritence {t}, unclear what to choose")
        t = t.__bases__[0]
