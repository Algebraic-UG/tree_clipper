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
    SCENE_PT_NodesAsJSON_Panel,
    SCENE_OT_NodesAsJSON_Panel_Export,
    SCENE_OT_NodesAsJSON_Panel_Import,
)

classes = [
    SCENE_PT_NodesAsJSON_Panel,
    SCENE_OT_NodesAsJSON_Panel_Export,
    SCENE_OT_NodesAsJSON_Panel_Import,
]

import _rna_info as rna_info  # Blender module.


def playground():
    rna_info.BuildRNAInfo()

    t = bpy.types.Node

    def all_subclasses(cls):
        """Return a set of all subclasses (recursive) of a given class."""
        subclasses = set(cls.__subclasses__())
        for subclass in cls.__subclasses__():
            subclasses.update(all_subclasses(subclass))
        return subclasses

    subs = all_subclasses(t)
    print("SUBCLASSES ==============================================")
    print("\n".join([cls.__name__ for cls in subs]))
    print(len(subs))

    def all_leafclasses(cls):
        return set(c for c in all_subclasses(cls) if len(all_subclasses(c)) == 0)

    leafs = all_leafclasses(t)

    print("LEAVES ==============================================")
    print("\n".join([cls.__name__ for cls in leafs]))
    print(len(leafs))

    def unique_props(cls):
        return [
            p
            for p in cls.bl_rna.properties
            if p.identifier not in [p.identifier for p in cls.bl_rna.base.properties]
        ]

    def collection_props(cls):
        return [prop for prop in unique_props(cls) if prop.type == "COLLECTION"]

    with_coll = [cls for cls in leafs if collection_props(cls)]

    print("WITH COLLECTIONS ==============================================")
    print("\n".join([cls.__name__ for cls in with_coll]))
    print(len(with_coll))

    def pointer_props(cls):
        return [prop for prop in unique_props(cls) if prop.type == "POINTER"]

    with_pointer = [cls for cls in leafs if pointer_props(cls)]

    print("WITH POINTERS ==============================================")
    print("\n".join([cls.__name__ for cls in with_pointer]))
    print(len(with_pointer))


def register():
    bpy.app.timers.register(playground)
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
