import bpy

from .operators_export import SCENE_OT_Tree_Clipper_Export_Prepare
from .operators_import import (
    SCENE_OT_Tree_Clipper_Import_Clipboard_Prepare,
    SCENE_OT_Tree_Clipper_Import_File_Prepare,
)
from ._vendor.tree_clipper.import_nodes import preliminary_check


class SCENE_PT_Tree_Clipper_Panel(bpy.types.Panel):
    bl_label = "Tree Clipper"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Tree Clipper"

    def draw(self, context: bpy.types.Context) -> None:
        assert isinstance(context.space_data, bpy.types.SpaceNodeEditor)

        export_col = self.layout.column()  # ty:ignore[possibly-missing-attribute]
        export_op = export_col.operator(SCENE_OT_Tree_Clipper_Export_Prepare.bl_idname)

        node_tree = context.space_data.node_tree
        if node_tree is None:
            export_col.enabled = False
        else:
            is_root = context.space_data.node_tree == context.space_data.edit_tree
            is_material = is_root and isinstance(
                context.space_data.id, bpy.types.Material
            )

            if is_material:
                name = context.space_data.id.name  # ty:ignore[possibly-missing-attribute]
            else:
                name = context.space_data.edit_tree.name  # ty:ignore[possibly-missing-attribute]

            export_op.is_material = is_material
            export_op.name = name

        self.layout.separator()  # ty:ignore[possibly-missing-attribute]

        import_col = self.layout.column()  # ty:ignore[possibly-missing-attribute]
        if SCENE_OT_Tree_Clipper_Import_Clipboard_Prepare.poll(context):
            import_text = SCENE_OT_Tree_Clipper_Import_Clipboard_Prepare.bl_label
        else:
            import_text = "Invalid Clipboard Content"
        import_col.operator(
            SCENE_OT_Tree_Clipper_Import_Clipboard_Prepare.bl_idname, text=import_text
        )
        import_col.operator(SCENE_OT_Tree_Clipper_Import_File_Prepare.bl_idname)
