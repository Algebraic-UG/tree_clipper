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

from .ui import (
    Tree_Clipper_External_Item,
    SCENE_UL_Tree_Clipper_External_List,
    SCENE_OT_Tree_Clipper_Export_Cache,
    SCENE_OT_Tree_Clipper_Export_Prepare,
    SCENE_OT_Tree_Clipper_Import_Cache,
    SCENE_OT_Tree_Clipper_Import_Prepare,
    SCENE_PT_Tree_Clipper_Panel,
)

classes = [
    Tree_Clipper_External_Item,
    SCENE_UL_Tree_Clipper_External_List,
    SCENE_OT_Tree_Clipper_Export_Cache,
    SCENE_OT_Tree_Clipper_Export_Prepare,
    SCENE_OT_Tree_Clipper_Import_Cache,
    SCENE_OT_Tree_Clipper_Import_Prepare,
    SCENE_PT_Tree_Clipper_Panel,
]


def register() -> None:
    print("reloaded")
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister() -> None:
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
