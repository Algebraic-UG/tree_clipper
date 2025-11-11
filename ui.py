import bpy


class SCENE_PT_NodesAsJSON_Panel_Export(bpy.types.Operator):
    bl_idname = "scene.nodes_as_json_export"
    bl_label = "Export"

    output_file: bpy.props.StringProperty(name="Output File", subtype="FILE_PATH")  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return super().execute(context)


class SCENE_PT_NodesAsJSON_Panel_Import(bpy.types.Operator):
    bl_idname = "scene.nodes_as_json_import"
    bl_label = "Import"

    input_file: bpy.props.StringProperty(name="Input File", subtype="FILE_PATH")  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return super().execute(context)


class SCENE_PT_NodesAsJSON_Panel(bpy.types.Panel):
    bl_label = "Nodes As JSON"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Nodes As JSON"

    def draw(self, _context):
        self.layout.operator(SCENE_PT_NodesAsJSON_Panel_Export.bl_idname)
        self.layout.operator(SCENE_PT_NodesAsJSON_Panel_Import.bl_idname)
