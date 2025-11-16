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
ROOT = "root"
SUB_TREES = "sub_trees"

SOCKET_IDENTIFIER = "identifier"
IS_MULTI_INPUT = "is_multi_input"

FROM_NODE = "from_node"
FROM_SOCKET = "from_socket"
TO_NODE = "to_node"
TO_SOCKET = "to_socket"

NODE_TYPE = "rna_type"
INPUTS = "inputs"
OUTPUTS = "outputs"

INTERFACE_SOCKET_TYPE = "rna_type"
IN_OUT = "in_out"

INTERFACE_ITEMS = "interface_items"
INTERFACE_ITEMS_TREE = "items_tree"
INTERFACE_ITEMS_ACTIVE = "active"

NODE_TREE_TYPE = "rna_type"
NODE_TREE_INTERFACE = "interface"
NODE_TREE_LINKS = "links"
NODE_TREE_NODES = "nodes"


def no_clobber(d: dict, key: str, value):
    if key in d:
        raise RuntimeError(f"Clobbering '{key}'")
    d[key] = value
