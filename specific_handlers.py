from types import NoneType
import bpy

from .export_nodes import Exporter

from .common import (
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


def _export_all_simple_writable_properties_and_list(
    exporter: Exporter,
    obj: bpy.types.bpy_struct,
    assumed_type: type,
    additional: list,
    from_root: FromRoot,
):
    return exporter.export_all_simple_writable_properties(
        obj, assumed_type, from_root
    ) | exporter.export_properties_from_id_list(
        obj, assumed_type, additional, from_root
    )


def _node_tree(
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


def _node_tree_interface(
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


def _interface_tree_socket(
    exporter: Exporter,
    socket: bpy.types.NodeTreeInterfaceSocket,
    from_root: FromRoot,
):
    return _export_all_simple_writable_properties_and_list(
        exporter,
        socket,
        bpy.types.NodeTreeInterfaceSocket,
        [IN_OUT],
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
        bpy.types.NodeTreeInterfacePanel,
        [INTERFACE_ITEMS],
        from_root,
    )


def _node(
    exporter: Exporter,
    node: bpy.types.Node,
    from_root: FromRoot,
):
    d = _export_all_simple_writable_properties_and_list(
        exporter,
        node,
        bpy.types.Node,
        [INPUTS, OUTPUTS],
        from_root,
    )

    return d


def _socket(
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


def _link(
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


BUILT_IN_HANDLERS = {
    NoneType: lambda _exporter, _obj, _from_root: {},
    bpy.types.NodeTree: _node_tree,
    bpy.types.NodeTreeInterface: _node_tree_interface,
    bpy.types.NodeTreeInterfaceSocket: _interface_tree_socket,
    bpy.types.NodeTreeInterfacePanel: _interface_tree_panel,
    bpy.types.Node: _node,
    bpy.types.NodeSocket: _socket,
    bpy.types.NodeLink: _link,
}
