import bpy

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import bpy._typing.rna_enums as rna_enums  # ty: ignore[unresolved-import]


from pathlib import Path

from ..id_data_getter import make_id_data_getter
from ..dynamic_pointer import add_all_known_pointer_properties
from ..common import GETTER, DEFAULT_FILE

from ..specific_handlers import (
    BUILT_IN_IMPORTER,
)
from ..import_nodes import ImportParameters, ImportIntermediate


_INTERMEDIATE_IMPORT_CACHE = None


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
