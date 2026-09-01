import bpy


class SCENE_OT_Tree_Clipper_Export_Active(bpy.types.Operator):
    bl_label = "Export Tree Clipper"
    bl_idname = "scene.tree_clipper_export_active"
    bl_description = (
        "Export the selected and active node group as a Tree Clipper string."
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        node = context.active_node
        return (
            node is not None
            and isinstance(
                node,
                bpy.types.CompositorNodeGroup
                | bpy.types.GeometryNodeGroup
                | bpy.types.ShaderNodeGroup
                | bpy.types.TextureNodeGroup,
            )
            and node.node_tree is not None
        )

    def execute(self, context: bpy.types.Context) -> None:  # ty:ignore[invalid-method-override]
        assert isinstance(context.space_data, bpy.types.SpaceNodeEditor)
        assert context.active_node is not None
        assert context.active_node.node_tree is not None  # ty:ignore[unresolved-attribute]

        bpy.ops.scene.tree_clipper_export_prepare(  # ty:ignore[unresolved-attribute]
            "INVOKE_DEFAULT",
            is_material=False,
            name=context.active_node.node_tree.name,  # ty:ignore[unresolved-attribute]
        )
        return {"FINISHED"}  # ty:ignore[invalid-return-type]
