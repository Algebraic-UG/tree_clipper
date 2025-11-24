import bpy


from pathlib import Path
import tempfile

from .specific_handlers import (
    BUILT_IN_EXPORTER,
    BUILT_IN_IMPORTER,
)
from .export_nodes import ExportParameters, ExportIntermediate
from .import_nodes import ImportParameters, ImportIntermediate

DEFAULT_FILE = str(Path(tempfile.gettempdir()) / "default.json")

_INTERMEDIATE_EXPORT_CACHE = None
_INTERMEDIATE_IMPORT_CACHE = None


class SCENE_OT_Tree_Clipper_Export_Prepare(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_export_prepare"
    bl_label = "Export"
    bl_options = {"REGISTER"}

    is_material: bpy.props.BoolProperty(name="Top level Material")  # type: ignore
    name: bpy.props.StringProperty(name="Material/NodeTree")  # type: ignore

    export_sub_trees: bpy.props.BoolProperty(name="Export Sub Trees", default=True)  # type: ignore
    skip_defaults: bpy.props.BoolProperty(name="Skip Defaults", default=True)  # type: ignore
    debug_prints: bpy.props.BoolProperty(name="Debug on Console", default=False)  # type: ignore
    write_from_roots: bpy.props.BoolProperty(name="Add Paths", default=False)  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, _context):
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

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_export_cache("INVOKE_DEFAULT")
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


class SCENE_UL_Tree_Clipper_External_List(bpy.types.UIList):
    def draw_item(
        self,
        _context,
        layout,
        _data,
        item,
        _icon,
        _active_data,
        _active_property,
    ):
        external = _INTERMEDIATE_EXPORT_CACHE.get_external()[item.external_id]
        pointer = external.pointed_to_by[item.idx]
        row = layout.row()
        row.prop(item, "description")
        row.prop(pointer.obj, pointer.identifier)


class Tree_Clipper_External_Item(bpy.types.PropertyGroup):
    external_id: bpy.props.IntProperty()  # type: ignore
    idx: bpy.props.IntProperty()  # type: ignore
    description: bpy.props.StringProperty(name="", default="Hint for Import")  # type: ignore


class SCENE_OT_Tree_Clipper_Export_Cache(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_export_cache"
    bl_label = "Export Cache"
    bl_options = {"REGISTER"}

    output_file: bpy.props.StringProperty(
        name="Output File",
        default=DEFAULT_FILE,
        subtype="FILE_PATH",
    )  # type: ignore

    compress: bpy.props.BoolProperty(name="Compress", default=True)  # type: ignore
    json_indent: bpy.props.IntProperty(name="JSON Indent", default=4, min=0)  # type: ignore

    external_items: bpy.props.CollectionProperty(type=Tree_Clipper_External_Item)  # type: ignore
    selected_external_item: bpy.props.IntProperty()  # type: ignore

    def invoke(self, context, _):
        self.external_items.clear()
        for external_id, external in _INTERMEDIATE_EXPORT_CACHE.get_external().items():
            for idx in range(len(external.pointed_to_by)):
                item = self.external_items.add()
                item.external_id = external_id
                item.idx = idx
        return context.window_manager.invoke_props_dialog(self, width=600)

    def execute(self, _context):
        global _INTERMEDIATE_EXPORT_CACHE
        _INTERMEDIATE_EXPORT_CACHE.export_to_file(
            file_path=Path(self.output_file),
            compress=self.compress,
            json_indent=self.json_indent,
        )
        _INTERMEDIATE_EXPORT_CACHE = None
        return {"FINISHED"}

    def draw(self, _context):
        self.layout.prop(self, "output_file")
        self.layout.prop(self, "compress")
        if not self.compress:
            self.layout.prop(self, "json_indent")
        if len(self.external_items) == 0:
            return
        self.layout.label(text="References to External:")
        self.layout.template_list(
            listtype_name="SCENE_UL_Tree_Clipper_External_List",
            list_id="",
            dataptr=self,
            propname="external_items",
            active_dataptr=self,
            active_propname="selected_external_item",
        )
        external_item = self.external_items[self.selected_external_item]
        external = _INTERMEDIATE_EXPORT_CACHE.get_external()[external_item.external_id]
        pointer = external.pointed_to_by[external_item.idx]
        head, body = self.layout.panel("details", default_closed=True)
        head.label(text="Item Details")
        if body is not None:
            body.label(text="Referenced at:")
            for path_elem in pointer.from_root.path:
                body.label(text="    -> " + path_elem)


class SCENE_OT_Tree_Clipper_Import_Prepare(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_import_prepare"
    bl_label = "Import"
    bl_options = {"REGISTER"}

    input_file: bpy.props.StringProperty(
        name="Input File",
        default=DEFAULT_FILE,
        subtype="FILE_PATH",
    )  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, _context):
        global _INTERMEDIATE_IMPORT_CACHE
        _INTERMEDIATE_IMPORT_CACHE = ImportIntermediate()
        _INTERMEDIATE_IMPORT_CACHE.from_file(Path(self.input_file))

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_import_cache("INVOKE_DEFAULT")
        return {"FINISHED"}


class SCENE_OT_Tree_Clipper_Import_Cache(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_import_cache"
    bl_label = "Import Cache"
    bl_options = {"REGISTER", "UNDO"}

    overwrite: bpy.props.BoolProperty(name="Overwrite", default=True)  # type: ignore

    allow_version_mismatch: bpy.props.BoolProperty(name="Ignore Version", default=False)  # type: ignore
    debug_prints: bpy.props.BoolProperty(name="Debug on Console", default=False)  # type: ignore

    def invoke(self, context, _):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, _context):
        global _INTERMEDIATE_IMPORT_CACHE
        _INTERMEDIATE_IMPORT_CACHE.import_nodes(
            ImportParameters(
                specific_handlers=BUILT_IN_IMPORTER,
                allow_version_mismatch=self.allow_version_mismatch,
                # TODO: put external things here https://github.com/Algebraic-UG/tree_clipper/issues/16
                getters={},
                overwrite=self.overwrite,
                debug_prints=self.debug_prints,
            )
        )
        _INTERMEDIATE_IMPORT_CACHE = None
        return {"FINISHED"}

    def draw(self, _context):
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

        self.layout.separator()

        self.layout.operator(SCENE_OT_Tree_Clipper_Import_Prepare.bl_idname)
