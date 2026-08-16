import json

import bpy

from .util import (
    export_to_string,
    make_test_node_tree,
    round_trip_without_external,
    save_failed,
)

if (bpy.app.version[0] == 5 and bpy.app.version[1] >= 2) or bpy.app.version[0] > 5:

    def test_node_panel_states():
        try:
            inner = make_test_node_tree(name="panel state inner")

            # Leave a gap in the persistent UIDs. Those identifiers are
            # read-only and are therefore not guaranteed to survive import.
            removed_panel = inner.interface.new_panel(name="removed")
            inner.interface.remove(removed_panel)

            open_panel = inner.interface.new_panel(name="open")
            closed_panel = inner.interface.new_panel(name="closed")
            inner.interface.new_socket(
                name="Open Value",
                in_out="INPUT",
                socket_type="NodeSocketFloat",
                parent=open_panel,
            )
            inner.interface.new_socket(
                name="Closed Value",
                in_out="INPUT",
                socket_type="NodeSocketFloat",
                parent=closed_panel,
            )

            outer = make_test_node_tree(name="panel state outer")
            group_node = outer.nodes.new(type="GeometryNodeGroup")
            group_node.node_tree = inner

            assert [state.identifier for state in group_node.panel_states] == [
                open_panel.persistent_uid,
                closed_panel.persistent_uid,
            ]
            group_node.panel_states[0].is_collapsed = False
            group_node.panel_states[1].is_collapsed = True

            serialization = json.loads(export_to_string(outer.name))
            serialized_outer = next(
                tree
                for tree in serialization["node_trees"]
                if tree["data"]["name"] == outer.name
            )
            serialized_node = serialized_outer["data"]["nodes"]["data"]["items"][0]
            serialized_states = serialized_node["data"]["panel_states"]["data"]["items"]

            assert [state["data"]["is_collapsed"] for state in serialized_states] == [
                False,
                True,
            ]
            assert all("identifier" not in state["data"] for state in serialized_states)

            round_trip_without_external(outer.name)
        except:
            save_failed(test_node_panel_states.__name__)
            raise
