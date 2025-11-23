import bpy

from .specific_abstract import (
    _BUILT_IN_EXPORTER,
    _BUILT_IN_IMPORTER,
    SpecificExporter,
    SpecificImporter,
)

from .common import (
    DATA,
    ID,
    no_clobber,
    IN_OUT,
    INPUTS,
    INTERFACE_ITEMS_TREE,
    NODE_TREE_INTERFACE,
    NODE_TREE_LINKS,
    NODE_TREE_NODES,
    OUTPUTS,
    FROM_NODE,
    FROM_SOCKET,
    TO_NODE,
    TO_SOCKET,
)


def _or_default(serialization: dict, ty: type, identifier: str):
    return serialization.get(identifier, ty.bl_rna.properties[identifier].default)


# Possible socket data types: https://docs.blender.org/api/current/bpy_types_enum_items/node_socket_data_type_items.html#rna-enum-node-socket-data-type-items
# Only a subset of those are supported on the capture attribute node: FLOAT, INT, VECTOR, RGBA, BOOLEAN, QUATERNION, MATRIX
# TODO this is incomplete?
def _map_attribute_type_to_socket_type(attr_type: str):
    return {
        "FLOAT": "FLOAT",
        "INT": "INT",
        "BOOLEAN": "BOOLEAN",
        "FLOAT_VECTOR": "VECTOR",
        "FLOAT_COLOR": "RGBA",
        "QUATERNION": "ROTATION",
        "FLOAT4X4": "MATRIX",
        "STRING": "STRING",
        "INT8": "INT",
        # "INT16_2D": ???
        # "INT32_2D": ???
        # "FLOAT2": "VECTOR",
        # "BYTE_COLOR": "RGBA",
    }[attr_type]


class NodeTreeExporter(SpecificExporter[bpy.types.NodeTree]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [NODE_TREE_INTERFACE, NODE_TREE_NODES, NODE_TREE_LINKS]
        )


class NodeTreeImporter(SpecificImporter[bpy.types.NodeTree]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            [NODE_TREE_INTERFACE, NODE_TREE_NODES]
        )

        # one thing that requires this is the repeat zone
        # after this more sockets are available for linking
        for func in self.importer.create_special_node_connections:
            func()
        self.importer.create_special_node_connections.clear()

        self.import_properties_from_id_list([NODE_TREE_LINKS])

        # now that the links exist they won't be removed immediately
        for func in self.importer.set_auto_remove:
            func()
        self.importer.set_auto_remove.clear()


class NodesImporter(SpecificImporter[bpy.types.Nodes]):
    def deserialize(self):
        self.getter().clear()
        active_id = self.serialization.get("active", None)
        for node in self.serialization["items"]:
            bl_idname = node[DATA]["bl_idname"]
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding {bl_idname}")
            new_node = self.getter().new(type=bl_idname)
            # it's important to do this immediately because renaming later can change more than one name
            new_node.name = _or_default(self.serialization, bpy.types.Node, "name")
            if node[ID] == active_id:
                self.getter().active = new_node


class InterfaceExporter(SpecificExporter[bpy.types.NodeTreeInterface]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INTERFACE_ITEMS_TREE]
        )


class InterfaceImporter(SpecificImporter[bpy.types.NodeTreeInterface]):
    def deserialize(self):
        self.getter().clear()

        def get_type(data: dict):
            item_type = _or_default(data, bpy.types.NodeTreeInterfaceItem, "item_type")
            if item_type == "SOCKET":
                return bpy.types.NodeTreeInterfaceSocket
            if item_type == "PANEL":
                return bpy.types.NodeTreeInterfacePanel
            raise RuntimeError(f"item_type neither SOCKET nor PANEL but {item_type}")

        items = self.serialization["items_tree"][DATA]["items"]
        uid_map = {}
        for i, item in enumerate(items):
            data = item[DATA]
            ty = get_type(data)
            if ty == bpy.types.NodeTreeInterfaceSocket:
                self.getter().new_socket(
                    name=str(i),
                    description=_or_default(data, ty, "description"),
                    in_out=_or_default(data, ty, "in_out"),
                    socket_type=data["socket_type"],
                    parent=None,
                )
            else:
                uid_map[
                    _or_default(
                        data, bpy.types.NodeTreeInterfacePanel, "persistent_uid"
                    )
                ] = i
                self.getter().new_panel(
                    name=str(i),
                    description=_or_default(data, ty, "description"),
                    default_closed=_or_default(data, ty, "default_closed"),
                )

        def parent(uid):
            if uid not in uid_map:
                return None
            return self.getter().items_tree[str(uid_map[uid])]

        for i, item in enumerate(items):
            data = item[DATA]
            self.getter().move_to_parent(
                item=self.getter().items_tree[str(i)],
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
            self.getter().move(
                self.getter().items_tree[str(i)],
                _or_default(item[DATA], bpy.types.NodeTreeInterfaceItem, "index"),
            )

        # this should be fine, we're not modifying the container anymore
        sorted_objs = [self.getter().items_tree[str(i)] for i in range(len(items))]
        assert len(sorted_objs) == len(items)
        for obj, item in zip(sorted_objs, items):
            data = item[DATA]
            obj.name = _or_default(data, get_type(data), "name")

        self.import_all_simple_writable_properties_and_list(["items_tree"])


class TreeSocketExporter(SpecificExporter[bpy.types.NodeTreeInterfaceSocket]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list(
            ["item_type", "index", IN_OUT]
        )
        no_clobber(data, "parent", self.obj.parent.persistent_uid)
        return data


class TreePanelExporter(SpecificExporter[bpy.types.NodeTreeInterfacePanel]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list(
            ["item_type", "index", "persistent_uid"]
        )
        no_clobber(data, "parent", self.obj.parent.persistent_uid)
        return data


class TreeItemImporter(SpecificImporter[bpy.types.NodeTreeInterfaceItem]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class TreePanelImporter(SpecificImporter[bpy.types.NodeTreeInterfacePanel]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class NodeExporter(SpecificExporter[bpy.types.Node]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])


class NodeImporter(SpecificImporter[bpy.types.Node]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])


class NodeInputsImporter(SpecificImporter[bpy.types.NodeInputs]):
    def deserialize(self):
        expected = len(self.serialization["items"])
        current = len(self.getter())
        if current != expected:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
expected {expected} in-sockets but found {current}
we currently don't support creating sockets"""
            )


class NodeOutputsImporter(SpecificImporter[bpy.types.NodeOutputs]):
    def deserialize(self):
        expected = len(self.serialization["items"])
        current = len(self.getter())
        if current != expected:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
expected {expected} out-sockets but found {current}
we currently don't support creating sockets"""
            )


class SocketExporter(SpecificExporter[bpy.types.NodeSocket]):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class SocketImporter(SpecificImporter[bpy.types.NodeSocket]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class LinkExporter(SpecificExporter[bpy.types.NodeLink]):
    def serialize(self):
        data = self.export_all_simple_writable_properties()

        no_clobber(data, FROM_NODE, self.obj.from_node.name)
        no_clobber(
            data,
            FROM_SOCKET,
            next(
                i
                for i, socket in enumerate(self.obj.from_node.outputs)
                if socket.identifier == self.obj.from_socket.identifier
            ),
        )
        no_clobber(data, TO_NODE, self.obj.to_node.name)
        no_clobber(
            data,
            TO_SOCKET,
            next(
                i
                for i, socket in enumerate(self.obj.to_node.inputs)
                if socket.identifier == self.obj.to_socket.identifier
            ),
        )

        return data


class LinksImporter(SpecificImporter[bpy.types.NodeLinks]):
    def deserialize(self):
        for link in self.serialization["items"]:
            data = link[DATA]
            from_node = data["from_node"]
            from_socket = data["from_socket"]
            to_node = data["to_node"]
            to_socket = data["to_socket"]
            if self.importer.debug_prints:
                print(
                    f"{self.from_root.to_str()}: linking {from_node}, {from_socket} to {to_node}, {to_socket}"
                )
            self.getter().new(
                input=self.importer.current_tree.nodes[from_node].outputs[from_socket],
                output=self.importer.current_tree.nodes[to_node].inputs[to_socket],
            )


class LinkImporter(SpecificImporter[bpy.types.NodeLink]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class MenuSwitchExporter(SpecificExporter[bpy.types.GeometryNodeMenuSwitch]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, "enum_items"]
        )


class MenuSwitchImporter(SpecificImporter[bpy.types.GeometryNodeMenuSwitch]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the enum_items implicitly create sockets
            ["enum_items", INPUTS, OUTPUTS],
        )


class MenuSwitchItemsImporter(SpecificImporter[bpy.types.NodeMenuSwitchItems]):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization["items"]:
            name = _or_default(item[DATA], bpy.types.NodeEnumItem, "name")
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name}")
            self.getter().new(name=name)


class CaptureAttrExporter(SpecificExporter[bpy.types.GeometryNodeCaptureAttribute]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, "capture_items"],
        )


class CaptureAttrImporter(SpecificImporter[bpy.types.GeometryNodeCaptureAttribute]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the capture_items implicitly create sockets
            ["capture_items", INPUTS, OUTPUTS],
        )


class CaptureAttrItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryCaptureAttributeItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization["items"]:
            name = _or_default(item[DATA], bpy.types.NodeEnumItem, "name")
            socket_type = _map_attribute_type_to_socket_type(
                _or_default(
                    item[DATA], bpy.types.NodeGeometryCaptureAttributeItem, "data_type"
                )
            )
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


class RepeatInputExporter(SpecificExporter[bpy.types.GeometryNodeRepeatInput]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])
        if self.obj.paired_output is None:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
Having no paired output for repeat nodes isn't supported"""
            )
        no_clobber(data, "paired_output", self.obj.paired_output.name)

        return data


class RepeatInputImporter(SpecificImporter[bpy.types.GeometryNodeRepeatInput]):
    def deserialize(self):
        self.import_all_simple_writable_properties()

        # if this fails it's easier to debug here
        output = self.serialization["paired_output"]

        def deferred():
            if not self.getter().pair_with_output(
                self.importer.current_tree.nodes[output]
            ):
                raise RuntimeError(
                    f"{self.from_root.to_str()}: failed to pair with {output}"
                )
            self.import_properties_from_id_list([INPUTS, OUTPUTS])

        # defer connection until we've created the output node
        # only then, import the sockets
        self.importer.create_special_node_connections.append(deferred)


class RepeatOutputExporter(SpecificExporter[bpy.types.GeometryNodeRepeatOutput]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, "repeat_items"]
        )


class RepeatOutputImporter(SpecificImporter[bpy.types.GeometryNodeRepeatOutput]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the repeat_items implicitly create sockets
            ["repeat_items", INPUTS, OUTPUTS]
        )


class RepeatOutputItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryRepeatOutputItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization["items"]:
            name = _or_default(item[DATA], bpy.types.NodeEnumItem, "name")
            socket_type = _or_default(item[DATA], bpy.types.RepeatItem, "socket_type")
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


class IndexItemExporter(SpecificExporter[bpy.types.IndexSwitchItem]):
    def serialize(self):
        return {}


class IndexItemsImporter(SpecificImporter[bpy.types.NodeIndexSwitchItems]):
    def deserialize(self):
        self.getter().clear()
        for _ in self.serialization["items"]:
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding index")
            self.getter().new()


class ViewerSpecificExporter(SpecificExporter[bpy.types.GeometryNodeViewer]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, "viewer_items"]
        )


class ViewerImporter(SpecificImporter[bpy.types.GeometryNodeViewer]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the viewer_items implicitly create sockets
            ["viewer_items", INPUTS, OUTPUTS],
        )


class ViewerItemsImporter(SpecificImporter[bpy.types.NodeGeometryViewerItems]):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization["items"]:
            data = item[DATA]
            name = _or_default(data, bpy.types.NodeGeometryViewerItem, "name")
            socket_type = _or_default(
                data, bpy.types.NodeGeometryViewerItem, "socket_type"
            )

            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")

            self.getter().new(socket_type=socket_type, name=name)


class ViewerItemImporter(SpecificImporter[bpy.types.NodeGeometryViewerItem]):
    def deserialize(self):
        auto_remove = _or_default(
            self.serialization, bpy.types.NodeGeometryViewerItem, "auto_remove"
        )

        def deferred():
            self.getter().auto_remove = auto_remove

        # very, very important to not set auto_remove to true before the links are established
        # especially while iterating over more properties of it
        self.importer.set_auto_remove.append(deferred)


class ColorRampElementExporter(SpecificExporter[bpy.types.ColorRampElement]):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class ColorRampElementsImporter(SpecificImporter[bpy.types.ColorRampElements]):
    def deserialize(self):
        # Can't start from zero here https://projects.blender.org/blender/blender/issues/150171
        number_needed = len(self.serialization["items"])

        if number_needed == 0:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
color ramps need at least one element"""
            )

        # this will probably not happen
        while len(self.getter()) > number_needed:
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: removing element")
            self.getter().remove(self.getter()[-1])

        while len(self.getter()) < number_needed:
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding element")
            self.getter().new(position=0)


class SimulationInputExporter(SpecificExporter[bpy.types.GeometryNodeSimulationInput]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])
        if self.obj.paired_output is None:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
Having no paired output for simulation nodes isn't supported"""
            )
        no_clobber(data, "paired_output", self.obj.paired_output.name)

        return data


class SimulationInputImporter(SpecificImporter[bpy.types.GeometryNodeSimulationInput]):
    def deserialize(self):
        self.import_all_simple_writable_properties()

        # if this fails it's easier to debug here
        output = self.serialization["paired_output"]

        def deferred():
            if not self.getter().pair_with_output(
                self.importer.current_tree.nodes[output]
            ):
                raise RuntimeError(
                    f"{self.from_root.to_str()}: failed to pair with {output}"
                )
            self.import_properties_from_id_list([INPUTS, OUTPUTS])

        # defer connection until we've created the output node
        # only then, import the sockets
        self.importer.create_special_node_connections.append(deferred)


class SimulationOutputExporter(
    SpecificExporter[bpy.types.GeometryNodeSimulationOutput]
):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, "state_items"]
        )


class SimulationOutputImporter(
    SpecificImporter[bpy.types.GeometryNodeSimulationOutput]
):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the state_items implicitly create sockets
            ["state_items", INPUTS, OUTPUTS]
        )


class SimulationOutputItemsImporter(
    SpecificImporter[bpy.types.NodeGeometrySimulationOutputItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization["items"]:
            name = _or_default(item[DATA], bpy.types.SimulationStateItem, "name")
            socket_type = _or_default(
                item[DATA], bpy.types.SimulationStateItem, "socket_type"
            )
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


# now they are cooked and ready to use ~ bon appétit
BUILT_IN_EXPORTER = _BUILT_IN_EXPORTER
BUILT_IN_IMPORTER = _BUILT_IN_IMPORTER
