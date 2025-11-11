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

from .panel import (
    SCENE_PT_NodesAsJSON_Panel,
    SCENE_PT_NodesAsJSON_Panel_Export,
    SCENE_PT_NodesAsJSON_Panel_Import,
)

classes = [
    SCENE_PT_NodesAsJSON_Panel,
    SCENE_PT_NodesAsJSON_Panel_Export,
    SCENE_PT_NodesAsJSON_Panel_Import,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
