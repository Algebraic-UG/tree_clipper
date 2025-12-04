import bpy
import _rna_info as rna_info

from .util import make_test_node_tree
from .test_all_nodes import test_all_nodes


def _all_subclasses(cls):
    subclasses = set(cls.__subclasses__())
    for subclass in cls.__subclasses__():
        subclasses.update(_all_subclasses(subclass))
    return subclasses


def pytest_generate_tests(metafunc):
    # Blender doc generation does this to force type creation which is otherwise lazy
    # https://github.com/blender/blender/blob/19891e0faa60e6c3cadc093ba871bc850c9233d4/doc/python_api/sphinx_doc_gen.py#L65
    rna_info.BuildRNAInfo()

    # we're only interested in the "leaf" types
    node_types = set(
        cls for cls in _all_subclasses(bpy.types.Node) if len(_all_subclasses(cls)) == 0
    )

    if metafunc.function == test_all_nodes:
        metafunc.parametrize("node_type", node_types)
