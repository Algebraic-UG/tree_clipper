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
            # NODE_TREE_NODES,
            # NODE_TREE_LINKS,
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
    importer.import_all_simple_writable_properties(
        interface,
        getter,
        serialization,
        bpy.types.NodeTreeInterface,
        from_root,
    )

    interface.clear()

    uid_map = {}
    for item in serialization["items_tree"][DATA]["items"]:
        data = item[DATA]
        item_type = data["item_type"]
        if item_type == "SOCKET":
            t = bpy.types.NodeTreeInterfaceSocket
            interface.new_socket(
                name=_or_default(data, t, "name"),
                description=_or_default(data, t, "description"),
                in_out=_or_default(data, t, "in_out"),
                socket_type=data["socket_type"],
                parent=None,
            )
        elif item_type == "PANEL":
            t = bpy.types.NodeTreeInterfacePanel
            uid_map[data["persistent_uid"]] = interface.new_panel(
                name=_or_default(data, t, "name"),
                description=_or_default(data, t, "description"),
                default_closed=_or_default(data, t, "default_closed"),
            ).persistent_uid
        else:
            raise RuntimeError(f"item_type neither SOCKET nor PANEL but {item_type}")

    def parent(uid):
        if uid not in uid_map:
            return None
        return next(
            p
            for p in interface.items_tree
            if getattr(p, "persistent_uid", None) == uid_map[uid]
        )

    for i, item in enumerate(serialization["items_tree"][DATA]["items"]):
        data = item[DATA]
        interface.move_to_parent(
            item=interface.items_tree[i],
            parent=parent(data["parent"]),
            to_position=_or_default(data, bpy.types.NodeTreeInterfaceItem, "position"),
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
        ["item_type", "position", IN_OUT],
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
        ["item_type", "position", "persistent_uid"],
        from_root,
    )
    no_clobber(d, "parent", panel.parent.persistent_uid)
    return d


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


def _import_node_inputs(
    importer: Importer,
    inputs: bpy.types.NodeInputs,
    _getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    existing_identifiers = [i.identifier for i in inputs]
    for input_socket in serialization["items"]:
        data = input_socket[DATA]
        identifier = data["identifier"]
        if identifier in existing_identifiers:
            continue
        if importer.debug_prints:
            print(f"{from_root}: adding {identifier}")
        inputs.new(
            type=data["bl_idname"],
            name=data["name"],
            identifier=identifier,
            use_multi_input=_or_default(data, bpy.types.NodeSocket, "is_multi_input"),
        )


def _import_node_outputs(
    importer: Importer,
    outputs: bpy.types.NodeOutputs,
    _getter: GETTER,
    serialization: dict,
    from_root: FromRoot,
):
    existing_identifiers = [i.identifier for i in outputs]
    for output_sockets in serialization["items"]:
        data = output_sockets[DATA]
        identifier = data["identifier"]
        if identifier in existing_identifiers:
            continue
        if importer.debug_prints:
            print(f"{from_root}: adding {identifier}")
        outputs.new(
            type=data["bl_idname"],
            name=data["name"],
            identifier=identifier,
        )


def _export_socket(
    exporter: Exporter,
    socket: bpy.types.NodeSocket,
    from_root: FromRoot,
):
    d = _export_all_simple_writable_properties_and_list(
        exporter,
        socket,
        bpy.types.NodeSocket,
        [SOCKET_IDENTIFIER, IS_MULTI_INPUT],
        from_root,
    )

    return d


def _export_link(
    exporter: Exporter,
    link: bpy.types.NodeLink,
    from_root: FromRoot,
):
    d = exporter.export_all_simple_writable_properties(
        link, bpy.types.NodeLink, from_root
    )

    no_clobber(d, FROM_NODE, link.from_node.name)
    no_clobber(d, FROM_SOCKET, link.from_socket.identifier)
    no_clobber(d, TO_NODE, link.to_node.name)
    no_clobber(d, TO_SOCKET, link.to_socket.identifier)

    return d


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
}


# TODO: make sure that they use a matching type in the hint
BUILT_IN_DESERIALIZERS = {
    NoneType: lambda _importer, _obj, _getter, _serialization, _from_root: {},
    bpy.types.NodeTree: _import_node_tree,
    bpy.types.NodeTreeInterface: _import_node_tree_interface,
    bpy.types.Nodes: _import_nodes,
    bpy.types.NodeInputs: _import_node_inputs,
    bpy.types.NodeOutputs: _import_node_outputs,
}
