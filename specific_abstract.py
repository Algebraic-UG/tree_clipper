from __future__ import annotations

import bpy

from types import NoneType
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, ClassVar, Type, cast


from .common import FromRoot, no_clobber
from .export_nodes import Exporter
from .import_nodes import GETTER, Importer


T = TypeVar("T", bound=bpy.types.bpy_struct)


# these are filled either manually, or by defining subclasses of the abstract ones below
_BUILT_IN_EXPORTER = {
    NoneType: lambda _exporter, _obj, _from_root: {},
}
_BUILT_IN_IMPORTER = {
    NoneType: lambda _importer, _obj, _getter, _serialization, _from_root: {},
}


class SpecificExporter(Generic[T], ABC):
    """Helper class for specific exporting.
    One can also just define functions but this is more convenient.

    Either this:

    ```
    def _export_node_tree(
        exporter: Exporter,
        node_tree: bpy.types.NodeTree,
        from_root: FromRoot,
    ):
        ...
    no_clobber(_BUILT_IN_EXPORTER, bpy.types.NodeTree, _export_node_tree)
    ```

    or this:
    ```
    class NodeTreeExporter(SpecificExporter[bpy.types.NodeTree]):
        # able to access self.obj with type hints!
        def serialize(self):
            ...
    ```
    """

    # the concrete bpy type for this subclass, e.g. bpy.types.NodeTree
    assumed_type: ClassVar[Type[T]]

    # this does three things
    # 1. fetch the type we want to treat and store it in `assumed_type`
    # 2. wrap the class construction and call to serialize
    # 3. register in _BUILT_IN_EXPORTER
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # 1.
        # Infer T from: class Foo(SpecificExporter[SomeType]):
        # it's a bit complicated to allow for multiple base classes
        # (if you wanted that for some reason)
        t_arg: Type[bpy.types.bpy_struct] | None = None
        for base in getattr(cls, "__orig_bases__", ()):
            origin = getattr(base, "__origin__", None)
            if origin is SpecificExporter:
                (t_arg,) = base.__args__
                break

        if t_arg is None:
            raise TypeError(
                f"{cls.__name__} must specify a type parameter, "
                "e.g. class NodeTreeExport(SpecificExporter[bpy.types.NodeTree])"
            )

        cls.assumed_type = t_arg

        # 2.
        # this is so much more convinient than writing this out for each function!
        def wrapper(
            exporter: Exporter,
            obj: T,
            from_root: FromRoot,
        ):
            inst = cls(
                exporter=exporter,
                obj=obj,
                from_root=from_root,
            )
            return inst.serialize()

        # 3.
        # This also makes sure that we register as the correct type, DRY!
        no_clobber(_BUILT_IN_EXPORTER, t_arg, wrapper)

    # this is only called in the wrapper
    def __init__(
        self,
        *,
        exporter: Exporter,
        obj: T,
        from_root: FromRoot,
    ):
        self.exporter = exporter
        self.obj = obj
        self.from_root = from_root

    def export_all_simple_writable_properties(self):
        return self.exporter.export_all_simple_writable_properties(
            obj=self.obj,
            assumed_type=self.assumed_type,
            from_root=self.from_root,
        )

    def export_properties_from_id_list(self, id_list: list[str]):
        return self.exporter.export_properties_from_id_list(
            obj=self.obj,
            properties=id_list,
            from_root=self.from_root,
        )

    def export_all_simple_writable_properties_and_list(self, id_list: list[str]):
        d = self.export_all_simple_writable_properties()
        for identifier, data in self.export_properties_from_id_list(id_list).items():
            no_clobber(d, identifier, data)
        return d

    @abstractmethod
    def serialize(self) -> None:
        """Do the actual exporting here"""


class SpecificImporter(Generic[T], ABC):
    """Helper class for specific importing.
    One can also just define functions but this is more convenient.

    Either this:

    ```
    def _import_node_tree(
        importer: Importer,
        node_tree: bpy.types.NodeTree,
        getter: GETTER,
        serialization: dict,
        from_root: FromRoot,
    ):
        ...
    no_clobber(_BUILT_IN_IMPORTER, bpy.types.NodeTree, _import_node_tree)
    ```

    or this:
    ```
    class NodeTreeImporter(SpecificImporter[bpy.types.NodeTree]):
        # able to access self.obj with type hints!
        def deserialize(self):
            ...
    ```
    """

    # the concrete bpy type for this subclass, e.g. bpy.types.NodeTree
    assumed_type: ClassVar[Type[T]]

    # this does three things
    # 1. fetch the type we want to treat and store it in `assumed_type`
    # 2. wrap the class construction and call to deserialize
    # 3. register in _BUILT_IN_IMPORTER
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # 1.
        # Infer T from: class Foo(SpecificImporter[SomeType]):
        # it's a bit complicated to allow for multiple base classes
        # (if you wanted that for some reason)
        t_arg: Type[bpy.types.bpy_struct] | None = None
        for base in getattr(cls, "__orig_bases__", ()):
            origin = getattr(base, "__origin__", None)
            if origin is SpecificImporter:
                (t_arg,) = base.__args__
                break

        if t_arg is None:
            raise TypeError(
                f"{cls.__name__} must specify a type parameter, "
                "e.g. class NodeTreeImport(SpecificImporter[bpy.types.NodeTree])"
            )

        cls.assumed_type = t_arg

        # 2.
        # this is so much more convinient than writing this out for each function!
        def wrapper(
            importer: Importer,
            obj: T,
            getter: GETTER,
            serialization: dict,
            from_root: FromRoot,
        ):
            inst = cls(
                importer=importer,
                obj=obj,
                getter=getter,
                serialization=serialization,
                from_root=from_root,
            )
            inst.deserialize()

        # 3.
        # This also makes sure that we register as the correct type, DRY!
        no_clobber(_BUILT_IN_IMPORTER, t_arg, wrapper)

    # this is only called in the wrapper
    def __init__(
        self,
        *,
        importer: Importer,
        obj: T,
        getter: GETTER,
        serialization: dict,
        from_root: FromRoot,
    ):
        self.importer = importer
        self.obj = obj
        self.getter = getter
        self.serialization = serialization
        self.from_root = from_root

    def import_all_simple_writable_properties(self):
        self.importer.import_all_simple_writable_properties(
            obj=self.obj,
            getter=self.getter,
            serialization=self.serialization,
            assumed_type=self.assumed_type,
            from_root=self.from_root,
        )

    def import_properties_from_id_list(self, id_list: list[str]):
        self.importer.import_properties_from_id_list(
            obj=self.obj,
            getter=self.getter,
            serialization=self.serialization,
            properties=id_list,
            from_root=self.from_root,
        )

    def import_all_simple_writable_properties_and_list(self, id_list: list[str]):
        self.import_all_simple_writable_properties()
        self.import_properties_from_id_list(id_list)

    @abstractmethod
    def deserialize(self) -> None:
        """Do the actual importing here"""
