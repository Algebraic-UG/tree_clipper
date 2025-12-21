import bpy

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import bpy._typing.rna_enums as rna_enums  # ty: ignore[unresolved-import]


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
        return context.window_manager.invoke_props_dialog(self)

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

        while _INTERMEDIATE_EXPORT_CACHE.step():
            pass

        report = _INTERMEDIATE_EXPORT_CACHE.exporter.report
        self.report(
            {"INFO"},
            f"Exported {report.exported_trees} trees, {report.exported_nodes} nodes, and {report.exported_links} links",
        )
        for warning in report.warnings:
            self.report({"WARNING"}, warning)

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_export_cache("INVOKE_DEFAULT")  # ty: ignore[unresolved-attribute]
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "is_material")
        self.layout.prop(
            self, "name", text="Material" if self.is_material else "Node Tree"
        )
        head, body = self.layout.panel("advanced", default_closed=True)
        head.label(text="Advanced")
        if body is not None:
            body.prop(self, "export_sub_trees")
            body.prop(self, "debug_prints")
            body.prop(self, "write_from_roots")


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
        return context.window_manager.invoke_props_dialog(self, width=600)

    def execute(
        self, context: bpy.types.Context
    ) -> set["rna_enums.OperatorReturnItems"]:
        global _INTERMEDIATE_EXPORT_CACHE
        assert isinstance(_INTERMEDIATE_EXPORT_CACHE, ExportIntermediate)
        _INTERMEDIATE_EXPORT_CACHE.set_external(
            (external_item.external_id, external_item.description)
            for external_item in self.external_items
            if not external_item.skip
        )
        _INTERMEDIATE_EXPORT_CACHE.export_to_file(
            file_path=Path(self.output_file),
            compress=self.compress,
            json_indent=self.json_indent,
        )
        _INTERMEDIATE_EXPORT_CACHE = None
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context) -> None:
        self.layout.prop(self, "output_file")
        self.layout.prop(self, "compress")
        if not self.compress:
            self.layout.prop(self, "json_indent")
        if len(self.external_items) == 0:
            return
        self.layout.label(text="References to External:")
        self.layout.template_list(
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
        head, body = self.layout.panel("details", default_closed=True)
        head.label(text="Item Details")
        if body is not None:
            body.label(text=f"Id in JSON: {pointer.pointer_id}")
            body.label(text="Referenced at:")
            for path_elem in pointer.from_root.path:
                body.label(text="    -> " + path_elem)
