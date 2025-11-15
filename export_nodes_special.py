import bpy

from .export_nodes import Exporter, FromRoot

from .common import (
    IN_OUT,
    INPUTS,
    INTERFACE_ITEMS,
    INTERFACE_ITEMS_TREE,
    INTERFACE_SOCKET_TYPE,
    NODE_TREE_INTERFACE,
    NODE_TREE_LINKS,
    NODE_TREE_NODES,
    NODE_TREE_TYPE,
    NODE_TYPE,
    OUTPUTS,
    SOCKET_IDENTIFIER,
    SOCKET_TYPE,
    FROM_NODE,
    FROM_SOCKET,
    TO_NODE,
    TO_SOCKET,
    IS_MULTI_INPUT,
)


def _no_clobber(d: dict, key: str, value):
    if key in d:
        raise RuntimeError(f"Clobbering '{key}'")
    d[key] = value


def _export_all_simple_writable_properties_and_list(
    exporter: Exporter,
    obj: bpy.types.bpy_struct,
    additional: list,
    from_root: FromRoot,
):
    return exporter.export_all_simple_writable_properties(
        obj, from_root
    ) | exporter.export_properties_from_id_list(obj, additional, from_root)


def _node_tree(
    exporter: Exporter,
    node_tree: bpy.types.NodeTree,
    from_root: FromRoot,
):
    d = _export_all_simple_writable_properties_and_list(
        exporter,
        node_tree,
        [NODE_TREE_INTERFACE, NODE_TREE_NODES, NODE_TREE_LINKS],
        from_root,
    )

    # will be used as 'type' arg in 'new'
    _no_clobber(d, NODE_TREE_TYPE, node_tree.bl_rna.identifier)

    return d


def _node_tree_interface(
    exporter: Exporter,
    interface: bpy.types.NodeTreeInterface,
    from_root: FromRoot,
):
    return _export_all_simple_writable_properties_and_list(
        exporter,
        interface,
        [INTERFACE_ITEMS_TREE],
        from_root,
    )


def _interface_tree_socket(
    exporter: Exporter,
    socket: bpy.types.NodeTreeInterfaceSocket,
    from_root: FromRoot,
):
    return _export_all_simple_writable_properties_and_list(
        exporter,
        socket,
        [INTERFACE_SOCKET_TYPE, IN_OUT],
        from_root,
    )


def _interface_tree_panel(
    exporter: Exporter,
    panel: bpy.types.NodeTreeInterfacePanel,
    from_root: FromRoot,
):
    return _export_all_simple_writable_properties_and_list(
        exporter,
        panel,
        [INTERFACE_ITEMS],
        from_root,
    )


def _node(
    exporter: Exporter,
    node: bpy.types.Node,
    from_root: FromRoot,
):
    d = _export_all_simple_writable_properties_and_list(
        exporter, node, [INPUTS, OUTPUTS], from_root
    )

    # will be used as 'type' arg in 'new'
    _no_clobber(d, NODE_TYPE, node.bl_rna.identifier)

    return d


def _socket(
    exporter: Exporter,
    socket: bpy.types.NodeSocket,
    from_root: FromRoot,
):
    d = _export_all_simple_writable_properties_and_list(
        exporter,
        socket,
        [SOCKET_IDENTIFIER, IS_MULTI_INPUT],
        from_root,
    )

    # will be used as 'type' arg in 'new'
    _no_clobber(d, SOCKET_TYPE, socket.bl_rna.identifier)

    return d


def _link(
    exporter: Exporter,
    link: bpy.types.NodeLink,
    from_root: FromRoot,
):
    d = exporter.export_all_simple_writable_properties(link, from_root)

    _no_clobber(d, FROM_NODE, link.from_node.name)
    _no_clobber(d, FROM_SOCKET, link.from_socket.identifier)
    _no_clobber(d, TO_NODE, link.to_node.name)
    _no_clobber(d, TO_SOCKET, link.to_socket.identifier)

    return d


BUILT_IN_HANDLERS = {
    bpy.types.NodeTree: _node_tree,
    bpy.types.NodeTreeInterface: _node_tree_interface,
    bpy.types.NodeTreeInterfaceSocket: _interface_tree_socket,
    bpy.types.NodeTreeInterfacePanel: _interface_tree_panel,
    bpy.types.NodeGroupInput: _node,
    bpy.types.NodeGroupOutput: _node,
    bpy.types.NodeSocket: _socket,
    bpy.types.NodeLink: _link,
}
