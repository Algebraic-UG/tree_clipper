import bpy

from pathlib import Path
import tempfile

from .export_nodes import export_nodes
from .specific_handlers import BUILT_IN_DESERIALIZERS, BUILT_IN_SERIALIZERS
from .import_nodes import import_nodes

DEFAULT_FILE = str(Path(tempfile.gettempdir()) / "default.json")


class SCENE_OT_NodesAsJSON_Panel_Export(bpy.types.Operator):
    bl_idname = "scene.nodes_as_json_export"
    bl_label = "Export"
    bl_options = {"REGISTER"}

    is_material: bpy.props.BoolProperty(name="Top level Material")  # type: ignore
    name: bpy.props.StringProperty(name="Material/NodeTree")  # type: ignore
    output_file: bpy.props.StringProperty(name="Output File", default=DEFAULT_FILE, subtype="FILE_PATH")  # type: ignore
    export_sub_trees: bpy.props.BoolProperty(name="Export Sub Trees", default=True)  # type: ignore
    skip_defaults: bpy.props.BoolProperty(name="Skip Defaults", default=True)  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, _context):
        export_nodes(
            is_material=self.is_material,
            name=self.name,
            output_file=self.output_file,
            specific_handlers=BUILT_IN_SERIALIZERS,
            export_sub_trees=self.export_sub_trees,
            skip_defaults=self.skip_defaults,
        )
        return {"FINISHED"}


class SCENE_OT_NodesAsJSON_Panel_Import(bpy.types.Operator):
    bl_idname = "scene.nodes_as_json_import"
    bl_label = "Import"
    bl_options = {"REGISTER", "UNDO"}

    input_file: bpy.props.StringProperty(name="Input File", default=DEFAULT_FILE, subtype="FILE_PATH")  # type: ignore
    allow_version_mismatch: bpy.props.BoolProperty(name="Ignore Version", default=False)  # type: ignore
    overwrite: bpy.props.BoolProperty(name="Overwrite", default=False)  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, _context):
        import_nodes(
            input_file=self.input_file,
            specific_handlers=BUILT_IN_DESERIALIZERS,
            allow_version_mismatch=self.allow_version_mismatch,
            overwrite=self.overwrite,
        )
        return {"FINISHED"}


class SCENE_PT_NodesAsJSON_Panel(bpy.types.Panel):
    bl_label = "Nodes As JSON"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Nodes As JSON"

    def draw(self, context):

        node_tree = context.space_data.node_tree
        if node_tree is None:
            self.layout.label(text="No node tree.")
            return

        is_material = isinstance(context.space_data.id, bpy.types.Material)
        if is_material:
            name = context.space_data.id.name
        else:
            name = context.space_data.node_tree.name

        export_op = self.layout.operator(SCENE_OT_NodesAsJSON_Panel_Export.bl_idname)
        export_op.is_material = is_material
        export_op.name = name

        self.layout.operator(SCENE_OT_NodesAsJSON_Panel_Import.bl_idname)
