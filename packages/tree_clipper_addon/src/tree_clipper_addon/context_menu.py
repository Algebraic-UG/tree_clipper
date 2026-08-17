from typing import Any

import bpy

from .operators_export import SCENE_OT_Tree_Clipper_Copy_Magic_Node_String
from .operators_import import SCENE_OT_Tree_Clipper_Import_Clipboard_Prepare


def draw_tree_clipper_context_menu(self: Any, context: bpy.types.Context) -> None:
    space = context.space_data
    if not isinstance(space, bpy.types.SpaceNodeEditor):
        return

    selected_nodes = getattr(context, "selected_nodes", ())
    if space.tree_type == "GeometryNodeTree" and not selected_nodes:
        self.layout.separator()
        self.layout.operator(
            SCENE_OT_Tree_Clipper_Import_Clipboard_Prepare.bl_idname,
            text="Paste Magic Node String",
            icon="PASTEDOWN",
        )
        return

    active_node = getattr(context, "active_node", None)
    if (
        active_node is not None
        and active_node.type == "GROUP"
        and active_node.node_tree is not None
    ):
        self.layout.separator()
        self.layout.operator(
            SCENE_OT_Tree_Clipper_Copy_Magic_Node_String.bl_idname,
            text="Copy Magic Node String",
            icon="COPYDOWN",
        )
