import bpy


from pathlib import Path
import tempfile

from .specific_handlers import (
    BUILT_IN_EXPORTER,
    BUILT_IN_IMPORTER,
)
from .export_nodes import ExportParameters, ExportIntermediate
from .import_nodes import ImportParameters, import_nodes_from_file

DEFAULT_FILE = str(Path(tempfile.gettempdir()) / "default.json")

_INTERMEDIATE_EXPORT_CACHE = None


def force_ui_redraw():
    for area in bpy.context.window.screen.areas:
        if area.type == "NODE_EDITOR":
            area.tag_redraw()


class SCENE_OT_Tree_Clipper_Export_Prepare(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_export_prepare"
    bl_label = "Prepare Export"
    bl_options = {"REGISTER"}

    is_material: bpy.props.BoolProperty(name="Top level Material")  # type: ignore
    name: bpy.props.StringProperty(name="Material/NodeTree")  # type: ignore

    export_sub_trees: bpy.props.BoolProperty(name="Export Sub Trees", default=True)  # type: ignore
    skip_defaults: bpy.props.BoolProperty(name="Skip Defaults", default=True)  # type: ignore
    debug_prints: bpy.props.BoolProperty(name="Debug on Console", default=False)  # type: ignore
    write_from_roots: bpy.props.BoolProperty(name="Add Paths", default=False)  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        global _INTERMEDIATE_EXPORT_CACHE
        _INTERMEDIATE_EXPORT_CACHE = ExportIntermediate(
            ExportParameters(
                is_material=self.is_material,
                name=self.name,
                specific_handlers=BUILT_IN_EXPORTER,
                export_sub_trees=self.export_sub_trees,
                skip_defaults=self.skip_defaults,
                debug_prints=self.debug_prints,
                write_from_roots=self.write_from_roots,
            )
        )

        # otherwise the cache buttons aren't shown until the panel is mouse-overed
        force_ui_redraw()

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_export_finalize("INVOKE_DEFAULT")
        return {"FINISHED"}

    def draw(self, _context):
        self.layout.prop(self, "is_material")
        self.layout.prop(
            self, "name", text="Material" if self.is_material else "Node Tree"
        )
        head, body = self.layout.panel("advanced", default_closed=True)
        head.label(text="Advanced")
        if body is not None:
            body.prop(self, "export_sub_trees")
            body.prop(self, "skip_defaults")
            body.prop(self, "debug_prints")
            body.prop(self, "write_from_roots")


class SCENE_OT_Tree_Clipper_Export_Clear_Cache(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_export_clear_cache"
    bl_label = "Clear Cache"
    bl_options = {"REGISTER"}

    def execute(_self, _context):
        global _INTERMEDIATE_EXPORT_CACHE
        _INTERMEDIATE_EXPORT_CACHE = None
        return {"FINISHED"}


class SCENE_OT_Tree_Clipper_Export_Finalize(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_export_finalize"
    bl_label = "Finalize Cache"
    bl_options = {"REGISTER"}

    output_file: bpy.props.StringProperty(
        name="Output File",
        default=DEFAULT_FILE,
        subtype="FILE_PATH",
    )  # type: ignore

    compress: bpy.props.BoolProperty(name="Compress", default=True)  # type: ignore
    json_indent: bpy.props.IntProperty(name="JSON Indent", default=4, min=0)  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, _context):
        _INTERMEDIATE_EXPORT_CACHE.export_to_file(
            file_path=Path(self.output_file),
            compress=self.compress,
            json_indent=self.json_indent,
        )
        return {"FINISHED"}

    def draw(self, _context):
        self.layout.prop(self, "output_file")
        self.layout.prop(self, "compress")
        if not self.compress:
            self.layout.prop(self, "json_indent")


class SCENE_OT_Tree_Clipper_Import(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_import"
    bl_label = "Import"
    bl_options = {"REGISTER", "UNDO"}

    input_file: bpy.props.StringProperty(
        name="Input File",
        default=DEFAULT_FILE,
        subtype="FILE_PATH",
    )  # type: ignore
    overwrite: bpy.props.BoolProperty(name="Overwrite", default=True)  # type: ignore

    allow_version_mismatch: bpy.props.BoolProperty(name="Ignore Version", default=False)  # type: ignore
    debug_prints: bpy.props.BoolProperty(name="Debug on Console", default=False)  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, _context):
        import_nodes_from_file(
            file_path=Path(self.input_file),
            parameters=ImportParameters(
                specific_handlers=BUILT_IN_IMPORTER,
                allow_version_mismatch=self.allow_version_mismatch,
                # TODO: put external things here https://github.com/Algebraic-UG/tree_clipper/issues/16
                getters={},
                overwrite=self.overwrite,
                debug_prints=self.debug_prints,
            ),
        )

        return {"FINISHED"}

    def draw(self, _context):
        self.layout.prop(self, "input_file")
        self.layout.prop(self, "overwrite")
        head, body = self.layout.panel("advanced", default_closed=True)
        head.label(text="Advanced")
        if body is not None:
            body.prop(self, "allow_version_mismatch")
            body.prop(self, "debug_prints")


class SCENE_PT_Tree_Clipper_Panel(bpy.types.Panel):
    bl_label = "Tree Clipper"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Tree Clipper"

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

        export_op = self.layout.operator(SCENE_OT_Tree_Clipper_Export_Prepare.bl_idname)
        export_op.is_material = is_material
        export_op.name = name

        if _INTERMEDIATE_EXPORT_CACHE is not None:
            export_cached = self.layout.row()
            export_cached.operator(SCENE_OT_Tree_Clipper_Export_Finalize.bl_idname)
            export_cached.operator(SCENE_OT_Tree_Clipper_Export_Clear_Cache.bl_idname)

        self.layout.operator(SCENE_OT_Tree_Clipper_Import.bl_idname)
