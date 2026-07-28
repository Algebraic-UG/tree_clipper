import bpy  # noqa: I001
import _rna_info as rna_info

import pytest

from .test_all_nodes import test_all_nodes
from .test_backwards_compatibility import test_backwards_compatibility_to_0_1_1
from .util import BACKWARDS_COMPATIBILITY_FILES_DIR, all_subclasses


@pytest.fixture(autouse=True)
def reset_blender():
    bpy.ops.wm.read_factory_settings(app_template="", use_empty=False)


def pytest_generate_tests(metafunc):
    # Blender doc generation does this to force type creation which is otherwise lazy
    # https://github.com/blender/blender/blob/19891e0faa60e6c3cadc093ba871bc850c9233d4/doc/python_api/sphinx_doc_gen.py#L65
    rna_info.BuildRNAInfo()

    # we're only interested in the "leaf" types
    node_types = {
        cls for cls in all_subclasses(bpy.types.Node) if len(all_subclasses(cls)) == 0
    }

    if metafunc.function == test_all_nodes:
        metafunc.parametrize("node_type", node_types)

    exports_from_0_1_1 = [
        str(p) for p in (BACKWARDS_COMPATIBILITY_FILES_DIR / "v0.1.1").rglob("*.json")
    ]

    if metafunc.function == test_backwards_compatibility_to_0_1_1:
        metafunc.parametrize("file", exports_from_0_1_1)
