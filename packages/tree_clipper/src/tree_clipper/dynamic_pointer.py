import bpy
import _rna_info as rna_info

from typing import Type

from .common import no_clobber


def _all_subclasses(cls):
    subclasses = set(cls.__subclasses__())
    for subclass in cls.__subclasses__():
        subclasses.update(_all_subclasses(subclass))
    return subclasses


def add_all_known_pointer_properties(
    *,
    cls: Type[bpy.types.PropertyGroup],
    prefix: str,
):
    def get_pointer_property_name(ty: type):
        return f"{prefix}{ty.__name__}"

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

    pointables = _all_subclasses(bpy.types.ID)

    # does this even ever happen
    if not hasattr(cls, "__annotations__"):
        cls.__annotations__ = {}

    # we store which kind of thing we're pointing to, used in get_pointer
    no_clobber(
        cls.__annotations__,
        "active_ptr_type_name",
        bpy.props.StringProperty(),
    )

    # now actually register all the properties
    for pointable in pointables:
        no_clobber(
            cls.__annotations__,
            get_pointer_property_name(pointable),
            bpy.props.PointerProperty(type=pointable),
        )

    # this switches the type we're pointing to and clears all
    def set_active_pointer_type(self, type_name: str):
        self.active_ptr_type_name = type_name
        for ty in pointables:
            setattr(self, get_pointer_property_name(ty), None)

    # this is needed to display the property
    def get_active_pointer_identifier(self) -> str:
        return f"{prefix}{self.active_ptr_type_name}"

    # directly return the pointer
    def get_active_pointer(self) -> bpy.types.PointerProperty:
        return getattr(self, self.get_active_pointer_identifier())

    assert not hasattr(cls, set_active_pointer_type.__name__)
    setattr(cls, set_active_pointer_type.__name__, set_active_pointer_type)
    assert not hasattr(cls, get_active_pointer_identifier.__name__)
    setattr(cls, get_active_pointer_identifier.__name__, get_active_pointer_identifier)
    assert not hasattr(cls, get_active_pointer.__name__)
    setattr(cls, get_active_pointer.__name__, get_active_pointer)
