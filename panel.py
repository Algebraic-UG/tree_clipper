import bpy


class SCENE_PT_NodesAsJSON_Panel(bpy.types.Panel):
    bl_label = "Nodes As JSON"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Nodes As JSON"

    def draw(self, context):
        self.layout.label(text="Hello World")
