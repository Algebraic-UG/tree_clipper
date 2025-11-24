import bpy

from types import NoneType
from typing import Any, Callable, TYPE_CHECKING, Self


if TYPE_CHECKING:
    from .export_nodes import Exporter
    from .import_nodes import Importer

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
TREE_CLIPPER_VERSION = "tree_clipper_version"
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

ID = "id"
DATA = "data"

MAGIC_STRING = "TreeClipper::"


def no_clobber(data: dict, key: str, value) -> None:
    if key in data:
        raise RuntimeError(f"Clobbering '{key}'")
    data[key] = value


class FromRoot:
    def __init__(self, path: list) -> None:
        self.path = path

    def add(self, piece: str) -> Self:
        return FromRoot(self.path + [piece])

    def add_prop(self, prop: bpy.types.Property) -> Self:
        return self.add(f"{prop.type} ({prop.identifier})")

    def to_str(self) -> str:
        return str(" -> ".join(self.path))


def most_specific_type_handled(
    specific_handlers: dict[type, Callable],
    obj: bpy.types.bpy_struct,
) -> type:
    # collections are too weird, this is False:
    # type(bpy.data.node_groups['Geometry Nodes'].nodes) == bpy.types.Nodes
    if isinstance(obj, bpy.types.bpy_prop_collection):
        return next(
            (
                ty
                for ty in specific_handlers.keys()
                if ty != NoneType and ty.bl_rna.identifier == obj.bl_rna.identifier
            ),
            NoneType,
        )

    ty = type(obj)
    while True:
        if ty in specific_handlers.keys():
            return ty
        if len(ty.__bases__) == 0:
            return NoneType
        if len(ty.__bases__) > 1:
            raise RuntimeError(f"multiple inheritence {ty}, unclear what to choose")
        ty = ty.__bases__[0]


GETTER = Callable[[], bpy.types.bpy_struct]
SERIALIZER = Callable[["Exporter", bpy.types.bpy_struct, FromRoot], dict[str, Any]]
DESERIALIZER = Callable[["Importer", GETTER, dict, FromRoot], None]
SIMPLE_DATA_TYPE = list[str] | list[float] | list[int] | str | float | int
