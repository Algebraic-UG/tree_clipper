import bpy
import _rna_info as rna_info  # ty:ignore[unresolved-import]

import pytest

from .util import all_subclasses
from .test_all_nodes import test_all_nodes


@pytest.fixture(autouse=True)
def reset_blender():
    bpy.ops.wm.read_factory_settings(app_template="", use_empty=False)


def pytest_generate_tests(metafunc):
    # Blender doc generation does this to force type creation which is otherwise lazy
    # https://github.com/blender/blender/blob/19891e0faa60e6c3cadc093ba871bc850c9233d4/doc/python_api/sphinx_doc_gen.py#L65
    rna_info.BuildRNAInfo()

    # we're only interested in the "leaf" types
    node_types = set(
        cls for cls in all_subclasses(bpy.types.Node) if len(all_subclasses(cls)) == 0
    )

    if metafunc.function == test_all_nodes:
        metafunc.parametrize("node_type", node_types)
