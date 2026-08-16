from typing import Any

import bpy

from .common import (
    BL_IDNAME,
    DATA,
    DEFAULT_VALUE,
    DIMENSIONS,
    GETTER,
    ID,
    ITEMS,
    NAME,
    NODE_TREE,
    no_clobber,
)
from .import_nodes import Importer
from .specific_abstract import (
    _BUILT_IN_EXPORTER,
    _BUILT_IN_IMPORTER,
    SpecificExporter,
    SpecificImporter,
)

# to help prevent typos, especially when used multiple times
ACTIVE = "active"
AUTO_REMOVE = "auto_remove"
CAPTURE_ITEMS = "capture_items"
DATA_TYPE = "data_type"
DEFAULT_CLOSED = "default_closed"
DESCRIPTION = "description"
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
BUNDLE_ITEMS = "bundle_items"
LAYER = "layer"
SCENE = "scene"
GENERATION_ITEMS = "generation_items"
MAIN_ITEMS = "main_items"
BAKE_ITEMS = "bake_items"
ACTIVE_ITEM = "active_item"
GRID_ITEMS = "grid_items"
VIEW = "view"
IMAGE = "image"
ENTRIES = "entries"
FORMAT = "format"
IS_PANEL_TOGGLE = "is_panel_toggle"
ENABLED = "enabled"
SINGLE_INPUT = "single_input"
SINGLE_OUTPUT = "single_output"
FILE_OUTPUT_ITEMS = "file_output_items"
INDEX_SWITCH_ITEMS = "index_switch_items"
INPUT_TYPE = "input_type"
CURVE_MAPPING = "curve_mapping"
WHITE_BALANCE_WHITEPOINT = "white_balance_whitepoint"
WIDTH = "width"
ACTIVE_INDEX = "active_index"
ACTIVE_ITEM_INDEX = "active_item_index"
ACTIVE_INPUT_INDEX = "active_input_index"
ACTIVE_OUTPUT_INDEX = "active_output_index"
ACTIVE_GENERATION_INDEX = "active_generation_index"
ACTIVE_MAIN_INDEX = "active_main_index"
DEFAULT_INPUT = "default_input"
LIST_ITEMS = "list_items"
ADD = "add"
REMOVE = "remove"
FONT = "font"
OVERFLOW = "overflow"
ALIGN_X = "align_x"
ALIGN_Y = "align_y"
PIVOT_MODE = "pivot_mode"
TEXTBOX_STATE = "textbox_state"
SAMPLE_ATTRIBUTE_ITEMS = "sample_attribute_items"
OPERATION = "operation"
SUBSURFACE_METHOD = "subsurface_method"
SOCKET_IDNAME = "socket_idname"
PANEL_STATES = "panel_states"

if (bpy.app.version[0] == 5 and bpy.app.version[1] >= 2) or bpy.app.version[0] > 5:
    NODE_GENERIC_COLLECTIONS = [INPUTS, OUTPUTS, PANEL_STATES]
else:
    NODE_GENERIC_COLLECTIONS = [INPUTS, OUTPUTS]


# this might not be needed anymore in many cases, because
# due to https://github.com/Algebraic-UG/tree_clipper/issues/59
# we don't skip defaults anymore
def _or_default(serialization: dict, ty: type[bpy.types.bpy_struct], identifier: str):
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
        ]()

    specific_importer.importer.defer_after_nodes_before_links.append(deferred)


# This is needed for manually mapping sockets for backwards compatibility
def map_socket(*, specific_importer: SpecificImporter, socket_name: str, input: bool):
    old_socket = next(
        (
            old
            for old in specific_importer.serialization[INPUTS if input else OUTPUTS][
                DATA
            ][ITEMS]
            if old[DATA][NAME] == socket_name
        ),
        None,
    )
    assert old_socket is not None, f"Missing old socket {socket_name}"
    if input:
        specific_importer.importer._import_obj(
            getter=lambda: specific_importer.getter().inputs[socket_name],
            serialization=old_socket,
            from_root=specific_importer.from_root.add(f"Mapped input '{socket_name}'"),
        )
    else:
        specific_importer.importer._import_obj(
            getter=lambda: specific_importer.getter().outputs[socket_name],
            serialization=old_socket,
            from_root=specific_importer.from_root.add(f"Mapped output '{socket_name}'"),
        )


def map_socket_input(*, importer: SpecificImporter, name: str):
    map_socket(specific_importer=importer, socket_name=name, input=True)


def map_socket_output(*, importer: SpecificImporter, name: str):
    map_socket(specific_importer=importer, socket_name=name, input=False)


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
        data = self.export_all_simple_writable_properties_and_list(
            [NODE_TREE_INTERFACE, NODE_TREE_NODES, BL_IDNAME],
            [ANNOTATION],
        )

        # We can't export all links, we have to skip the ones than have a from_socket
        # that is from a Render Layer node and is disabled.
        # The normal collection exporting can't filter so we recreate it here
        # with some debug prints to track which links we skip.
        # see https://github.com/Algebraic-UG/tree_clipper/issues/84

        links = self.exporter._export_obj(
            obj=self.obj.links,
            from_root=self.from_root.add_prop(
                self.obj.bl_rna.properties[NODE_TREE_LINKS]
            ),
        )

        link_items = []
        for i, link in enumerate(self.obj.links):
            from_root_link = self.from_root.add(f"[{i}] (unnamed)")

            if (
                isinstance(link.from_node, bpy.types.CompositorNodeRLayers)
                and not link.from_socket.enabled
            ):
                warning = (
                    f"{from_root_link.to_str()} Skipping link with disabled socket"
                )
                self.exporter.report.warnings.append(warning)
                if self.exporter.debug_prints:
                    print(warning)
                continue

            link_items.append(
                self.exporter._export_obj(
                    obj=link,
                    from_root=from_root_link,
                )
            )

        no_clobber(links[DATA], ITEMS, link_items)
        no_clobber(data, NODE_TREE_LINKS, links)

        return data


class NodeTreeImporter(SpecificImporter[bpy.types.NodeTree]):
    def deserialize(self):
        if isinstance(self.getter(), bpy.types.ShaderNodeTree):
            forbidden = [NAME]
        else:
            forbidden = []

        self.import_all_simple_writable_properties(forbidden)
        self.import_properties_from_id_list(
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


class NodesImporter(SpecificImporter[bpy.types.Nodes]):  # ty:ignore[invalid-type-arguments]
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

            def get_parent(data) -> None | bpy.types.NodeTreeInterfacePanel:
                if PARENT_INDEX in data:
                    parent_index = data[PARENT_INDEX]
                    assert parent_index < len(self.getter().items_tree)
                    parent = self.getter().items_tree[parent_index]
                    assert isinstance(parent, bpy.types.NodeTreeInterfacePanel)
                    return parent
                else:
                    return None

            if ty == bpy.types.NodeTreeInterfaceSocket:
                if self.importer.debug_prints:
                    print(
                        f"{self.from_root.to_str()}: adding socket {name}, {data[SOCKET_TYPE]}"
                    )
                new_item = self.getter().new_socket(
                    name=name,
                    description=description,
                    in_out=_or_default(data, ty, "in_out"),
                    socket_type=data[SOCKET_TYPE],
                    parent=get_parent(data),
                )
                if isinstance(new_item, bpy.types.NodeTreeInterfaceSocketBool):
                    new_item.is_panel_toggle = data[IS_PANEL_TOGGLE]
            else:
                if self.importer.debug_prints:
                    print(f"{self.from_root.to_str()}: adding panel {name}")
                new_item = self.getter().new_panel(
                    name=name,
                    description=description,
                    default_closed=_or_default(data, ty, DEFAULT_CLOSED),
                )
                parent = get_parent(data)
                if parent is not None:
                    self.getter().move_to_parent(
                        item=new_item,
                        parent=parent,
                        to_position=len(parent.interface_items),
                    )

        self.import_all_simple_writable_properties_and_list([ITEMS_TREE])


class TreePanelExporter(SpecificExporter[bpy.types.NodeTreeInterfacePanel]):
    """We need to skip the sub items, they're already in the interface-level list"""

    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list([ITEM_TYPE])
        if self.obj.parent.index >= 0:  # ty:ignore[unresolved-attribute]
            no_clobber(data, PARENT_INDEX, self.obj.parent.index)  # ty:ignore[unresolved-attribute]
        return data


class TreeSocketExporter(SpecificExporter[bpy.types.NodeTreeInterfaceSocket]):
    """We need to add in_out which isn't writable"""

    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list([IN_OUT, ITEM_TYPE])

        # https://github.com/Algebraic-UG/tree_clipper/issues/203
        if DEFAULT_INPUT not in data:
            data[DEFAULT_INPUT] = "VALUE"

        if self.obj.parent.index >= 0:  # ty:ignore[unresolved-attribute]
            no_clobber(data, PARENT_INDEX, self.obj.parent.index)  # ty:ignore[unresolved-attribute]

        # https://github.com/Algebraic-UG/tree_clipper/issues/111
        if isinstance(self.exporter.current_tree, bpy.types.ShaderNodeTree):
            data.pop(DEFAULT_INPUT, None)  # can be missing

        return data


class TreeSocketImporter(SpecificImporter[bpy.types.NodeTreeInterfaceSocket]):
    def deserialize(self):
        # https://github.com/Algebraic-UG/tree_clipper/issues/43
        if DIMENSIONS in self.serialization:
            prop = self.getter().bl_rna.properties[DIMENSIONS]
            if self.importer.debug_prints:
                print(
                    f"{self.from_root.add_prop(prop).to_str()}: immediately set dimension"
                )
            dimensions = self.serialization[DIMENSIONS]
            self.getter().dimensions = dimensions  # ty: ignore[invalid-assignment]

        # importing the socket type resets the dimension!
        self.import_all_simple_writable_properties([SOCKET_TYPE])


class TreePanelImporter(SpecificImporter[bpy.types.NodeTreeInterfacePanel]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class NodeExporter(SpecificExporter[bpy.types.Node]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME],
            [PARENT],
        )


class NodeImporter(SpecificImporter[bpy.types.Node]):
    def deserialize(self):
        # this is the case for many node types that would otherwise need a specific handler
        if DATA_TYPE in self.serialization:
            self.import_properties_from_id_list([DATA_TYPE])
        if SOCKET_TYPE in self.serialization:
            self.import_properties_from_id_list([SOCKET_TYPE])
        if OPERATION in self.serialization:
            self.import_properties_from_id_list([OPERATION])

        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


class CompositorNodeGroupImporter(SpecificImporter[bpy.types.CompositorNodeGroup]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            [NODE_TREE] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class GeometryNodeGroupImporter(SpecificImporter[bpy.types.GeometryNodeGroup]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            [NODE_TREE] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class ShaderNodeGroupImporter(SpecificImporter[bpy.types.ShaderNodeGroup]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            [NODE_TREE] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class TextureNodeGroupImporter(SpecificImporter[bpy.types.TextureNodeGroup]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            [NODE_TREE] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


# https://github.com/Algebraic-UG/tree_clipper/issues/205
def remove_disabled_in_old_file(importer: Importer, serialization: dict[str, Any]):
    if (bpy.app.version[0] == 5 and bpy.app.version[1] >= 2) or bpy.app.version[0] > 5:
        if importer.blender_version[0] == 5 and importer.blender_version[1] < 2:
            for disabled in [
                s[ID] for s in serialization[ITEMS] if not s[DATA][ENABLED]
            ]:
                if importer.debug_prints:
                    print(
                        f"Removing disabled socket for backward compatibility: {disabled}"
                    )
                if disabled in importer.disabled_ids:
                    raise RuntimeError("Double disabled: {disabled}")
                importer.disabled_ids.add(disabled)
            serialization[ITEMS] = [s for s in serialization[ITEMS] if s[DATA][ENABLED]]


class NodeInputsImporter(SpecificImporter[bpy.types.NodeInputs]):  # ty:ignore[invalid-type-arguments]
    def deserialize(self):
        expected = len(self.serialization[ITEMS])
        current = len(self.getter())
        if current != expected:
            remove_disabled_in_old_file(self.importer, self.serialization)
            expected = len(self.serialization[ITEMS])
            if current != expected:
                raise RuntimeError(
                    f"""{self.from_root.to_str()}
expected {expected} in-sockets but found {current}
we currently don't support creating sockets"""
                )


class NodeOutputsImporter(SpecificImporter[bpy.types.NodeOutputs]):  # ty:ignore[invalid-type-arguments]
    def deserialize(self):
        expected = len(self.serialization[ITEMS])
        current = len(self.getter())
        if current != expected:
            remove_disabled_in_old_file(self.importer, self.serialization)
            expected = len(self.serialization[ITEMS])
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
            prop = self.getter().bl_rna.properties[DIMENSIONS]
            if self.importer.debug_prints:
                print(
                    f"{self.from_root.add_prop(prop).to_str()}: immediately set dimension"
                )
            dimensions = self.serialization[DIMENSIONS]
            self.getter().dimensions = dimensions  # ty: ignore[invalid-assignment]
            if DEFAULT_VALUE in self.serialization:
                default_value = self.serialization[DEFAULT_VALUE]
                if len(default_value) > dimensions:
                    if self.importer.debug_prints:
                        print(
                            f"{self.from_root.add_prop(prop).to_str()}: fixing dimension mismatch"
                        )
                    self.serialization[DEFAULT_VALUE] = default_value[:dimensions]

        # importing the socket type resets the dimension!
        self.import_all_simple_writable_properties([SOCKET_TYPE])


class LinkExporter(SpecificExporter[bpy.types.NodeLink]):
    def serialize(self):
        # https://github.com/Algebraic-UG/tree_clipper/issues/114
        if self.obj.to_socket.is_multi_input:  # ty:ignore[unresolved-attribute]
            additional_props = [MULTI_INPUT_SORT_ID]
        else:
            additional_props = []
        return self.export_all_simple_writable_properties_and_list(
            additional_props,
            [FROM_SOCKET, TO_SOCKET],
        )


class LinksImporter(SpecificImporter[bpy.types.NodeLinks]):  # ty:ignore[invalid-type-arguments]
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/205
            def connected_to_disabled(link):
                return (
                    link[DATA][FROM_SOCKET] in self.importer.disabled_ids
                    or link[DATA][TO_SOCKET] in self.importer.disabled_ids
                )

            if self.importer.debug_prints:
                for link in self.serialization[ITEMS]:
                    if connected_to_disabled(link):
                        print(
                            f"Removing link from/to disabled for backward compatibility: {link[ID]}"
                        )
            self.serialization[ITEMS] = [
                link
                for link in self.serialization[ITEMS]
                if not connected_to_disabled(link)
            ]

        multi_links = []
        for i, link in enumerate(self.serialization[ITEMS]):
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: Importing link {link[ID]}")

            data = link[DATA]
            from_socket_id = data[FROM_SOCKET]
            to_socket_id = data[TO_SOCKET]

            assert from_socket_id in self.importer.getters, (
                f"Socket with Id {from_socket_id} not deserialized yet"
            )
            assert to_socket_id in self.importer.getters, (
                f"Socket with Id {to_socket_id} not deserialized yet"
            )

            from_socket = self.importer.getters[from_socket_id]()
            to_socket = self.importer.getters[to_socket_id]()

            assert isinstance(from_socket, bpy.types.NodeSocket)
            assert isinstance(to_socket, bpy.types.NodeSocket)

            from_node = from_socket.node
            to_node = to_socket.node

            if self.importer.debug_prints:
                print(
                    f"{self.from_root.to_str()}: linking {from_node.name}, {from_socket.identifier} to {to_node.name}, {to_socket.identifier}"  # ty:ignore[unresolved-attribute]
                )

            self.getter().new(input=from_socket, output=to_socket)

            if isinstance(to_node, bpy.types.NodeReroute):
                continue
            if not to_socket.is_multi_input:
                continue

            multi_links.append(i)

        if self.importer.debug_prints:
            print(f"{self.from_root.to_str()}: multilinks are {multi_links}")

        for i in multi_links:
            link = self.getter()[i]
            multi_input_sort_id = self.serialization[ITEMS][i][DATA][
                MULTI_INPUT_SORT_ID
            ]

            if self.importer.debug_prints:
                print(
                    f"{self.from_root.to_str()}: putting link {i} in the correct place: {multi_input_sort_id}"
                )

            if link.multi_input_sort_id == multi_input_sort_id:
                continue

            other = next(
                (
                    other
                    for other in link.to_socket.links
                    if other.multi_input_sort_id == multi_input_sort_id
                ),
                None,
            )
            if other is None:
                raise RuntimeError(
                    f"No link is occupying sort id {multi_input_sort_id}"
                )

            link.swap_multi_input_sort_id(other)


class LinkImporter(SpecificImporter[bpy.types.NodeLink]):
    def deserialize(self):
        self.import_all_simple_writable_properties()


class MenuSwitchExporter(SpecificExporter[bpy.types.GeometryNodeMenuSwitch]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME, ENUM_ITEMS],
            [PARENT],
        )


class MenuSwitchImporter(SpecificImporter[bpy.types.GeometryNodeMenuSwitch]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the enum_items implicitly create sockets
            [ENUM_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS,
        )
        _import_node_parent(self)


class MenuSwitchItemsImporter(SpecificImporter[bpy.types.NodeMenuSwitchItems]):  # ty:ignore[invalid-type-arguments]
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            name = _or_default(item[DATA], bpy.types.NodeEnumItem, NAME)
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name}")
            self.getter().new(name=name)


class SwitchImporter(SpecificImporter[bpy.types.GeometryNodeSwitch]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the input_type resets sockets
            [INPUT_TYPE] + NODE_GENERIC_COLLECTIONS,
        )
        _import_node_parent(self)


class CaptureAttrExporter(SpecificExporter[bpy.types.GeometryNodeCaptureAttribute]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME, CAPTURE_ITEMS],
            [PARENT],
        )


def compat_5_1(importer: Importer) -> bool:
    current_is_at_least_5_2 = (
        bpy.app.version[0] == 5 and bpy.app.version[1] >= 2
    ) or bpy.app.version[0] > 5
    import_is_at_most_5_1 = (
        importer.blender_version[0] == 5 and importer.blender_version[1] < 2
    )
    return current_is_at_least_5_2 and import_is_at_most_5_1


class CameraInfoImporter(SpecificImporter[bpy.types.GeometryNodeCameraInfo]):
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/212
            self.serialization[OUTPUTS][DATA][ITEMS][2][DATA][DEFAULT_VALUE].pop()
            self.serialization[OUTPUTS][DATA][ITEMS][3][DATA][DEFAULT_VALUE].pop()
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


FAKE_MODE_SOCKET = {
    "id": -1,
    "data": {
        "name": "Mode",
        "description": "",
        "hide": False,
        "enabled": True,
        "link_limit": 1,
        "show_expanded": False,
        "hide_value": False,
        "pin_gizmo": False,
        "type": "MENU",
        "display_shape": "CIRCLE",
        "default_value": "From Start",
    },
}


class FindInStringImporter(SpecificImporter[bpy.types.FunctionNodeFindInString]):
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/182
            self.serialization[INPUTS][DATA][ITEMS].insert(2, FAKE_MODE_SOCKET)
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


class InputStringImporter(SpecificImporter[bpy.types.FunctionNodeInputString]):
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/211
            self.serialization[TEXTBOX_STATE] = None
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


FAKE_BASE_SOCKET = {
    "id": -1,
    "data": {
        "name": "Base",
        "description": "",
        "hide": False,
        "enabled": True,
        "link_limit": 1,
        "show_expanded": False,
        "hide_value": False,
        "pin_gizmo": False,
        "type": "INT",
        "display_shape": "CIRCLE",
        "default_value": 10,
    },
}

FAKE_PADDING_SOCKET = {
    "id": -1,
    "data": {
        "name": "Padding",
        "description": "",
        "hide": False,
        "enabled": True,
        "link_limit": 1,
        "show_expanded": False,
        "hide_value": False,
        "pin_gizmo": False,
        "type": "INT",
        "display_shape": "CIRCLE",
        "default_value": 0,
    },
}


class ValueToStringImporter(SpecificImporter[bpy.types.FunctionNodeValueToString]):
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/197
            self.serialization[INPUTS][DATA][ITEMS].insert(2, FAKE_BASE_SOCKET)
            self.serialization[INPUTS][DATA][ITEMS].insert(3, FAKE_PADDING_SOCKET)
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


class StringToValueImporter(SpecificImporter[bpy.types.FunctionNodeStringToValue]):
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/198
            self.serialization[INPUTS][DATA][ITEMS].insert(1, FAKE_BASE_SOCKET)
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


FAKE_QUALITY_SOCKET = {
    "id": -1,
    "data": {
        "name": "Quality",
        "description": "",
        "hide": False,
        "enabled": True,
        "link_limit": 1,
        "show_expanded": False,
        "hide_value": False,
        "pin_gizmo": False,
        "type": "INT",
        "display_shape": "LINE",
        "default_value": 3,
    },
}


class SubdivisionSurfaceImporter(
    SpecificImporter[bpy.types.GeometryNodeSubdivisionSurface]
):
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/210
            self.serialization[INPUTS][DATA][ITEMS].insert(5, FAKE_QUALITY_SOCKET)
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


FAKE_THIN_WALL_SOCKET = {
    "id": -1,
    "data": {
        "name": "Thin Wall",
        "description": "",
        "hide": False,
        "enabled": True,
        "link_limit": 1,
        "show_expanded": False,
        "hide_value": False,
        "pin_gizmo": False,
        "type": "BOOLEAN",
        "display_shape": "CIRCLE",
        "default_value": False,
    },
}


class PrincipledBSDFImporter(SpecificImporter[bpy.types.ShaderNodeBsdfPrincipled]):
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/209
            self.serialization[INPUTS][DATA][ITEMS].insert(5, FAKE_THIN_WALL_SOCKET)
            if self.serialization[SUBSURFACE_METHOD] == "RANDOM_WALK":
                self.serialization[SUBSURFACE_METHOD] = "RANDOM_WALK_LEGACY"
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


FAKE_SELECTION_SOCKET = {
    "id": -1,
    "data": {
        "name": "Selection",
        "description": "",
        "hide": False,
        "enabled": True,
        "link_limit": 1,
        "show_expanded": False,
        "hide_value": True,
        "pin_gizmo": False,
        "type": "BOOLEAN",
        "display_shape": "DIAMOND",
        "default_value": True,  # maybe this should be false for output
    },
}


class CaptureAttrImporter(SpecificImporter[bpy.types.GeometryNodeCaptureAttribute]):
    def deserialize(self):
        if compat_5_1(self.importer):
            # https://github.com/Algebraic-UG/tree_clipper/issues/208
            self.serialization[INPUTS][DATA][ITEMS].insert(1, FAKE_SELECTION_SOCKET)
            self.serialization[OUTPUTS][DATA][ITEMS].insert(1, FAKE_SELECTION_SOCKET)

        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the capture_items implicitly create sockets
            [CAPTURE_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS,
        )
        _import_node_parent(self)


class CaptureAttrItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryCaptureAttributeItems]  # ty:ignore[invalid-type-arguments]
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
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME],
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
                self.importer.current_tree.nodes[output]  # ty:ignore[unresolved-attribute]
            ):
                raise RuntimeError(
                    f"{self.from_root.to_str()}: failed to pair with {output}"
                )
            self.import_properties_from_id_list(NODE_GENERIC_COLLECTIONS)

        # defer connection until we've created the output node
        # only then, import the sockets
        self.importer.defer_after_nodes_before_links.append(deferred)
        _import_node_parent(self)


class RepeatOutputExporter(SpecificExporter[bpy.types.GeometryNodeRepeatOutput]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME, REPEAT_ITEMS],
            [PARENT],
        )


class RepeatOutputImporter(SpecificImporter[bpy.types.GeometryNodeRepeatOutput]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the repeat_items implicitly create sockets
            [REPEAT_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class RepeatOutputItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryRepeatOutputItems]  # ty:ignore[invalid-type-arguments]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            name = _or_default(item[DATA], bpy.types.NodeEnumItem, NAME)
            socket_type = _or_default(item[DATA], bpy.types.RepeatItem, SOCKET_TYPE)
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding item {name} {socket_type}")
            self.getter().new(socket_type=socket_type, name=name)


class IndexSwitchImporter(SpecificImporter[bpy.types.GeometryNodeIndexSwitch]):
    """We need to trigger the import of the data type first"""

    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            [INDEX_SWITCH_ITEMS] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class IndexItemExporter(SpecificExporter[bpy.types.IndexSwitchItem]):
    def serialize(self):
        return {}


class IndexItemsImporter(SpecificImporter[bpy.types.NodeIndexSwitchItems]):  # ty:ignore[invalid-type-arguments]
    def deserialize(self):
        self.getter().clear()
        for _ in self.serialization[ITEMS]:
            if self.importer.debug_prints:
                print(f"{self.from_root.to_str()}: adding index")
            self.getter().new()


class ViewerSpecificExporter(SpecificExporter[bpy.types.GeometryNodeViewer]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME, VIEWER_ITEMS],
            [PARENT],
        )


class ViewerImporter(SpecificImporter[bpy.types.GeometryNodeViewer]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the viewer_items implicitly create sockets
            [VIEWER_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS,
        )
        _import_node_parent(self)


class ViewerItemsImporter(SpecificImporter[bpy.types.NodeGeometryViewerItems]):  # ty:ignore[invalid-type-arguments]
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


class ColorRampElementsImporter(SpecificImporter[bpy.types.ColorRampElements]):  # ty:ignore[invalid-type-arguments]
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
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME],
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
                self.importer.current_tree.nodes[output]  # ty:ignore[unresolved-attribute]
            ):
                raise RuntimeError(
                    f"{self.from_root.to_str()}: failed to pair with {output}"
                )
            self.import_properties_from_id_list(NODE_GENERIC_COLLECTIONS)

        # defer connection until we've created the output node
        # only then, import the sockets
        self.importer.defer_after_nodes_before_links.append(deferred)
        _import_node_parent(self)


class SimulationOutputExporter(
    SpecificExporter[bpy.types.GeometryNodeSimulationOutput]
):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME, STATE_ITEMS],
            [PARENT],
        )


class SimulationOutputImporter(
    SpecificImporter[bpy.types.GeometryNodeSimulationOutput]
):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the state_items implicitly create sockets
            [STATE_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class SimulationOutputItemsImporter(
    SpecificImporter[bpy.types.NodeGeometrySimulationOutputItems]  # ty:ignore[invalid-type-arguments]
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
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME],
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
                self.importer.current_tree.nodes[output]  # ty:ignore[unresolved-attribute]
            ):
                raise RuntimeError(
                    f"{self.from_root.to_str()}: failed to pair with {output}"
                )
            self.import_properties_from_id_list(NODE_GENERIC_COLLECTIONS)

        # defer connection until we've created the output node
        # only then, import the sockets
        self.importer.defer_after_nodes_before_links.append(deferred)
        _import_node_parent(self)


class NodeClosureOutputExporter(SpecificExporter[bpy.types.NodeClosureOutput]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME, INPUT_ITEMS, OUTPUT_ITEMS],
            [PARENT],
        )


class NodeClosureOutputImporter(SpecificImporter[bpy.types.NodeClosureOutput]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the items implicitly create sockets
            [INPUT_ITEMS, OUTPUT_ITEMS, ACTIVE_INPUT_INDEX, ACTIVE_OUTPUT_INDEX]
            + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class NodeClosureInputItems(SpecificImporter[bpy.types.NodeClosureInputItems]):  # ty:ignore[invalid-type-arguments]
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


class NodeClosureOutputItems(SpecificImporter[bpy.types.NodeClosureOutputItems]):  # ty:ignore[invalid-type-arguments]
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
    """The reroute's sockets can cause problems, we just register them for linking"""

    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list(
            [BL_IDNAME], [PARENT]
        )

        # https://github.com/Algebraic-UG/tree_clipper/issues/98
        data.pop(WIDTH)

        # https://github.com/Algebraic-UG/tree_clipper/issues/203
        data.pop(SOCKET_IDNAME)

        no_clobber(
            data,
            SINGLE_INPUT,
            self.exporter.register_as_serialized(self.obj.inputs[0]),
        )
        no_clobber(
            data,
            SINGLE_OUTPUT,
            self.exporter.register_as_serialized(self.obj.outputs[0]),
        )

        return data


class RerouteImporter(SpecificImporter[bpy.types.NodeReroute]):
    """See export"""

    def deserialize(self):
        self.import_all_simple_writable_properties()
        _import_node_parent(self)

        self.importer.register_as_deserialized(
            ident=self.serialization[SINGLE_INPUT],
            getter=lambda: self.getter().inputs[0],
        )
        self.importer.register_as_deserialized(
            ident=self.serialization[SINGLE_OUTPUT],
            getter=lambda: self.getter().outputs[0],
        )


class CurveMapPointExporter(SpecificExporter[bpy.types.CurveMapPoint]):
    __doc__ = f"""The container constructs them using the {LOCATION}"""

    def serialize(self):
        return self.export_all_simple_writable_properties()


class CurveMapPointsImporter(SpecificImporter[bpy.types.CurveMapPoints]):  # ty:ignore[invalid-type-arguments]
    __doc__ = f"""The {LOCATION} needs to be picked apart into argumets
and there are always at least two points.
We remove all but two and skip first and last from the serialization."""

    def deserialize(self):
        while len(self.getter()) > 2:
            self.getter().remove(point=self.getter()[1])
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
    __doc__ = f"""The properties on this one are special.
The properties of the pointees {DISPLAY_SETTINGS} and {VIEW_SETTINGS} are set implicitly
by setting certain enums values.
They also have an implicit ordering, first the display needs to be set, then the view."""

    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)

        display_device = self.serialization[DISPLAY_SETTINGS][DATA][DISPLAY_DEVICE]
        view_transform = self.serialization[VIEW_SETTINGS][DATA][VIEW_TRANSFORM]
        look = self.serialization[VIEW_SETTINGS][DATA][LOOK]
        self.getter().display_settings.display_device = display_device  # ty: ignore[invalid-assignment]
        self.getter().view_settings.view_transform = view_transform  # ty: ignore[invalid-assignment]
        self.getter().view_settings.look = look  # ty: ignore[invalid-assignment]


class NodeEvaluateClosureImporter(SpecificImporter[bpy.types.NodeEvaluateClosure]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the input_items and output_items implicitly create sockets
            [INPUT_ITEMS, OUTPUT_ITEMS, ACTIVE_INPUT_INDEX, ACTIVE_OUTPUT_INDEX]
            + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class EvalClosureInputItemExporter(
    SpecificExporter[bpy.types.NodeEvaluateClosureInputItem]
):
    __doc__ = f"""We need {SOCKET_TYPE} and {NAME}, both are simple & writable"""

    def serialize(self):
        return self.export_all_simple_writable_properties()


class EvalClosureInputItemsImporter(
    SpecificImporter[bpy.types.NodeEvaluateClosureInputItems]  # ty:ignore[invalid-type-arguments]
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
    __doc__ = f"""We need {SOCKET_TYPE} and {NAME}, both are simple & writable"""

    def serialize(self):
        return self.export_all_simple_writable_properties()


class EvalClosureOutputItemsImporter(
    SpecificImporter[bpy.types.NodeEvaluateClosureOutputItems]  # ty:ignore[invalid-type-arguments]
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
            [FORMAT_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class FormatStringItemExporter(
    SpecificExporter[bpy.types.NodeFunctionFormatStringItem]
):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class FormatStringItemsImporter(
    SpecificImporter[bpy.types.NodeFunctionFormatStringItems]  # ty:ignore[invalid-type-arguments]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class CombineBundleImporter(SpecificImporter[bpy.types.NodeCombineBundle]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the bundle_items implicitly create sockets
            [BUNDLE_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class CombineBundleItemExporter(SpecificExporter[bpy.types.NodeCombineBundleItem]):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class CombineBundleItemsImporter(SpecificImporter[bpy.types.NodeCombineBundleItems]):  # ty:ignore[invalid-type-arguments]
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class SeparateBundleImporter(SpecificImporter[bpy.types.NodeSeparateBundle]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the bundle_items implicitly create sockets
            [BUNDLE_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class SeparateBundleItemExporter(SpecificExporter[bpy.types.NodeSeparateBundleItem]):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class SeparateBundleItemsImporter(SpecificImporter[bpy.types.NodeSeparateBundleItems]):  # ty:ignore[invalid-type-arguments]
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class RenderLayersExporter(SpecificExporter[bpy.types.CompositorNodeRLayers]):
    __doc__ = f"""We skip the {LAYER} if the {SCENE} is not set.
{LAYER} is an empty string in that case and we can't set that during import."""

    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list(
            [BL_IDNAME],
            [PARENT, SCENE],
        )

        # We can't export all sockets, we have to skip the ones than are disabled
        # The normal collection exporting can't filter so we recreate it here
        # with some debug prints to track which sockets we skip.
        # see https://github.com/Algebraic-UG/tree_clipper/issues/84

        assert len(self.obj.inputs) == 0

        outputs = self.exporter._export_obj(
            obj=self.obj.outputs,
            from_root=self.from_root.add_prop(self.obj.bl_rna.properties[OUTPUTS]),
        )

        output_items = []
        other_disabled_should_follow = False
        for i, output_item in enumerate(self.obj.outputs):
            from_root_socket = self.from_root.add(f"[{i}] ({output_item.name})")

            if output_item.enabled:
                assert not other_disabled_should_follow, (
                    "We assume the enabled sockets are all at the beginning"
                )

                output_items.append(
                    self.exporter._export_obj(
                        obj=output_item,
                        from_root=from_root_socket,
                    )
                )

                continue

            other_disabled_should_follow = True
            if self.exporter.debug_prints:
                print(f"{from_root_socket.to_str()} Skipping disabled output socket")

        no_clobber(outputs[DATA], ITEMS, output_items)
        no_clobber(data, OUTPUTS, outputs)

        return data


class RenderLayersImporter(SpecificImporter[bpy.types.CompositorNodeRLayers]):
    def deserialize(self):
        self.import_all_simple_writable_properties([LAYER])
        if self.serialization[SCENE] is not None:
            assert self.serialization[LAYER] != ""
            # order is important, the scene determines which layers can be set
            self.import_properties_from_id_list([SCENE, LAYER])
        _import_node_parent(self)

        # We can't import all sockets, we have to skip the ones than are disabled
        # The normal collection importing can't filter so we recreate it here
        # with some debug prints to track which sockets we skip.
        # see https://github.com/Algebraic-UG/tree_clipper/issues/84

        enabled_outputs = [socket for socket in self.getter().outputs if socket.enabled]
        serialized_outputs = self.serialization[OUTPUTS][DATA][ITEMS]

        # prior checks of the scene and layer should make this impossible to fail
        assert len(enabled_outputs) == len(serialized_outputs), (
            f"{len(enabled_outputs)} enabled output sockets, {len(serialized_outputs)} in serialization"
        )

        # the rest is basically the same as in normal collection importing

        def make_getter(i: int) -> GETTER:
            return lambda: getattr(self.getter(), OUTPUTS)[i]

        for i, item in enumerate(serialized_outputs):
            name = item.get(NAME, "unnamed")
            self.importer._import_obj(
                getter=make_getter(i),
                serialization=item,
                from_root=self.from_root.add(f"[{i}] ({name})"),
            )


class ForEachInputExporter(
    SpecificExporter[bpy.types.GeometryNodeForeachGeometryElementInput]
):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME],
            [PARENT],
        )
        if self.obj.paired_output is None:
            raise RuntimeError(
                f"""{self.from_root.to_str()}
Having no paired output for for_each nodes isn't supported"""
            )
        no_clobber(data, PAIRED_OUTPUT, self.obj.paired_output.name)

        return data


class ForEachInputImporter(
    SpecificImporter[bpy.types.GeometryNodeForeachGeometryElementInput]
):
    def deserialize(self):
        self.import_all_simple_writable_properties()

        # if this fails it's easier to debug here
        output = self.serialization[PAIRED_OUTPUT]

        def deferred():
            if not self.getter().pair_with_output(
                self.importer.current_tree.nodes[output]  # ty:ignore[unresolved-attribute]
            ):
                raise RuntimeError(
                    f"{self.from_root.to_str()}: failed to pair with {output}"
                )
            self.import_properties_from_id_list(NODE_GENERIC_COLLECTIONS)

        # defer connection until we've created the output node
        # only then, import the sockets
        self.importer.defer_after_nodes_before_links.append(deferred)
        _import_node_parent(self)


class ForEachOutputImporter(
    SpecificImporter[bpy.types.GeometryNodeForeachGeometryElementOutput]
):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the items implicitly create sockets
            [
                GENERATION_ITEMS,
                INPUT_ITEMS,
                MAIN_ITEMS,
                ACTIVE_GENERATION_INDEX,
                ACTIVE_INPUT_INDEX,
                ACTIVE_MAIN_INDEX,
            ]
            + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class GenerationItemExporter(
    SpecificExporter[bpy.types.ForeachGeometryElementGenerationItem]
):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class GenerationItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryForeachGeometryElementGenerationItems]  # ty:ignore[invalid-type-arguments]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class InputItemExporter(SpecificExporter[bpy.types.ForeachGeometryElementInputItem]):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class InputItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryForeachGeometryElementInputItems]  # ty:ignore[invalid-type-arguments]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class MainItemExporter(SpecificExporter[bpy.types.ForeachGeometryElementMainItem]):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class MainItemsImporter(
    SpecificImporter[bpy.types.NodeGeometryForeachGeometryElementMainItems]  # ty:ignore[invalid-type-arguments]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class BakeExporter(SpecificExporter[bpy.types.GeometryNodeBake]):
    __doc__ = f"""We need to specialize to avoid {ACTIVE_ITEM}, which is broken
https://projects.blender.org/blender/blender/issues/151276"""

    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME, BAKE_ITEMS],
            [PARENT],
        )


class BakeImporter(SpecificImporter[bpy.types.GeometryNodeBake]):
    def deserialize(self) -> None:
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the bake_items implicitly create sockets
            [BAKE_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class BakeItemExporter(SpecificExporter[bpy.types.NodeGeometryBakeItem]):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class BakeItemsImporter(SpecificImporter[bpy.types.NodeGeometryBakeItems]):  # ty:ignore[invalid-type-arguments]
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class FieldToGridExporter(SpecificExporter[bpy.types.GeometryNodeFieldToGrid]):
    __doc__ = f"""We need to specialize to avoid {ACTIVE_ITEM}, which is broken
https://projects.blender.org/blender/blender/issues/151276"""

    def serialize(self):
        return self.export_all_simple_writable_properties_and_list(
            NODE_GENERIC_COLLECTIONS + [BL_IDNAME, GRID_ITEMS],
            [PARENT],
        )


class FieldToGridImporter(SpecificImporter[bpy.types.GeometryNodeFieldToGrid]):
    def deserialize(self) -> None:
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the grid_items implicitly create sockets
            [GRID_ITEMS, ACTIVE_INDEX] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class FieldToGridItemExporter(SpecificExporter[bpy.types.GeometryNodeFieldToGridItem]):
    def serialize(self):
        return self.export_all_simple_writable_properties()


class FieldToGridItemsImporter(
    SpecificImporter[bpy.types.GeometryNodeFieldToGridItems]  # ty:ignore[invalid-type-arguments]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][DATA_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class FileOutputImporter(SpecificImporter[bpy.types.CompositorNodeOutputFile]):
    def deserialize(self):
        self.import_all_simple_writable_properties_and_list(
            # ordering is important, the file_output_items implicitly create sockets
            [FILE_OUTPUT_ITEMS, ACTIVE_ITEM_INDEX, FORMAT] + NODE_GENERIC_COLLECTIONS
        )
        _import_node_parent(self)


class FileOutputItemExporter(SpecificExporter[bpy.types.NodeCompositorFileOutputItem]):
    def serialize(self):
        return self.export_all_simple_writable_properties_and_list([FORMAT])


class FileOutputItemsImporter(
    SpecificImporter[bpy.types.NodeCompositorFileOutputItems]  # ty:ignore[invalid-type-arguments]
):
    def deserialize(self):
        self.getter().clear()
        for item in self.serialization[ITEMS]:
            socket_type = item[DATA][SOCKET_TYPE]
            name = item[DATA][NAME]
            self.getter().new(name=name, socket_type=socket_type)


class SetMeshNormalImporter(SpecificImporter[bpy.types.GeometryNodeSetMeshNormal]):
    """We need to trigger the import of mode first"""

    def deserialize(self) -> None:
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


class ColorManagedViewSettingsExporter(
    SpecificExporter[bpy.types.ColorManagedViewSettings]
):
    def serialize(self):
        data = self.export_all_simple_writable_properties_and_list([CURVE_MAPPING])
        # this is calculated from the other properties and can cause problems on import
        # https://github.com/Algebraic-UG/tree_clipper/issues/96
        data.pop(WHITE_BALANCE_WHITEPOINT)
        return data


class CompareImporter(SpecificImporter[bpy.types.FunctionNodeCompare]):
    """We need to trigger the choices first"""

    def deserialize(self) -> None:
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


class RotateEulerImporter(SpecificImporter[bpy.types.FunctionNodeRotateEuler]):
    """We need to trigger the import of rotation_type first"""

    def deserialize(self) -> None:
        self.import_all_simple_writable_properties_and_list(NODE_GENERIC_COLLECTIONS)
        _import_node_parent(self)


if (bpy.app.version[0] == 5 and bpy.app.version[1] >= 1) or bpy.app.version[0] > 5:

    class FieldToListExporter(SpecificExporter[bpy.types.GeometryNodeFieldToList]):
        def serialize(self):
            return self.export_all_simple_writable_properties_and_list(
                NODE_GENERIC_COLLECTIONS + [BL_IDNAME, LIST_ITEMS],
                [PARENT],
            )

    class FieldToListImporter(SpecificImporter[bpy.types.GeometryNodeFieldToList]):
        def deserialize(self):
            self.import_all_simple_writable_properties_and_list(
                # ordering is important, the list_items implicitly create sockets
                [LIST_ITEMS, ACTIVE_INDEX, INPUTS, OUTPUTS]
            )
            _import_node_parent(self)

    class FieldToListItemExporter(
        SpecificExporter[bpy.types.GeometryNodeFieldToListItem]
    ):
        def serialize(self):
            return self.export_all_simple_writable_properties()

    class FieldToListItemsImporter(
        SpecificImporter[bpy.types.GeometryNodeFieldToListItems]  # ty:ignore[invalid-type-arguments]
    ):
        def deserialize(self):
            self.getter().clear()
            for item in self.serialization[ITEMS]:
                socket_type = item[DATA][SOCKET_TYPE]
                name = item[DATA][NAME]
                self.getter().new(name=name, socket_type=socket_type)

    class CryptomatteExporter(SpecificExporter[bpy.types.CompositorNodeCryptomatte]):
        def serialize(self):
            data = self.export_all_simple_writable_properties_and_list(
                NODE_GENERIC_COLLECTIONS + [BL_IDNAME],
                [PARENT],
            )
            # https://github.com/Algebraic-UG/tree_clipper/issues/165
            data.pop(ADD)
            data.pop(REMOVE)
            return data

    class CryptomatteV2Exporter(
        SpecificExporter[bpy.types.CompositorNodeCryptomatteV2]
    ):
        def serialize(self):
            data = self.export_all_simple_writable_properties_and_list(
                NODE_GENERIC_COLLECTIONS + [BL_IDNAME, ENTRIES],
                [PARENT, IMAGE, SCENE],
            )
            # https://github.com/Algebraic-UG/tree_clipper/issues/165
            data.pop(ADD)
            data.pop(REMOVE)
            return data

    class StringToCurvesImporter(
        SpecificImporter[bpy.types.GeometryNodeStringToCurves]
    ):
        def deserialize(self):
            # https://github.com/Algebraic-UG/tree_clipper/issues/167
            if self.importer.blender_version[:2] == [5, 0]:
                # we have to skip the INPUTS/OUTPUTS collection importers because
                # the number of sockets has changed between versions
                self.import_all_simple_writable_properties_and_list([])
                _import_node_parent(self)

                # this might not be needed, but nice to have all the getters
                self.only_create_getters([INPUTS, OUTPUTS])

                # allow conneting the old links
                map_socket_input(importer=self, name="String")
                map_socket_input(importer=self, name="Size")
                map_socket_input(importer=self, name="Character Spacing")
                map_socket_input(importer=self, name="Word Spacing")
                map_socket_input(importer=self, name="Line Spacing")
                map_socket_input(importer=self, name="Text Box Width")
                map_socket_input(importer=self, name="Text Box Height")

                map_socket_output(importer=self, name="Curve Instances")
                map_socket_output(importer=self, name="Line")
                map_socket_output(importer=self, name="Pivot Point")

                # map node attributes to default socket values
                font = self.importer.getters.get(self.serialization[FONT])
                if font is not None:
                    font = font()
                self.getter().inputs["Font"].default_value = font

                # these menu values need to be mapped from
                # BOTTOM_BASELINE to Bottom Baseline
                def map_menu_value(old: str):
                    return old.replace("_", " ").title()

                self.getter().inputs["Overflow"].default_value = map_menu_value(
                    self.serialization[OVERFLOW]
                )
                self.getter().inputs["Align X"].default_value = map_menu_value(
                    self.serialization[ALIGN_X]
                )
                self.getter().inputs["Align Y"].default_value = map_menu_value(
                    self.serialization[ALIGN_Y]
                )
                self.getter().inputs["Pivot Point"].default_value = map_menu_value(
                    self.serialization[PIVOT_MODE]
                )

                return

            self.import_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])
            _import_node_parent(self)

    class UVUnwrapImporter(SpecificImporter[bpy.types.GeometryNodeUVUnwrap]):
        def deserialize(self):
            # https://github.com/Algebraic-UG/tree_clipper/issues/168
            if self.importer.blender_version[:2] == [5, 0]:
                self.import_all_simple_writable_properties_and_list([OUTPUTS])
                # this might not be needed, but nice to have all the getters
                self.only_create_getters([INPUTS])

                map_socket_input(importer=self, name="Selection")
                map_socket_input(importer=self, name="Seam")
                map_socket_input(importer=self, name="Margin")
                map_socket_input(importer=self, name="Fill Holes")
                map_socket_input(importer=self, name="Method")

                return

            self.import_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])
            _import_node_parent(self)

    class PackUVIslandsImporter(SpecificImporter[bpy.types.GeometryNodeUVPackIslands]):
        def deserialize(self):
            # https://github.com/Algebraic-UG/tree_clipper/issues/169
            if self.importer.blender_version[:2] == [5, 0]:
                self.import_all_simple_writable_properties_and_list([OUTPUTS])
                # this might not be needed, but nice to have all the getters
                self.only_create_getters([INPUTS])

                map_socket_input(importer=self, name="UV")
                map_socket_input(importer=self, name="Selection")
                map_socket_input(importer=self, name="Margin")
                map_socket_input(importer=self, name="Rotate")
                map_socket_input(importer=self, name="Method")

                return

            self.import_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])
            _import_node_parent(self)

    class FillCurveImporter(SpecificImporter[bpy.types.GeometryNodeFillCurve]):
        def deserialize(self):
            # https://github.com/Algebraic-UG/tree_clipper/issues/170
            if self.importer.blender_version[:2] == [5, 0]:
                self.import_all_simple_writable_properties_and_list([OUTPUTS])
                # this might not be needed, but nice to have all the getters
                self.only_create_getters([INPUTS])

                map_socket_input(importer=self, name="Curve")
                map_socket_input(importer=self, name="Group ID")
                map_socket_input(importer=self, name="Mode")

                return

            self.import_all_simple_writable_properties_and_list([INPUTS, OUTPUTS])
            _import_node_parent(self)


FAKE_ADD_SOCKET = {
    "id": -1,
    "data": {
        "name": "",
        "description": "",
        "hide": False,
        "enabled": True,
        "link_limit": 4095,
        "show_expanded": False,
        "hide_value": False,
        "pin_gizmo": False,
        "type": "CUSTOM",
        "display_shape": "CIRCLE",
    },
}

if (bpy.app.version[0] == 5 and bpy.app.version[1] >= 2) or bpy.app.version[0] > 5:

    class RaycastSampleAttributeItemExporter(
        SpecificExporter[bpy.types.NodeRaycastSampleAttributeItem]  # ty:ignore[unresolved-attribute]
    ):
        def serialize(self):
            return self.export_all_simple_writable_properties()

    class RaycastSampleAttributeItemsImporter(
        SpecificImporter[bpy.types.NodeRaycastSampleAttributeItems]  # ty:ignore[unresolved-attribute]
    ):
        def deserialize(self):
            self.getter().clear()
            for item in self.serialization[ITEMS]:
                name = _or_default(
                    item[DATA],
                    bpy.types.NodeRaycastSampleAttributeItem,  # ty:ignore[unresolved-attribute]
                    NAME,
                )
                socket_type = _map_attribute_type_to_socket_type(
                    _or_default(
                        item[DATA],
                        bpy.types.NodeGeometryCaptureAttributeItem,
                        DATA_TYPE,
                    )
                )
                if self.importer.debug_prints:
                    print(
                        f"{self.from_root.to_str()}: adding item {name} {socket_type}"
                    )
                self.getter().new(socket_type=socket_type, name=name)

    class RaycastImporter(SpecificImporter[bpy.types.ShaderNodeRaycast]):
        def deserialize(self):
            if compat_5_1(self.importer):
                # https://github.com/Algebraic-UG/tree_clipper/issues/213
                self.serialization[SAMPLE_ATTRIBUTE_ITEMS] = {
                    "id": -1,
                    "data": {"items": []},
                }
                self.serialization[ACTIVE_INDEX] = 0
                self.serialization[INPUTS][DATA][ITEMS].insert(3, FAKE_ADD_SOCKET)
                self.serialization[OUTPUTS][DATA][ITEMS].insert(5, FAKE_ADD_SOCKET)

            self.import_all_simple_writable_properties_and_list(
                # ordering is important, the sample_attribute_items implicitly create sockets
                [SAMPLE_ATTRIBUTE_ITEMS, ACTIVE_INDEX, INPUTS, OUTPUTS]
            )
            _import_node_parent(self)

    class ClosureToListItemExporter(
        SpecificExporter[bpy.types.GeometryNodeClosureToListItem]  # ty:ignore[unresolved-attribute]
    ):
        def serialize(self):
            return self.export_all_simple_writable_properties()

    class ClosureToListItemsImporter(
        SpecificImporter[bpy.types.GeometryNodeClosureToListItems]  # ty:ignore[unresolved-attribute]
    ):
        def deserialize(self):
            self.getter().clear()
            for item in self.serialization[ITEMS]:
                name = _or_default(
                    item[DATA],
                    bpy.types.GeometryNodeClosureToListItem,  # ty:ignore[unresolved-attribute]
                    NAME,
                )
                socket_type = _or_default(
                    item[DATA],
                    bpy.types.GeometryNodeClosureToListItem,  # ty:ignore[unresolved-attribute]
                    SOCKET_TYPE,
                )
                if self.importer.debug_prints:
                    print(
                        f"{self.from_root.to_str()}: adding item {name} {socket_type}"
                    )
                self.getter().new(socket_type=socket_type, name=name)

    class ClosureToListImporter(SpecificImporter[bpy.types.GeometryNodeClosureToList]):  # ty:ignore[unresolved-attribute]
        def deserialize(self):
            self.import_all_simple_writable_properties_and_list(
                # ordering is important, the list_items implicitly create sockets
                [LIST_ITEMS, ACTIVE_INDEX, INPUTS, OUTPUTS]
            )
            _import_node_parent(self)


# now they are cooked and ready to use ~ bon appétit
BUILT_IN_EXPORTER = _BUILT_IN_EXPORTER
BUILT_IN_IMPORTER = _BUILT_IN_IMPORTER
