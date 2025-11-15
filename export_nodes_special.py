import bpy

from .export_nodes import Exporter, FromRoot

from .common import (
    IN_OUT,
    INPUTS,
    INTERFACE_ITEMS,
    INTERFACE_ITEMS_ACTIVE,
    INTERFACE_ITEMS_TREE,
    INTERFACE_SOCKET_TYPE,
    MATERIAL_NAME,
    NODE_TREE_INTERFACE,
    NODE_TREE_LINKS,
    NODE_TREE_NODES,
    NODE_TREE_TYPE,
    NODE_TYPE,
    OUTPUTS,
    PROPERTY_TYPES_SIMPLE,
    SOCKET_IDENTIFIER,
    SOCKET_TYPE,
    BLENDER_VERSION,
    FROM_NODE,
    FROM_SOCKET,
    NODES_AS_JSON_VERSION,
    ROOT,
    SUB_TREES,
    TO_NODE,
    TO_SOCKET,
    USE_MULTI_INPUT,
)


def _no_clobber(d: dict, key: str, value):
    if key in d:
        raise RuntimeError(f"Clobbering '{key}'")
    d[key] = value


def _node_tree(
    exporter: Exporter,
    node_tree: bpy.types.NodeTree,
    from_root: FromRoot,
):
    d = exporter.export_all_simple_writable_properties(node_tree, from_root)
    d = d | exporter.export_properties_from_list(
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
    return exporter.export_all_simple_writable_properties(
        interface, from_root
    ) | exporter.export_properties_from_list(
        interface, [INTERFACE_ITEMS_TREE], from_root
    )


def _interface_tree_socket(
    exporter: Exporter,
    socket: bpy.types.NodeTreeInterfaceSocket,
    from_root: FromRoot,
):
    d = exporter.export_all_simple_writable_properties(socket, from_root)

    # will be used as 'socket_type' arg in 'new_socket'
    _no_clobber(d, INTERFACE_SOCKET_TYPE, socket.socket_type)
    _no_clobber(d, IN_OUT, socket.in_out)

    return d


def _interface_tree_panel(
    exporter: Exporter,
    panel: bpy.types.NodeTreeInterfacePanel,
    from_root: FromRoot,
):
    return exporter.export_all_simple_writable_properties(
        panel, from_root
    ) | exporter.export_properties_from_list(panel, [INTERFACE_ITEMS], from_root)


def _node(
    exporter: Exporter,
    node: bpy.types.Node,
    from_root: FromRoot,
):
    d = exporter.export_all_simple_writable_properties(
        node, from_root
    ) | exporter.export_properties_from_list(node, [INPUTS, OUTPUTS], from_root)

    # will be used as 'type' arg in 'new'
    _no_clobber(d, NODE_TYPE, node.bl_rna.identifier)

    return d


def _socket(
    exporter: Exporter,
    socket: bpy.types.NodeSocket,
    from_root: FromRoot,
):
    d = exporter.export_all_simple_writable_properties(socket, from_root)

    # not sure when one has to add sockets, but the following would be needed
    # name is writable, so we already have it

    # will be used as 'type' arg in 'new'
    _no_clobber(d, SOCKET_TYPE, socket.bl_rna.identifier)
    _no_clobber(d, SOCKET_IDENTIFIER, socket.identifier)
    # this technically only needed for inputs
    _no_clobber(d, USE_MULTI_INPUT, socket.is_multi_input)

    return d


BUILT_IN_HANDLERS = {
    bpy.types.NodeTree: _node_tree,
    bpy.types.NodeTreeInterface: _node_tree_interface,
    bpy.types.NodeTreeInterfaceSocket: _interface_tree_socket,
    bpy.types.NodeTreeInterfacePanel: _interface_tree_panel,
    bpy.types.Node: _node,
    bpy.types.NodeSocket: _socket,
}

#    @_debug_print()
#    def _export_node_link(self, link: bpy.types.NodeLink, *, path):
#        d = self._export_all_writable_properties(link, path=path)
#
#        _no_clobber(d, FROM_NODE, link.from_node.name)
#        _no_clobber(d, FROM_SOCKET, link.from_socket.identifier)
#        _no_clobber(d, TO_NODE, link.to_node.name)
#        _no_clobber(d, TO_SOCKET, link.to_socket.identifier)
#
#        return d
#
#    @_debug_print()
#    def _export_node(self, node: bpy.types.Node, *, path: list):
#        d = self._export_all_writable_properties(
#            node, path=path
#        ) | self._export_specific_readonly_properties(node, path=path)
#
#        # will be used as 'type' arg in 'new'
#        _no_clobber(d, NODE_TYPE, node.bl_rna.identifier)
#
#        inputs = [
#            self._export_node_socket(socket, path=path + [f"Input ({socket.name})"])
#            for socket in node.inputs
#        ]
#        _no_clobber(d, INPUTS, inputs)
#        outputs = [
#            self._export_node_socket(socket, path=path + [f"Output ({socket.name})"])
#            for socket in node.outputs
#        ]
#        _no_clobber(d, OUTPUTS, outputs)
#
#        return d
#
#    @_debug_print()
#    def _export_interface_tree_socket(
#        self,
#        socket: bpy.types.NodeTreeInterfaceSocket,
#        *,
#        path: list,
#    ):
#        d = self._export_all_writable_properties(socket, path=path)
#
#        # will be used as 'socket_type' arg in 'new_socket'
#        _no_clobber(d, INTERFACE_SOCKET_TYPE, socket.socket_type)
#        _no_clobber(d, IN_OUT, socket.in_out)
#
#        return d
#
#    @_debug_print()
#    def _export_interface_tree_panel(
#        self,
#        panel: bpy.types.NodeTreeInterfacePanel,
#        *,
#        path: list,
#    ):
#        d = self._export_all_writable_properties(panel, path=path)
#        items = [
#            self._export_interface_item(item, path=path)
#            for item in panel.interface_items
#        ]
#        _no_clobber(d, INTERFACE_ITEMS, items)
#        return d
#
#    def _export_interface_item(
#        self,
#        item: bpy.types.NodeTreeInterfaceItem,
#        *,
#        path: list,
#    ):
#        if item.item_type == "SOCKET":
#            return self._export_interface_tree_socket(
#                item,
#                path=path + [f"{item.in_out} Socket ({item.name})"],
#            )
#        elif item.item_type == "PANEL":
#            return self._export_interface_tree_panel(
#                item,
#                path=path + [f"Panel ({item.name})"],
#            )
#        else:
#            raise RuntimeError(f"Unknown item type: {item.item_type}")
#
#    @_debug_print()
#    def _export_interface(self, interface: bpy.types.NodeTreeInterface, *, path):
#        d = self._export_all_writable_properties(interface, path=path)
#
#        items = [
#            self._export_interface_item(item, path=path)
#            for item in interface.items_tree
#        ]
#        _no_clobber(d, INTERFACE_ITEMS_TREE, items)
#        _no_clobber(d, INTERFACE_ITEMS_ACTIVE, interface.active_index)
#
#        return d
