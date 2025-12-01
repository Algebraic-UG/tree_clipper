import bpy

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import bpy._typing.rna_enums as rna_enums  # ty: ignore[unresolved-import]


from pathlib import Path
import tempfile

from .id_data_getter import make_id_data_getter
from .dynamic_pointer import add_all_known_pointer_properties
from .common import GETTER

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
                skip_defaults=self.skip_defaults,
                debug_prints=self.debug_prints,
                write_from_roots=self.write_from_roots,
            )
        )

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
            body.prop(self, "skip_defaults")
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
        for item in self.external_items:
            cached_item = _INTERMEDIATE_EXPORT_CACHE.get_external()[item.external_id]
            cached_item.description = item.description
            cached_item.skip = item.skip
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


class SCENE_OT_Tree_Clipper_Import_Prepare(bpy.types.Operator):
    bl_idname = "scene.tree_clipper_import_prepare"
    bl_label = "Import"
    bl_options = {"REGISTER"}

    input_file: bpy.props.StringProperty(
        name="Input File",
        default=DEFAULT_FILE,
        subtype="FILE_PATH",
    )  # type: ignore

    def invoke(
        self, context: bpy.types.Context, event: bpy.types.Event
    ) -> set["rna_enums.OperatorReturnItems"]:
        return context.window_manager.invoke_props_dialog(self)

    def execute(
        self, context: bpy.types.Context
    ) -> set["rna_enums.OperatorReturnItems"]:
        global _INTERMEDIATE_IMPORT_CACHE
        _INTERMEDIATE_IMPORT_CACHE = ImportIntermediate()
        _INTERMEDIATE_IMPORT_CACHE.from_file(Path(self.input_file))

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
    bl_options = {"REGISTER", "UNDO"}

    overwrite: bpy.props.BoolProperty(name="Overwrite", default=True)  # type: ignore

    allow_version_mismatch: bpy.props.BoolProperty(name="Ignore Version", default=False)  # type: ignore
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
            if external_item["skip"]:
                continue
            item = context.scene.tree_clipper_external_import_items.items.add()
            item.external_id = int(external_id)
            item.description = external_item["description"]
            item.set_active_pointer_type(external_item["fixed_type_name"])

        return context.window_manager.invoke_props_dialog(self)

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
        getters: dict[int, GETTER] = dict(
            (
                external_item.external_id,
                make_id_data_getter(
                    getattr(
                        external_item, external_item.get_active_pointer_identifier()
                    )
                ),
            )
            for external_item in context.scene.tree_clipper_external_import_items.items
        )

        # double check that only skipped ones are missing
        for (
            external_id,
            external_item,
        ) in _INTERMEDIATE_IMPORT_CACHE.get_external().items():
            if external_item["skip"]:
                getters[int(external_id)] = lambda: None
            else:
                assert int(external_id) in getters

        _INTERMEDIATE_IMPORT_CACHE.import_nodes(
            ImportParameters(
                specific_handlers=BUILT_IN_IMPORTER,
                allow_version_mismatch=self.allow_version_mismatch,
                getters=getters,
                overwrite=self.overwrite,
                debug_prints=self.debug_prints,
            )
        )
        _INTERMEDIATE_IMPORT_CACHE = None
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context) -> None:
        assert hasattr(context.scene, "tree_clipper_external_import_items")
        assert isinstance(
            context.scene.tree_clipper_external_import_items,
            Tree_Clipper_External_Import_Items,
        )
        self.layout.prop(self, "overwrite")
        head, body = self.layout.panel("advanced", default_closed=True)
        head.label(text="Advanced")
        if body is not None:
            body.prop(self, "allow_version_mismatch")
            body.prop(self, "debug_prints")
        if len(context.scene.tree_clipper_external_import_items.items) == 0:
            return
        self.layout.label(text="References to External:")
        self.layout.template_list(
            listtype_name="SCENE_UL_Tree_Clipper_External_Import_List",
            list_id="",
            dataptr=context.scene.tree_clipper_external_import_items,
            propname="items",
            active_dataptr=context.scene.tree_clipper_external_import_items,
            active_propname="selected",
        )


class SCENE_PT_Tree_Clipper_Panel(bpy.types.Panel):
    bl_label = "Tree Clipper"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "Tree Clipper"

    def draw(self, context: bpy.types.Context) -> None:
        assert isinstance(context.space_data, bpy.types.SpaceNodeEditor)

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

        self.layout.operator(SCENE_OT_Tree_Clipper_Import_Prepare.bl_idname)
