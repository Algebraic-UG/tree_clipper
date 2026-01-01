import bpy

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import bpy._typing.rna_enums as rna_enums  # type: ignore


from pathlib import Path

from ._vendor.tree_clipper.common import DEFAULT_FILE

from ._vendor.tree_clipper.specific_handlers import (
    BUILT_IN_EXPORTER,
)
from ._vendor.tree_clipper.export_nodes import ExportParameters, ExportIntermediate


_INTERMEDIATE_EXPORT_CACHE = None


class SCENE_OT_Tree_Clipper_Export_Prepare(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_export_prepare"
    bl_label = "Export"
    bl_options = {"REGISTER"}

    is_material: bpy.props.BoolProperty(name="Top level Material")  # type: ignore
    name: bpy.props.StringProperty(name="Material/NodeTree")  # type: ignore

    export_sub_trees: bpy.props.BoolProperty(name="Export Sub Trees", default=True)  # type: ignore
    debug_prints: bpy.props.BoolProperty(name="Debug on Console", default=False)  # type: ignore
    write_from_roots: bpy.props.BoolProperty(name="Add Paths", default=False)  # type: ignore

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set["rna_enums.OperatorReturnItems"]:
        return context.window_manager.invoke_props_dialog(self)  # ty:ignore[possibly-missing-attribute]

    def execute(
        self, context: bpy.types.Context
    ) -> set["rna_enums.OperatorReturnItems"]:
        global _INTERMEDIATE_EXPORT_CACHE
        _INTERMEDIATE_EXPORT_CACHE = ExportIntermediate(
            ExportParameters(
                is_material=self.is_material,
                name=self.name,
                specific_handlers=BUILT_IN_EXPORTER,
                export_sub_trees=self.export_sub_trees,
                debug_prints=self.debug_prints,
                write_from_roots=self.write_from_roots,
            )
        )

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_export_modal("INVOKE_DEFAULT")  # ty: ignore[unresolved-attribute]
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "is_material")  # ty:ignore[possibly-missing-attribute]
        self.layout.prop(  # ty:ignore[possibly-missing-attribute]
            self, "name", text="Material" if self.is_material else "Node Tree"
        )
        head, body = self.layout.panel("advanced", default_closed=True)  # ty:ignore[possibly-missing-attribute]
        head.label(text="Advanced")
        if body is not None:
            body.prop(self, "export_sub_trees")
            body.prop(self, "debug_prints")
            body.prop(self, "write_from_roots")


class SCENE_OT_Tree_Clipper_Export_Modal(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_export_modal"
    bl_label = "Export Modal"
    bl_options = set()

    _timer = None

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set["rna_enums.OperatorReturnItems"]:
        assert isinstance(_INTERMEDIATE_EXPORT_CACHE, ExportIntermediate)
        self._timer = context.window_manager.event_timer_add(0, window=context.window)  # ty:ignore[possibly-missing-attribute]
        context.window_manager.progress_begin(0, _INTERMEDIATE_EXPORT_CACHE.total_steps)  # ty:ignore[possibly-missing-attribute]
        context.window_manager.modal_handler_add(self)  # ty:ignore[possibly-missing-attribute]

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        global _INTERMEDIATE_EXPORT_CACHE
        assert isinstance(_INTERMEDIATE_EXPORT_CACHE, ExportIntermediate)

        if event.type in {"RIGHTMOUSE", "ESC"}:
            context.window_manager.event_timer_remove(self._timer)
            _INTERMEDIATE_EXPORT_CACHE = None
            return {"CANCELLED"}

        if _INTERMEDIATE_EXPORT_CACHE.step():
            context.window_manager.progress_update(
                _INTERMEDIATE_EXPORT_CACHE.progress()
            )
            return {"RUNNING_MODAL"}

        context.window_manager.progress_end()
        report = _INTERMEDIATE_EXPORT_CACHE.exporter.report
        self.report(
            {"INFO"},
            f"Exported {report.exported_trees} trees, {report.exported_nodes} nodes, and {report.exported_links} links",
        )
        for warning in _INTERMEDIATE_EXPORT_CACHE.exporter.report.warnings:
            self.report({"WARNING"}, warning)

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_export_cache("INVOKE_DEFAULT")  # ty: ignore[unresolved-attribute]
        return {"FINISHED"}


class SCENE_UL_Tree_Clipper_External_Export_List(bpy.types.UIList):
    def draw_item(
        self,
        context: bpy.types.Context,
        layout: bpy.types.UILayout,
        data: Any | None,
        item: Any | None,
        icon: int | None,
        active_data: Any,
        active_property: str | None,
        index: int | None,
        flt_flag: int | None,
    ) -> None:
        assert isinstance(_INTERMEDIATE_EXPORT_CACHE, ExportIntermediate)
        assert isinstance(item, Tree_Clipper_External_Export_Item)
        external = _INTERMEDIATE_EXPORT_CACHE.get_external()[item.external_id]
        pointer = external.pointed_to_by
        row = layout.row()
        row.prop(item, "description")
        row.prop(pointer.obj, pointer.identifier, text="")
        row.prop(item, "skip")


class Tree_Clipper_External_Export_Item(bpy.types.PropertyGroup):
    external_id: bpy.props.IntProperty()  # type: ignore
    description: bpy.props.StringProperty(name="", default="Hint for Import")  # type: ignore
    skip: bpy.props.BoolProperty(name="Hide in Import", default=False)  # type: ignore


_COMPRESS = "Compress"
_JSON = "JSON"
_CLIPBOARD = "Clipboard"
_FILE = "File"


class SCENE_OT_Tree_Clipper_Export_Cache(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_export_cache"
    bl_label = "Export Cache"
    bl_options = set()

    clipboard_or_file: bpy.props.EnumProperty(items=[(_CLIPBOARD,) * 3, (_FILE,) * 3])  # type: ignore
    output_file: bpy.props.StringProperty(
        name="Output File",
        default=DEFAULT_FILE,
        subtype="FILE_PATH",
    )  # type: ignore

    compress_or_json: bpy.props.EnumProperty(items=[(_COMPRESS,) * 3, (_JSON,) * 3])  # type: ignore
    json_indent: bpy.props.IntProperty(name="JSON Indent", default=4, min=0)  # type: ignore

    external_items: bpy.props.CollectionProperty(type=Tree_Clipper_External_Export_Item)  # type: ignore
    selected_external_item: bpy.props.IntProperty()  # type: ignore

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set["rna_enums.OperatorReturnItems"]:
        self.external_items.clear()
        assert isinstance(_INTERMEDIATE_EXPORT_CACHE, ExportIntermediate)
        for external_id in _INTERMEDIATE_EXPORT_CACHE.get_external().keys():
            item = self.external_items.add()
            item.external_id = external_id
        return context.window_manager.invoke_props_dialog(self, width=300)  # ty:ignore[possibly-missing-attribute]

    def execute(
        self, context: bpy.types.Context
    ) -> set["rna_enums.OperatorReturnItems"]:
        global _INTERMEDIATE_EXPORT_CACHE
        assert isinstance(_INTERMEDIATE_EXPORT_CACHE, ExportIntermediate)

        clipboard = self.clipboard_or_file == _CLIPBOARD
        compress = self.compress_or_json == _COMPRESS

        _INTERMEDIATE_EXPORT_CACHE.set_external(
            (external_item.external_id, external_item.description)
            for external_item in self.external_items
            if not external_item.skip
        )
        if clipboard:
            bpy.context.window_manager.clipboard = (  # ty:ignore[invalid-assignment]
                _INTERMEDIATE_EXPORT_CACHE.export_to_str(
                    compress=compress,
                    json_indent=self.json_indent,
                )
            )
        else:
            _INTERMEDIATE_EXPORT_CACHE.export_to_file(
                file_path=Path(self.output_file),
                compress=compress,
                json_indent=self.json_indent,
            )
        _INTERMEDIATE_EXPORT_CACHE = None
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "clipboard_or_file", expand=True)  # ty:ignore[possibly-missing-attribute]
        clipboard = self.clipboard_or_file == _CLIPBOARD

        file_col = self.layout.column()  # ty:ignore[possibly-missing-attribute]
        file_col.prop(self, "output_file")  # ty:ignore[possibly-missing-attribute]
        file_col.enabled = not clipboard

        self.layout.prop(self, "compress_or_json", expand=True)  # ty:ignore[possibly-missing-attribute]
        compress = self.compress_or_json == _COMPRESS

        json_col = self.layout.column()  # ty:ignore[possibly-missing-attribute]
        json_col.prop(self, "json_indent")  # ty:ignore[possibly-missing-attribute]
        json_col.enabled = not compress

        if len(self.external_items) == 0:
            return

        self.layout.label(text="References to External:")  # ty:ignore[possibly-missing-attribute]
        self.layout.template_list(  # ty:ignore[possibly-missing-attribute]
            listtype_name="SCENE_UL_Tree_Clipper_External_Export_List",
            list_id="",
            dataptr=self,
            propname="external_items",
            active_dataptr=self,
            active_propname="selected_external_item",
        )
        external_item = self.external_items[self.selected_external_item]
        assert isinstance(_INTERMEDIATE_EXPORT_CACHE, ExportIntermediate)
        external = _INTERMEDIATE_EXPORT_CACHE.get_external()[external_item.external_id]
        pointer = external.pointed_to_by
        head, body = self.layout.panel("details", default_closed=True)  # ty:ignore[possibly-missing-attribute]
        head.label(text="Item Details")
        if body is not None:
            body.label(text=f"Id in JSON: {pointer.pointer_id}")
            body.label(text="Referenced at:")
            for path_elem in pointer.from_root.path:
                body.label(text="    -> " + path_elem)
