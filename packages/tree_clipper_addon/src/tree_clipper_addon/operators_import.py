import bpy

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import bpy._typing.rna_enums as rna_enums  # type: ignore


from pathlib import Path

from ._vendor.tree_clipper.dynamic_pointer import add_all_known_pointer_properties
from ._vendor.tree_clipper.common import DEFAULT_FILE

from ._vendor.tree_clipper.specific_handlers import (
    BUILT_IN_IMPORTER,
)
from ._vendor.tree_clipper.import_nodes import ImportParameters, ImportIntermediate

from .post_import import post_import

_INTERMEDIATE_IMPORT_CACHE = None


class SCENE_OT_Tree_Clipper_Import_File_Prepare(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_import_file_prepare"
    bl_label = "Import File"
    bl_options = {"REGISTER"}

    input_file: bpy.props.StringProperty(
        name="Input File",
        default=DEFAULT_FILE,
        subtype="FILE_PATH",
    )  # type: ignore

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set["rna_enums.OperatorReturnItems"]:
        return context.window_manager.invoke_props_dialog(self)  # ty:ignore[possibly-missing-attribute]

    def execute(
        self, context: bpy.types.Context
    ) -> set["rna_enums.OperatorReturnItems"]:
        global _INTERMEDIATE_IMPORT_CACHE
        _INTERMEDIATE_IMPORT_CACHE = ImportIntermediate(file_path=Path(self.input_file))

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_import_cache("INVOKE_DEFAULT")  # ty: ignore[unresolved-attribute]
        return {"FINISHED"}


class SCENE_OT_Tree_Clipper_Import_Clipboard_Prepare(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_import_clipboard_prepare"
    bl_label = "Import Clipboard"
    bl_options = {"REGISTER"}

    def execute(
        self, context: bpy.types.Context
    ) -> set["rna_enums.OperatorReturnItems"]:
        global _INTERMEDIATE_IMPORT_CACHE
        _INTERMEDIATE_IMPORT_CACHE = ImportIntermediate(
            string=bpy.context.window_manager.clipboard  # ty:ignore[possibly-missing-attribute]
        )

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_import_cache("INVOKE_DEFAULT")  # ty: ignore[unresolved-attribute]
        return {"FINISHED"}


class SCENE_UL_Tree_Clipper_External_Import_List(bpy.types.UIList):
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
        assert isinstance(item, Tree_Clipper_External_Import_Item)
        row = layout.row()
        row.label(text=item.description)
        row.prop(item, item.get_active_pointer_identifier(), text="")


class Tree_Clipper_External_Import_Item(bpy.types.PropertyGroup):
    external_id: bpy.props.IntProperty()  # type: ignore
    description: bpy.props.StringProperty()  # type: ignore


# note that this adds the member functions set_active_pointer_type and get_active_pointer_identifier
add_all_known_pointer_properties(cls=Tree_Clipper_External_Import_Item, prefix="ptr_")


class Tree_Clipper_External_Import_Items(bpy.types.PropertyGroup):
    items: bpy.props.CollectionProperty(type=Tree_Clipper_External_Import_Item)  # type: ignore
    selected: bpy.props.IntProperty()  # type: ignore


class SCENE_OT_Tree_Clipper_Import_Cache(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_import_cache"
    bl_label = "Import Cache"
    bl_options = set()

    debug_prints: bpy.props.BoolProperty(name="Debug on Console", default=False)  # type: ignore

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set["rna_enums.OperatorReturnItems"]:
        assert isinstance(_INTERMEDIATE_IMPORT_CACHE, ImportIntermediate)
        assert hasattr(context.scene, "tree_clipper_external_import_items")
        assert isinstance(
            context.scene.tree_clipper_external_import_items,
            Tree_Clipper_External_Import_Items,
        )
        context.scene.tree_clipper_external_import_items.items.clear()
        for (
            external_id,
            external_item,
        ) in _INTERMEDIATE_IMPORT_CACHE.get_external().items():
            if external_item["description"] is None:
                continue
            item = context.scene.tree_clipper_external_import_items.items.add()
            item.external_id = int(external_id)
            item.description = external_item["description"]
            item.set_active_pointer_type(external_item["fixed_type_name"])

        return context.window_manager.invoke_props_dialog(self)  # ty:ignore[possibly-missing-attribute]

    def execute(
        self, context: bpy.types.Context
    ) -> set["rna_enums.OperatorReturnItems"]:
        global _INTERMEDIATE_IMPORT_CACHE
        assert isinstance(_INTERMEDIATE_IMPORT_CACHE, ImportIntermediate)
        assert hasattr(context.scene, "tree_clipper_external_import_items")
        assert isinstance(
            context.scene.tree_clipper_external_import_items,
            Tree_Clipper_External_Import_Items,
        )

        # collect what is set from the UI
        _INTERMEDIATE_IMPORT_CACHE.set_external(
            (
                external_item.external_id,
                external_item.get_active_pointer(),
            )
            for external_item in context.scene.tree_clipper_external_import_items.items
        )

        _INTERMEDIATE_IMPORT_CACHE.start_import(
            ImportParameters(
                specific_handlers=BUILT_IN_IMPORTER,
                debug_prints=self.debug_prints,
            )
        )

        # seems impossible to use bl_idname here
        bpy.ops.scene.tree_clipper_import_modal("INVOKE_DEFAULT")  # ty: ignore[unresolved-attribute]
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context) -> None:
        assert hasattr(context.scene, "tree_clipper_external_import_items")
        assert isinstance(
            context.scene.tree_clipper_external_import_items,
            Tree_Clipper_External_Import_Items,
        )
        head, body = self.layout.panel("advanced", default_closed=True)  # ty:ignore[possibly-missing-attribute]
        head.label(text="Advanced")
        if body is not None:
            body.prop(self, "debug_prints")
        if len(context.scene.tree_clipper_external_import_items.items) == 0:
            return
        self.layout.label(text="References to External:")  # ty:ignore[possibly-missing-attribute]
        self.layout.template_list(  # ty:ignore[possibly-missing-attribute]
            listtype_name="SCENE_UL_Tree_Clipper_External_Import_List",
            list_id="",
            dataptr=context.scene.tree_clipper_external_import_items,
            propname="items",
            active_dataptr=context.scene.tree_clipper_external_import_items,
            active_propname="selected",
        )


class SCENE_OT_Tree_Clipper_Import_Modal(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_import_modal"
    bl_label = "Import Modal"
    bl_options = {"UNDO"}

    _timer = None

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set["rna_enums.OperatorReturnItems"]:
        assert isinstance(_INTERMEDIATE_IMPORT_CACHE, ImportIntermediate)
        self._timer = context.window_manager.event_timer_add(0, window=context.window)  # ty:ignore[possibly-missing-attribute]
        context.window_manager.progress_begin(0, _INTERMEDIATE_IMPORT_CACHE.total_steps)  # ty:ignore[possibly-missing-attribute]
        context.window_manager.modal_handler_add(self)  # ty:ignore[possibly-missing-attribute]

        return {"RUNNING_MODAL"}

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        global _INTERMEDIATE_IMPORT_CACHE
        assert isinstance(_INTERMEDIATE_IMPORT_CACHE, ImportIntermediate)

        if event.type in {"RIGHTMOUSE", "ESC"}:
            context.window_manager.event_timer_remove(self._timer)
            _INTERMEDIATE_IMPORT_CACHE = None
            return {"FINISHED"}

        if _INTERMEDIATE_IMPORT_CACHE.step():
            context.window_manager.progress_update(
                _INTERMEDIATE_IMPORT_CACHE.progress()
            )
            return {"RUNNING_MODAL"}

        context.window_manager.progress_end()
        report = _INTERMEDIATE_IMPORT_CACHE.importer.report

        if report.rename_material is not None:
            original_name, new_name = report.rename_material
            self.report(
                {"INFO"}, f"Imported material '{original_name}' as '{new_name}'"
            )
        for original_name, new_name in report.renames_node_group.items():
            self.report(
                {"INFO"}, f"Imported node_group '{original_name}' as '{new_name}'"
            )
        self.report(
            {"INFO"},
            f"Imported {report.imported_trees} trees, {report.imported_nodes} nodes, and {report.imported_links} links",
        )

        for warning in report.warnings:
            self.report({"WARNING"}, warning)

        _INTERMEDIATE_IMPORT_CACHE = None

        post_import(context=context, event=event, report=report)

        return {"FINISHED"}
