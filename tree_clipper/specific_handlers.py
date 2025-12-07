import bpy

from typing import Type

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
    ITEMS,
    BL_IDNAME,
    NAME,
)

# to help prevent typos, especially when used multiple times
ACTIVE = "active"
AUTO_REMOVE = "auto_remove"
CAPTURE_ITEMS = "capture_items"
DATA_TYPE = "data_type"
DEFAULT_CLOSED = "default_closed"
DESCRIPTION = "description"
DIMENSIONS = "dimensions"
ENUM_ITEMS = "enum_items"
FROM_NODE = "from_node"
FROM_SOCKET = "from_socket"
INPUTS = "inputs"
IN_OUT = "in_out"
ITEM_TYPE = "item_type"
ITEM_TYPE_SOCKET = "SOCKET"
ITEM_TYPE_PANEL = "PANEL"
ITEMS_TREE = "items_tree"
MULTI_INPUT_SORT_ID = "multi_input_sort_id"
NODE_TREE_INTERFACE = "interface"
NODE_TREE_LINKS = "links"
NODE_TREE_NODES = "nodes"
OUTPUTS = "outputs"
PAIRED_OUTPUT = "paired_output"
PARENT = "parent"
PARENT_INDEX = "parent_index"
REPEAT_ITEMS = "repeat_items"
SOCKET_TYPE = "socket_type"
STATE_ITEMS = "state_items"
TO_NODE = "to_node"
TO_SOCKET = "to_socket"
VIEWER_ITEMS = "viewer_items"
ANNOTATION = "annotation"
LOCATION = "location"
CURVES = "curves"
DISPLAY_SETTINGS = "display_settings"
DISPLAY_DEVICE = "display_device"
VIEW_SETTINGS = "view_settings"
VIEW_TRANSFORM = "view_transform"
LOOK = "look"
INPUT_ITEMS = "input_items"
OUTPUT_ITEMS = "output_items"
FORMAT_ITEMS = "format_items"


# this might not be needed anymore in many cases, because
# due to https://github.com/Algebraic-UG/tree_clipper/issues/59
# we don't skip defaults anymore
def _or_default(serialization: dict, ty: Type[bpy.types.bpy_struct], identifier: str):
    return serialization.get(identifier, ty.bl_rna.properties[identifier].default)  # ty: ignore[unresolved-attribute]


def _import_node_parent(specific_importer: SpecificImporter) -> None:
    assert isinstance(specific_importer.getter(), bpy.types.Node)

    parent_id = specific_importer.serialization[PARENT]
    if parent_id is None:
        return

    assert isinstance(parent_id, int)

    def deferred():
        specific_importer.getter().parent = specific_importer.importer.getters[
            parent_id
        ]()  # ty: ignore[invalid-assignment]

    specific_importer.importer.defer_after_nodes_before_links.append(deferred)


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
            [NODE_TREE_INTERFACE, NODE_TREE_NODES, NODE_TREE_LINKS, BL_IDNAME],
            [ANNOTATION],
        )


class NodeTreeImporter(SpecificImporter[bpy.types.NodeTree]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            [NODE_TREE_INTERFACE, NODE_TREE_NODES, ANNOTATION]
        )

        # one thing that requires this is the repeat zone
        # after this more sockets are available for linking
        for func in self.importer.defer_after_nodes_before_links:
            func()
        self.importer.defer_after_nodes_before_links.clear()

        self.import_properties_from_id_list([NODE_TREE_LINKS])

        # now that the links exist they won't be removed immediately
        for func in self.importer.set_auto_remove:
            func()
        self.importer.set_auto_remove.clear()


class NodesImporter(SpecificImporter[bpy.types.Nodes]):
    def deserialize(self):
        self.getter().clear()
        active_id = self.serialization.get(ACTIVE, None)
        for node in self.serialization[ITEMS]:
            bl_idname = node[DATA][BL_IDNAME]
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding {bl_idname}")
            new_node = self.getter().new(type=bl_idname)
            # it's important to do this immediately because renaming later can change more than one name
            new_node.name = _or_default(self.serialization, bpy.types.Node, NAME)
            if node[ID] == active_id:
                self.getter().active = new_node


class InterfaceExporter(SpecificExporter[bpy.types.NodeTreeInterface]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list([ITEMS_TREE])


class InterfaceImporter(SpecificImporter[bpy.types.NodeTreeInterface]):
    def deserialize(self):
        self.getter().clear()

        def get_type(data: dict):
            item_type = _or_default(data, bpy.types.NodeTreeInterfaceItem, ITEM_TYPE)
            if item_type == ITEM_TYPE_SOCKET:
                return bpy.types.NodeTreeInterfaceSocket
            if item_type == ITEM_TYPE_PANEL:
                return bpy.types.NodeTreeInterfacePanel
            raise RuntimeError(
                f"item_type neither {ITEM_TYPE_SOCKET} nor {ITEM_TYPE_PANEL} but {item_type}"
            )

        for item in self.serialization[ITEMS_TREE][DATA][ITEMS]:
            data = item[DATA]
            ty = get_type(data)
            name = _or_default(data, ty, NAME)
            description = _or_default(data, ty, DESCRIPTION)

            if PARENT_INDEX in data:
                parent_index = data[PARENT_INDEX]
                assert parent_index < len(self.getter().items_tree)
                parent = self.getter().items_tree[parent_index]
            else:
                parent = None

            if ty == bpy.types.NodeTreeInterfaceSocket:
                new_item = self.getter().new_socket(
                    name=name,
                    description=description,
                    in_out=_or_default(data, ty, "in_out"),
                    socket_type=data[SOCKET_TYPE],
                    parent=parent,
                )
            else:
                new_item = self.getter().new_panel(
                    name=name,
                    description=description,
                    default_closed=_or_default(data, ty, DEFAULT_CLOSED),
                )
                if parent is not None:
                    self.getter().move_to_parent(
                        item=new_item,
                        parent=parent,
                        to_position=len(parent.interface_items),
                    )

        self.import_all_simple_writable_properties_and_list([ITEMS_TREE])


class TreeSocketExporter(SpecificExporter[bpy.types.NodeTreeInterfaceSocket]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list([ITEM_TYPE, IN_OUT])
        if self.obj.parent.index >= 0:
            no_clobber(data, PARENT_INDEX, self.obj.parent.index)
        return data


class TreePanelExporter(SpecificExporter[bpy.types.NodeTreeInterfacePanel]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list([ITEM_TYPE])
        if self.obj.parent.index >= 0:
            no_clobber(data, PARENT_INDEX, self.obj.parent.index)
        return data


class TreeItemImporter(SpecificImporter[bpy.types.NodeTreeInterfaceItem]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class TreePanelImporter(SpecificImporter[bpy.types.NodeTreeInterfacePanel]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class NodeExporter(SpecificExporter[bpy.types.Node]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME],
            [PARENT],
        )


class NodeImporter(SpecificImporter[bpy.types.Node]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])
        _import_node_parent(self)


class NodeInputsImporter(SpecificImporter[bpy.types.NodeInputs]):
    def deserialize(self):
        expected = len(self.serialization[ITEMS])
        current = len(self.getter())
        if current != expected:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
expected {expected} in-sockets but found {current}
we currently don't support creating sockets"""
            )


class NodeOutputsImporter(SpecificImporter[bpy.types.NodeOutputs]):
    def deserialize(self):
        expected = len(self.serialization[ITEMS])
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
        # https://github.com/Algebraic-UG/tree_clipper/issues/43
        if DIMENSIONS in self.serialization:
            self.getter().dimensions = self.serialization[DIMENSIONS]  # ty: ignore[invalid-assignment]
        self.import_all_simple_writable_properties()


class LinkExporter(SpecificExporter[bpy.types.NodeLink]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list(
            [MULTI_INPUT_SORT_ID]
        )

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
        for link in self.serialization[ITEMS]:
            data = link[DATA]
            from_node = data[FROM_NODE]
            from_socket = data[FROM_SOCKET]
            to_node = data[TO_NODE]
            to_socket = data[TO_SOCKET]
            if self.importer.debug_prints:
                print(
                    f"{self.from_root.to_str()}: linking {from_node}, {from_socket} to {to_node}, {to_socket}"
                )
            new_link = self.getter().new(
                input=self.importer.current_tree.nodes[from_node].outputs[from_socket],
                output=self.importer.current_tree.nodes[to_node].inputs[to_socket],
            )

            # bubble the link to the correct position
            multi_input_sort_id = _or_default(
                data, bpy.types.NodeLink, MULTI_INPUT_SORT_ID
            )
            multi_links = (
                self.importer.current_tree.nodes[to_node].inputs[to_socket].links
            )
            assert new_link.multi_input_sort_id + 1 == len(multi_links)
            while new_link.multi_input_sort_id > multi_input_sort_id:
                new_link.swap_multi_input_sort_id(
                    next(
                        other
                        for other in multi_links
                        if other.multi_input_sort_id == new_link.multi_input_sort_id - 1
                    )
                )


class LinkImporter(SpecificImporter[bpy.types.NodeLink]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class MenuSwitchExporter(SpecificExporter[bpy.types.GeometryNodeMenuSwitch]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME, ENUM_ITEMS],
            [PARENT],
        )


class MenuSwitchImporter(SpecificImporter[bpy.types.GeometryNodeMenuSwitch]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the enum_items implicitly create sockets
            [ENUM_ITEMS, INPUTS, OUTPUTS],
        )
        _import_node_parent(self)


class MenuSwitchItemsImporter(SpecificImporter[bpy.types.NodeMenuSwitchItems]):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            name = _or_default(item[DATA], bpy.types.NodeEnumItem, NAME)
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name}")
            self.getter().new(name=name)


class CaptureAttrExporter(SpecificExporter[bpy.types.GeometryNodeCaptureAttribute]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME, CAPTURE_ITEMS],
            [PARENT],
        )


class CaptureAttrImporter(SpecificImporter[bpy.types.GeometryNodeCaptureAttribute]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the capture_items implicitly create sockets
            [CAPTURE_ITEMS, INPUTS, OUTPUTS],
        )
        _import_node_parent(self)


class CaptureAttrItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryCaptureAttributeItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            name = _or_default(item[DATA], bpy.types.NodeEnumItem, NAME)
            socket_type = _map_attribute_type_to_socket_type(
                _or_default(
                    item[DATA], bpy.types.NodeGeometryCaptureAttributeItem, DATA_TYPE
                )
            )
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


class RepeatInputExporter(SpecificExporter[bpy.types.GeometryNodeRepeatInput]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME],
            [PARENT],
        )
        if self.obj.paired_output is None:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
Having no paired output for repeat nodes isn't supported"""
            )
        no_clobber(data, PAIRED_OUTPUT, self.obj.paired_output.name)

        return data


class RepeatInputImporter(SpecificImporter[bpy.types.GeometryNodeRepeatInput]):
    def deserialize(self):
        self.import_all_simple_writable_properties()

        # if this fails it's easier to debug here
        output = self.serialization[PAIRED_OUTPUT]

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
        self.importer.defer_after_nodes_before_links.append(deferred)
        _import_node_parent(self)


class RepeatOutputExporter(SpecificExporter[bpy.types.GeometryNodeRepeatOutput]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME, REPEAT_ITEMS],
            [PARENT],
        )


class RepeatOutputImporter(SpecificImporter[bpy.types.GeometryNodeRepeatOutput]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the repeat_items implicitly create sockets
            [REPEAT_ITEMS, INPUTS, OUTPUTS]
        )
        _import_node_parent(self)


class RepeatOutputItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryRepeatOutputItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            name = _or_default(item[DATA], bpy.types.NodeEnumItem, NAME)
            socket_type = _or_default(item[DATA], bpy.types.RepeatItem, SOCKET_TYPE)
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


class IndexItemExporter(SpecificExporter[bpy.types.IndexSwitchItem]):
    def serialize(self):
        return {}


class IndexItemsImporter(SpecificImporter[bpy.types.NodeIndexSwitchItems]):
    def deserialize(self):
        self.getter().clear()
        for _ in self.serialization[ITEMS]:
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding index")
            self.getter().new()


class ViewerSpecificExporter(SpecificExporter[bpy.types.GeometryNodeViewer]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME, VIEWER_ITEMS],
            [PARENT],
        )


class ViewerImporter(SpecificImporter[bpy.types.GeometryNodeViewer]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the viewer_items implicitly create sockets
            [VIEWER_ITEMS, INPUTS, OUTPUTS],
        )
        _import_node_parent(self)


class ViewerItemsImporter(SpecificImporter[bpy.types.NodeGeometryViewerItems]):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            data = item[DATA]
            name = _or_default(data, bpy.types.NodeGeometryViewerItem, NAME)
            socket_type = _or_default(
                data, bpy.types.NodeGeometryViewerItem, SOCKET_TYPE
            )

            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")

            self.getter().new(socket_type=socket_type, name=name)


class ViewerItemImporter(SpecificImporter[bpy.types.NodeGeometryViewerItem]):
    def deserialize(self):
        auto_remove = _or_default(
            self.serialization, bpy.types.NodeGeometryViewerItem, AUTO_REMOVE
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
        number_needed = len(self.serialization[ITEMS])

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
        data = self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME],
            [PARENT],
        )
        if self.obj.paired_output is None:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
Having no paired output for simulation nodes isn't supported"""
            )
        no_clobber(data, PAIRED_OUTPUT, self.obj.paired_output.name)

        return data


class SimulationInputImporter(SpecificImporter[bpy.types.GeometryNodeSimulationInput]):
    def deserialize(self):
        self.import_all_simple_writable_properties()

        # if this fails it's easier to debug here
        output = self.serialization[PAIRED_OUTPUT]

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
        self.importer.defer_after_nodes_before_links.append(deferred)
        _import_node_parent(self)


class SimulationOutputExporter(
    SpecificExporter[bpy.types.GeometryNodeSimulationOutput]
):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME, STATE_ITEMS],
            [PARENT],
        )


class SimulationOutputImporter(
    SpecificImporter[bpy.types.GeometryNodeSimulationOutput]
):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the state_items implicitly create sockets
            [STATE_ITEMS, INPUTS, OUTPUTS]
        )
        _import_node_parent(self)


class SimulationOutputItemsImporter(
    SpecificImporter[bpy.types.NodeGeometrySimulationOutputItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            name = _or_default(item[DATA], bpy.types.SimulationStateItem, NAME)
            socket_type = _or_default(
                item[DATA], bpy.types.SimulationStateItem, SOCKET_TYPE
            )
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


class NodeClosureInputExporter(SpecificExporter[bpy.types.NodeClosureInput]):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME],
            [PARENT],
        )
        if self.obj.paired_output is None:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
Having no paired output for closure nodes isn't supported"""
            )
        no_clobber(data, PAIRED_OUTPUT, self.obj.paired_output.name)

        return data


class NodeClosureInputImporter(SpecificImporter[bpy.types.NodeClosureInput]):
    def deserialize(self):
        self.import_all_simple_writable_properties()

        # if this fails it's easier to debug here
        output = self.serialization[PAIRED_OUTPUT]

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
        self.importer.defer_after_nodes_before_links.append(deferred)
        _import_node_parent(self)


class NodeClosureOutputExporter(SpecificExporter[bpy.types.NodeClosureOutput]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [INPUTS, OUTPUTS, BL_IDNAME, INPUT_ITEMS, OUTPUT_ITEMS],
            [PARENT],
        )


class NodeClosureOutputImporter(SpecificImporter[bpy.types.NodeClosureOutput]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the items implicitly create sockets
            [INPUT_ITEMS, OUTPUT_ITEMS, INPUTS, OUTPUTS]
        )
        _import_node_parent(self)


class NodeClosureInputItems(SpecificImporter[bpy.types.NodeClosureInputItems]):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            name = _or_default(item[DATA], bpy.types.NodeClosureInputItem, NAME)
            socket_type = _or_default(
                item[DATA], bpy.types.NodeClosureInputItem, SOCKET_TYPE
            )
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


class NodeClosureOutputItems(SpecificImporter[bpy.types.NodeClosureOutputItems]):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            name = _or_default(item[DATA], bpy.types.NodeClosureOutputItem, NAME)
            socket_type = _or_default(
                item[DATA], bpy.types.NodeClosureOutputItem, SOCKET_TYPE
            )
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


class RerouteExporter(SpecificExporter[bpy.types.NodeReroute]):
    """The reroute's sockets are not needed and can cause problems"""

    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            [BL_IDNAME],
            [PARENT],
        )


class RerouteImporter(SpecificImporter[bpy.types.NodeReroute]):
    """The reroute's sockets are not needed and can cause problems"""

    def deserialize(self):
        self.import_all_simple_writable_properties()
        _import_node_parent(self)


class CurveMapPointExporter(SpecificExporter[bpy.types.CurveMapPoint]):
    f"""The container constructs them using the {LOCATION}"""

    def serialize(self):
        return self.export_all_simple_writable_properties()


class CurveMapPointsImporter(SpecificImporter[bpy.types.CurveMapPoints]):
    f"""The {LOCATION} needs to be picked apart into argumets
and there are always at least two points, so we must skip first and last"""

    def deserialize(self):
        for item in self.serialization[ITEMS][1:-1]:
            location = item[DATA][LOCATION]
            self.getter().new(position=location[0], value=location[1])


class CurveMappingImporter(SpecificImporter[bpy.types.CurveMapping]):
    """After the points are added to the curves we need to call update"""

    def deserialize(self):
        self.import_all_simple_writable_properties_and_list([CURVES])

        def deferred():
            self.getter().update()

        self.importer.defer_after_nodes_before_links.append(deferred)


class ConvertToDisplayImporter(
    SpecificImporter[bpy.types.CompositorNodeConvertToDisplay]
):
    f"""The properties on this one are special.
The properties of the pointees {DISPLAY_SETTINGS} and {VIEW_SETTINGS} are set implicitly
by setting certain enums values.
They also have an implicit ordering, first the display needs to be set, then the view."""

    def deserialize(self):
        self.import_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])
        _import_node_parent(self)

        display_device = self.serialization[DISPLAY_SETTINGS][DATA][DISPLAY_DEVICE]
        view_transform = self.serialization[VIEW_SETTINGS][DATA][VIEW_TRANSFORM]
        look = self.serialization[VIEW_SETTINGS][DATA][LOOK]
        self.getter().display_settings.display_device = display_device  # ty: ignore[invalid-assignment]
        self.getter().view_settings.view_transform = view_transform  # ty: ignore[invalid-assignment]
        self.getter().view_settings.look = look  # ty: ignore[invalid-assignment]


class EvalClosureInputItemExporter(
    SpecificExporter[bpy.types.NodeEvaluateClosureInputItem]
):
    f"""We need {SOCKET_TYPE} and {NAME}, both are simple & writable"""

    def serialize(self):
        return self.export_all_simple_writable_properties()


class EvalClosureInputItemsImporter(
    SpecificImporter[bpy.types.NodeEvaluateClosureInputItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class EvalClosureOutputItemExporter(
    SpecificExporter[bpy.types.NodeEvaluateClosureOutputItem]
):
    f"""We need {SOCKET_TYPE} and {NAME}, both are simple & writable"""

    def serialize(self):
        return self.export_all_simple_writable_properties()


class EvalClosureOutputItemsImporter(
    SpecificImporter[bpy.types.NodeEvaluateClosureOutputItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class FormatStringNodeImporter(SpecificImporter[bpy.types.FunctionNodeFormatString]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the format_items implicitly create sockets
            [FORMAT_ITEMS, INPUTS, OUTPUTS]
        )
        _import_node_parent(self)


class FormatStringItemExporter(
    SpecificExporter[bpy.types.NodeFunctionFormatStringItem]
):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class FormatStringItemsImporter(
    SpecificImporter[bpy.types.NodeFunctionFormatStringItems]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


# now they are cooked and ready to use ~ bon appétit
BUILT_IN_EXPORTER = _BUILT_IN_EXPORTER
BUILT_IN_IMPORTER = _BUILT_IN_IMPORTER
