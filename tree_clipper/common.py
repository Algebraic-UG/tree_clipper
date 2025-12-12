import bpy

from types import NoneType
from typing import Any, Callable, TYPE_CHECKING
from pathlib import Path
import tempfile


if TYPE_CHECKING:
    from .export_nodes import Exporter
    from .import_nodes import Importer

# these fields are in the top level JSON object
BLENDER_VERSION = "blender_version"
TREE_CLIPPER_VERSION = "tree_clipper_version"
MATERIAL_NAME = "name"
TREES = "node_trees"
EXTERNAL = "external"
SCENES = "scenes"

# within each external item
EXTERNAL_DESCRIPTION = "description"
EXTERNAL_FIXED_TYPE_NAME = "fixed_type_name"

# for every object
ID = "id"  # to reference it from elsewhere
DATA = "data"  # the actual data
FROM_ROOT = "from_root"  # optional, for debugging

# every compressed serialization starts with this
MAGIC_STRING = "TreeClipper::"

# to help prevent typos
BL_RNA = "bl_rna"
BL_IDNAME = "bl_idname"
RNA_TYPE = "rna_type"  # TODO: another 'forbidden' category?
DEFAULT_VALUE = "default_value"
DISPLAY_SHAPE = "display_shape"
ITEMS = "items"
NAME = "name"
PROP_TYPE_BOOLEAN = "BOOLEAN"
PROP_TYPE_INT = "INT"
PROP_TYPE_FLOAT = "FLOAT"
PROP_TYPE_STRING = "STRING"
PROP_TYPE_ENUM = "ENUM"
PROP_TYPE_POINTER = "POINTER"
PROP_TYPE_COLLECTION = "COLLECTION"
SIMPLE_PROPERTY_TYPES_AS_STRS = set(
    [
        PROP_TYPE_BOOLEAN,
        PROP_TYPE_INT,
        PROP_TYPE_FLOAT,
        PROP_TYPE_STRING,
        PROP_TYPE_ENUM,
    ]
)
NODE_TREE = "node_tree"

# bl_* properties can be dangerous to set
# https://github.com/Algebraic-UG/tree_clipper/issues/39
# they should probably be read-only in most cases?
FORBIDDEN_PROPERTIES = [
    "bl_idname",
    "bl_label",
    "bl_subtype_label",
    "bl_static_type",
    "bl_description",
    "bl_icon",
    "bl_width_default",
    "bl_width_min",
    "bl_width_max",
    "bl_height_default",
    "bl_height_min",
    "bl_height_max",
]


def no_clobber(data: dict, key: str, value) -> None:
    if key in data:
        raise RuntimeError(f"Clobbering '{key}'")
    data[key] = value


class FromRoot:
    def __init__(self, path: list) -> None:
        self.path = path

    def add(self, piece: str) -> "FromRoot":
        return FromRoot(self.path + [piece])

    def add_prop(self, prop: bpy.types.Property) -> "FromRoot":
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
                if ty != NoneType and ty.bl_rna.identifier == obj.bl_rna.identifier  # type: ignore
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
SIMPLE_PROP_TYPE = (
    bpy.types.BoolProperty
    | bpy.types.IntProperty
    | bpy.types.FloatProperty
    | bpy.types.StringProperty
    | bpy.types.EnumProperty
)
SIMPLE_PROP_TYPE_TUPLE = (
    bpy.types.BoolProperty,
    bpy.types.IntProperty,
    bpy.types.FloatProperty,
    bpy.types.StringProperty,
    bpy.types.EnumProperty,
)
EXTERNAL_SERIALIZATION = dict[str, str | None]

DEFAULT_FILE = str(Path(tempfile.gettempdir()) / "default.json")
