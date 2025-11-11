import bpy

from pathlib import Path
import tempfile

from .export_nodes import export_nodes
from .import_nodes import import_nodes

DEFAULT_FILE = Path(tempfile.gettempdir()) / "default.json"


class SCENE_PT_NodesAsJSON_Panel_Export(bpy.types.Operator):
    bl_idname = "scene.nodes_as_json_export"
    bl_label = "Export"

    material: bpy.props.BoolProperty(name="Top level Material")  # type: ignore
    name: bpy.props.StringProperty(name="Material/NodeTree")  # type: ignore
    output_file: bpy.props.StringProperty(name="Output File", subtype="FILE_PATH")  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return export_nodes(self, context)


class SCENE_PT_NodesAsJSON_Panel_Import(bpy.types.Operator):
    bl_idname = "scene.nodes_as_json_import"
    bl_label = "Import"

    input_file: bpy.props.StringProperty(name="Input File", subtype="FILE_PATH")  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        return import_nodes(self, context)


class SCENE_PT_NodesAsJSON_Panel(bpy.types.Panel):
    bl_label = "Nodes As JSON"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Nodes As JSON"

    def draw(self, _context):

        self.layout.operator(
            SCENE_PT_NodesAsJSON_Panel_Export.bl_idname
        ).output_file = f"{str(DEFAULT_FILE)}"
        self.layout.operator(SCENE_PT_NodesAsJSON_Panel_Import.bl_idname).input_file = (
            f"{str(DEFAULT_FILE)}"
        )
