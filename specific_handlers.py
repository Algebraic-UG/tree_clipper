import bpy

from types import NoneType

from .import_nodes import GETTER, Importer
from .export_nodes import Exporter

from .common import (
    DATA,
    ID,
    no_clobber,
    IN_OUT,
    INPUTS,
    INTERFACE_ITEMS,
    INTERFACE_ITEMS_TREE,
    NODE_TREE_INTERFACE,
    NODE_TREE_LINKS,
    NODE_TREE_NODES,
    OUTPUTS,
    SOCKET_IDENTIFIER,
    FROM_NODE,
    FROM_SOCKET,
    TO_NODE,
    TO_SOCKET,
    IS_MULTI_INPUT,
    FromRoot,
)


def _or_default(serialization: dict, t: type, identifier: str):
    return serialization.get(identifier, t.bl_rna.properties[identifier].default)


# TODO this is incomplete?
def _map_attribute_type_to_socket_type(attr_type: str):
    return {
        "FLOAT": "FLOAT",
        "INT": "INT",
        "BOOLEAN": "BOOLEAN",
        "FLOAT_VECTOR": "VECTOR",
        "FLOAT_COLOR": "RGBA",
        # "QUATERNION": ???
        "FLOAT4X4": "MATRIX",
        "STRING": "STRING",
        "INT8": "INT",
        # "INT16_2D": ???
        # "INT32_2D": ???
        # "FLOAT2":???
        # "BYTE_COLOR":???
    }[attr_type]


def _export_all_simple_writable_properties_and_list(
    exporter: Exporter,
    obj: bpy.types.bpy_struct,
    assumed_type: type,
    additional: list[str],
    from_root: FromRoot,
):
    d = exporter.export_all_simple_writable_properties(obj, assumed_type, from_root)
    for identifier, data in exporter.export_properties_from_id_list(
        obj, additional, from_root
    ).items():
        no_clobber(d, identifier, data)
    return d


def _import_all_simple_writable_properties_and_list(
    importer: Importer,
    obj: bpy.types.bpy_struct,
    getter: GETTER,
    serialization: dict,
    assumed_type: type,
    additional: list[str],
    from_root: FromRoot,
):
    importer.import_all_simple_writable_properties(
        obj,
        getter,
        serialization,
        assumed_type,
        from_root,
    )
    importer.import_properties_from_id_list(
        obj,
        getter,
        serialization,
        additional,
        from_root,
    )


def _export_node_tree(
    exporter: Exporter,
    node_tree: bpy.types.NodeTree,
    from_root: FromRoot,
):
    d = _export_all_simple_writable_properties_and_list(
        exporter,
        node_tree,
        bpy.types.NodeTree,
        [NODE_TREE_INTERFACE, NODE_TREE_NODES, NODE_TREE_LINKS],
        from_root,
    )

    return d


def _import_node_tree(
    importer: Importer,
    node_tree: bpy.types.NodeTree,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    node_tree.links.clear()
    node_tree.nodes.clear()
    _import_all_simple_writable_properties_and_list(
        importer,
        node_tree,
        getter,
        serialization,
        bpy.types.NodeTree,
        [
            # the order here is important
            # the interface creates sockets on the group input/output nodes that can't be created otherwise
            # the nodes and their sockets must exist in order to be linked up
            NODE_TREE_INTERFACE,
            NODE_TREE_NODES,
            NODE_TREE_LINKS,
        ],
        from_root,
    )


def _import_nodes(
    importer: Importer,
    nodes: bpy.types.Nodes,
    _getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    active_id = serialization.get("active", None)
    for node in serialization["items"]:
        bl_idname = node[DATA]["bl_idname"]
        if importer.debug_prints:
            print(f"{from_root.to_str()}: adding {bl_idname}")
        n = nodes.new(type=bl_idname)
        if node[ID] == active_id:
            nodes.active = n


def _export_node_tree_interface(
    exporter: Exporter,
    interface: bpy.types.NodeTreeInterface,
    from_root: FromRoot,
):
    return _export_all_simple_writable_properties_and_list(
        exporter,
        interface,
        bpy.types.NodeTreeInterface,
        [INTERFACE_ITEMS_TREE],
        from_root,
    )


def _import_node_tree_interface(
    importer: Importer,
    interface: bpy.types.NodeTreeInterface,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    interface.clear()

    def get_type(data: dict):
        item_type = _or_default(data, bpy.types.NodeTreeInterfaceItem, "item_type")
        if item_type == "SOCKET":
            return bpy.types.NodeTreeInterfaceSocket
        if item_type == "PANEL":
            return bpy.types.NodeTreeInterfacePanel
        raise RuntimeError(f"item_type neither SOCKET nor PANEL but {item_type}")

    items = serialization["items_tree"][DATA]["items"]
    uid_map = {}
    for i, item in enumerate(items):
        data = item[DATA]
        t = get_type(data)
        if t == bpy.types.NodeTreeInterfaceSocket:
            interface.new_socket(
                name=str(i),
                description=_or_default(data, t, "description"),
                in_out=_or_default(data, t, "in_out"),
                socket_type=data["socket_type"],
                parent=None,
            )
        else:
            uid_map[data["persistent_uid"]] = i
            interface.new_panel(
                name=str(i),
                description=_or_default(data, t, "description"),
                default_closed=_or_default(data, t, "default_closed"),
            )

    def parent(uid):
        if uid not in uid_map:
            return None
        return interface.items_tree[str(uid_map[uid])]

    for i, item in enumerate(items):
        data = item[DATA]
        interface.move_to_parent(
            item=interface.items_tree[str(i)],
            parent=parent(data["parent"]),
            # this doesn't matter because we move below
            to_position=0,
        )

    # we assume that the order in the serialization matches the one in original memory
    # but the one displayed is something else, stored in 'index'
    # we need to be careful how we move the items, hence the sorting
    sorted_items = list(enumerate(items))
    sorted_items.sort(
        key=lambda index_and_item: _or_default(
            index_and_item[1][DATA], bpy.types.NodeTreeInterfaceItem, "index"
        )
    )
    for i, item in sorted_items:
        interface.move(
            interface.items_tree[str(i)],
            _or_default(item[DATA], bpy.types.NodeTreeInterfaceItem, "index"),
        )

    # this should be fine, we're not modifying the container anymore
    sorted_objs = [interface.items_tree[str(i)] for i in range(len(items))]
    assert len(sorted_objs) == len(items)
    for obj, item in zip(sorted_objs, items):
        data = item[DATA]
        obj.name = _or_default(data, get_type(data), "name")

    _import_all_simple_writable_properties_and_list(
        importer,
        interface,
        getter,
        serialization,
        bpy.types.NodeTreeInterface,
        ["items_tree"],
        from_root,
    )


def _export_interface_tree_socket(
    exporter: Exporter,
    socket: bpy.types.NodeTreeInterfaceSocket,
    from_root: FromRoot,
):
    d = _export_all_simple_writable_properties_and_list(
        exporter,
        socket,
        bpy.types.NodeTreeInterfaceSocket,
        ["item_type", "index", IN_OUT],
        from_root,
    )
    no_clobber(d, "parent", socket.parent.persistent_uid)
    return d


def _export_interface_tree_panel(
    exporter: Exporter,
    panel: bpy.types.NodeTreeInterfacePanel,
    from_root: FromRoot,
):
    d = _export_all_simple_writable_properties_and_list(
        exporter,
        panel,
        bpy.types.NodeTreeInterfacePanel,
        ["item_type", "index", "persistent_uid"],
        from_root,
    )
    no_clobber(d, "parent", panel.parent.persistent_uid)
    return d


def _import_interface_tree_item(
    importer: Importer,
    item: bpy.types.NodeTreeInterfaceItem,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    importer.import_all_simple_writable_properties(
        item,
        getter,
        serialization,
        bpy.types.NodeTreeInterfaceItem,
        from_root,
    )


def _import_interface_tree_panel(
    importer: Importer,
    item: bpy.types.NodeTreeInterfaceItem,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    importer.import_all_simple_writable_properties(
        item,
        getter,
        serialization,
        bpy.types.NodeTreeInterfaceItem,
        from_root,
    )


def _export_node(
    exporter: Exporter,
    node: bpy.types.Node,
    from_root: FromRoot,
):
    return _export_all_simple_writable_properties_and_list(
        exporter,
        node,
        bpy.types.Node,
        [INPUTS, OUTPUTS],
        from_root,
    )


def _import_node(
    importer: Importer,
    node: bpy.types.Node,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    _import_all_simple_writable_properties_and_list(
        importer,
        node,
        getter,
        serialization,
        bpy.types.Node,
        [INPUTS, OUTPUTS],
        from_root,
    )


def _import_node_inputs(
    _importer: Importer,
    inputs: bpy.types.NodeInputs,
    _getter: GETTER,
    serialization: dict,
    _from_root: FromRoot,
):
    if len(inputs) != len(serialization["items"]):
        raise RuntimeError("We currently don't support creating sockets")


def _import_node_outputs(
    _importer: Importer,
    outputs: bpy.types.NodeOutputs,
    _getter: GETTER,
    serialization: dict,
    _from_root: FromRoot,
):
    if len(outputs) != len(serialization["items"]):
        raise RuntimeError("We currently don't support creating sockets")


def _export_socket(
    exporter: Exporter,
    socket: bpy.types.NodeSocket,
    from_root: FromRoot,
):
    return exporter.export_all_simple_writable_properties(
        socket,
        bpy.types.NodeSocket,
        from_root,
    )


def _import_socket(
    importer: Importer,
    socket: bpy.types.NodeSocket,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    importer.import_all_simple_writable_properties(
        socket,
        getter,
        serialization,
        bpy.types.NodeSocket,
        from_root,
    )


def _export_link(
    exporter: Exporter,
    link: bpy.types.NodeLink,
    from_root: FromRoot,
):
    d = exporter.export_all_simple_writable_properties(
        link, bpy.types.NodeLink, from_root
    )

    no_clobber(d, FROM_NODE, link.from_node.name)
    no_clobber(
        d,
        FROM_SOCKET,
        next(
            i
            for i, s in enumerate(link.from_node.outputs)
            if s.identifier == link.from_socket.identifier
        ),
    )
    no_clobber(d, TO_NODE, link.to_node.name)
    no_clobber(
        d,
        TO_SOCKET,
        next(
            i
            for i, s in enumerate(link.to_node.inputs)
            if s.identifier == link.to_socket.identifier
        ),
    )

    return d


def _import_links(
    importer: Importer,
    links: bpy.types.NodeLinks,
    _getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    for link in serialization["items"]:
        data = link[DATA]
        from_node = data["from_node"]
        from_socket = data["from_socket"]
        to_node = data["to_node"]
        to_socket = data["to_socket"]
        if importer.debug_prints:
            print(
                f"{from_root.to_str()}: linking {from_node}, {from_socket} to {to_node}, {to_socket}"
            )
        source = importer.current_tree.nodes[from_node].outputs[from_socket]
        target = importer.current_tree.nodes[to_node].inputs[to_socket]
        links.new(source, target)


def _import_link(
    importer: Importer,
    link: bpy.types.NodeLink,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    importer.import_all_simple_writable_properties(
        link,
        getter,
        serialization,
        bpy.types.NodeLink,
        from_root,
    )


def _export_menu_switch(
    exporter: Exporter,
    node: bpy.types.GeometryNodeMenuSwitch,
    from_root: FromRoot,
):
    return _export_all_simple_writable_properties_and_list(
        exporter,
        node,
        bpy.types.GeometryNodeMenuSwitch,
        [INPUTS, OUTPUTS, "enum_items"],
        from_root,
    )


def _import_menu_switch(
    importer: Importer,
    node: bpy.types.GeometryNodeMenuSwitch,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    _import_all_simple_writable_properties_and_list(
        importer,
        node,
        getter,
        serialization,
        bpy.types.GeometryNodeMenuSwitch,
        # ordering is important, the enum_items implicitly create sockets
        ["enum_items", INPUTS, OUTPUTS],
        from_root,
    )


def _import_menu_switch_items(
    importer: Importer,
    items: bpy.types.NodeMenuSwitchItems,
    _getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    items.clear()
    for item in serialization["items"]:
        name = _or_default(item[DATA], bpy.types.NodeEnumItem, "name")
        if importer.debug_prints:
            print(f"{from_root.to_str()}: adding item {name}")
        items.new(name)


def _export_capture_attr(
    exporter: Exporter,
    node: bpy.types.GeometryNodeCaptureAttribute,
    from_root: FromRoot,
):
    return _export_all_simple_writable_properties_and_list(
        exporter,
        node,
        bpy.types.GeometryNodeCaptureAttribute,
        [INPUTS, OUTPUTS, "capture_items"],
        from_root,
    )


def _import_capture_attr(
    importer: Importer,
    node: bpy.types.GeometryNodeCaptureAttribute,
    getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    _import_all_simple_writable_properties_and_list(
        importer,
        node,
        getter,
        serialization,
        bpy.types.GeometryNodeCaptureAttribute,
        ["capture_items", INPUTS, OUTPUTS],
        from_root,
    )


def _import_catpure_attr_items(
    importer: Importer,
    items: bpy.types.NodeGeometryCaptureAttributeItems,
    _getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    items.clear()
    for item in serialization["items"]:
        name = _or_default(item[DATA], bpy.types.NodeEnumItem, "name")
        data_type = _map_attribute_type_to_socket_type(
            _or_default(
                item[DATA], bpy.types.NodeGeometryCaptureAttributeItem, "data_type"
            )
        )
        if importer.debug_prints:
            print(f"{from_root.to_str()}: adding item {name} {data_type}")
        items.new(data_type, name)


# TODO: make sure that they use a matching type in the hint
BUILT_IN_SERIALIZERS = {
    NoneType: lambda _exporter, _obj, _from_root: {},
    bpy.types.NodeTree: _export_node_tree,
    bpy.types.NodeTreeInterface: _export_node_tree_interface,
    bpy.types.NodeTreeInterfaceSocket: _export_interface_tree_socket,
    bpy.types.NodeTreeInterfacePanel: _export_interface_tree_panel,
    bpy.types.Node: _export_node,
    bpy.types.NodeSocket: _export_socket,
    bpy.types.NodeLink: _export_link,
    bpy.types.GeometryNodeMenuSwitch: _export_menu_switch,
    bpy.types.GeometryNodeCaptureAttribute: _export_capture_attr,
}


# TODO: make sure that they use a matching type in the hint
BUILT_IN_DESERIALIZERS = {
    NoneType: lambda _importer, _obj, _getter, _serialization, _from_root: {},
    bpy.types.NodeTree: _import_node_tree,
    bpy.types.NodeTreeInterface: _import_node_tree_interface,
    bpy.types.NodeTreeInterfaceItem: _import_interface_tree_item,
    bpy.types.NodeTreeInterfacePanel: _import_interface_tree_panel,
    bpy.types.Nodes: _import_nodes,
    bpy.types.Node: _import_node,
    bpy.types.NodeInputs: _import_node_inputs,
    bpy.types.NodeOutputs: _import_node_outputs,
    bpy.types.NodeSocket: _import_socket,
    bpy.types.NodeLinks: _import_links,
    bpy.types.NodeLink: _import_link,
    bpy.types.GeometryNodeMenuSwitch: _import_menu_switch,
    bpy.types.NodeMenuSwitchItems: _import_menu_switch_items,
    bpy.types.GeometryNodeCaptureAttribute: _import_capture_attr,
    bpy.types.NodeGeometryCaptureAttributeItems: _import_catpure_attr_items,
}
