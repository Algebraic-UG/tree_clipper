# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy

from .ui.operators_export import (
    Tree_Clipper_External_Export_Item,
    SCENE_UL_Tree_Clipper_External_Export_List,
    SCENE_OT_Tree_Clipper_Export_Cache,
    SCENE_OT_Tree_Clipper_Export_Prepare,
)

from .ui.operators_import import (
    Tree_Clipper_External_Import_Item,
    Tree_Clipper_External_Import_Items,
    SCENE_UL_Tree_Clipper_External_Import_List,
    SCENE_OT_Tree_Clipper_Import_Cache,
    SCENE_OT_Tree_Clipper_Import_Prepare,
)

from .ui import SCENE_PT_Tree_Clipper_Panel

classes = [
    Tree_Clipper_External_Export_Item,
    SCENE_UL_Tree_Clipper_External_Export_List,
    SCENE_OT_Tree_Clipper_Export_Cache,
    SCENE_OT_Tree_Clipper_Export_Prepare,
    Tree_Clipper_External_Import_Item,
    Tree_Clipper_External_Import_Items,
    SCENE_UL_Tree_Clipper_External_Import_List,
    SCENE_OT_Tree_Clipper_Import_Cache,
    SCENE_OT_Tree_Clipper_Import_Prepare,
    SCENE_PT_Tree_Clipper_Panel,
]


def register() -> None:
    print("reloaded")
    for cls in classes:
        bpy.utils.register_class(cls)
    # the pointer properties in the items make it impossible to store on the operator
    bpy.types.Scene.tree_clipper_external_import_items = bpy.props.PointerProperty(  # ty: ignore[unresolved-attribute]
        type=Tree_Clipper_External_Import_Items
    )


def unregister() -> None:
    del bpy.types.Scene.tree_clipper_external_import_items  # ty: ignore[unresolved-attribute]
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
