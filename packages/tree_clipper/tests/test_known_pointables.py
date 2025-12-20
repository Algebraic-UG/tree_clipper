import deepdiff
import bpy
import _rna_info as rna_info  # ty:ignore[unresolved-import]

from tree_clipper.dynamic_pointer import KNOWN_POINTABLES

from .util import all_subclasses


def test_known_pointables():
    # TODO: it seems that it's not possible to create a writable pointer property
    # that is pointing to a custom type, meaning one that is derived from a PropertyGroup.
    # If this is somehow possible we'll need to revisit this.
    # pointable_groups = set(
    #    cls
    #    for cls in _all_subclasses(bpy.types.PropertyGroup)
    #    if getattr(cls, "is_registered", False)
    # )
    # pointable_ids = _all_subclasses(bpy.types.ID)
    # pointables = pointable_groups.union(pointable_ids)

    # Blender doc generation does this to force type creation which is otherwise lazy
    # https://github.com/blender/blender/blob/19891e0faa60e6c3cadc093ba871bc850c9233d4/doc/python_api/sphinx_doc_gen.py#L65
    rna_info.BuildRNAInfo()

    pointables = all_subclasses(bpy.types.ID)

    diff = deepdiff.DeepDiff(KNOWN_POINTABLES, pointables)

    print(diff.pretty())
    assert diff == {}
