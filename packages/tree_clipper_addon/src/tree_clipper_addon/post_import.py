import bpy

from ._vendor.tree_clipper.import_nodes import ImportReport

TREE_TYPE_TO_GROUP_TYPE = {
    bpy.types.CompositorNodeTree: bpy.types.CompositorNodeGroup,
    bpy.types.GeometryNodeTree: bpy.types.GeometryNodeGroup,
    bpy.types.ShaderNodeTree: bpy.types.ShaderNodeGroup,
    bpy.types.TextureNodeTree: bpy.types.TextureNodeGroup,
}


def post_import(
    *,
    context: bpy.types.Context,
    event: bpy.types.Event,
    report: ImportReport,
) -> None:
    def add_as_group() -> str | None:
        if not isinstance(context.space_data, bpy.types.SpaceNodeEditor):
            return "Not a node editor."

        node_tree = context.space_data.node_tree
        if node_tree is None:
            return "No active tree to attach to."

        assert report.last_getter is not None
        imported_root = report.last_getter()

        if node_tree.bl_rna.identifier != imported_root.bl_rna.identifier:  # ty:ignore[unresolved-attribute]
            return f"Editor type is {node_tree.bl_rna.identifier}, but imported {imported_root.bl_rna.identifier}."  # ty:ignore[unresolved-attribute]

        group = node_tree.nodes.new(
            type=TREE_TYPE_TO_GROUP_TYPE[type(imported_root)].bl_rna.identifier,  # ty:ignore[possibly-missing-attribute]
        )
        group.node_tree = imported_root  # ty:ignore[unresolved-attribute]

        # fix offset
        group.location = context.region.view2d.region_to_view(  # ty:ignore[possibly-missing-attribute, invalid-assignment]
            event.mouse_region_x, event.mouse_region_y
        )
        # otherwise the others will be moved as well
        for node in node_tree.nodes:
            node.select = False
        group.select = True

        bpy.ops.node.translate_attach_remove_on_cancel("INVOKE_DEFAULT")

    failure_reason = add_as_group()
    if failure_reason is not None:

        def warn_popup():
            def draw(self, context: bpy.types.Context):
                self.layout.label(text="The import succeeded! 🎉")
                self.layout.label(text="Could not attached the root to current editor:")
                self.layout.label(text=failure_reason)
                self.layout.separator()
                self.layout.label(text="Please check the INFO for the imported trees.")

            bpy.context.window_manager.popup_menu(  # ty:ignore[possibly-missing-attribute]
                draw, title="Where's My Import?", icon="INFO"
            )

        # we need to defer, otherwise Blender crashes
        bpy.app.timers.register(warn_popup)

    pass
