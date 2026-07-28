import tomllib
from pathlib import Path

from tree_clipper.common import CURRENT_TREE_CLIPPER_VERSION


def test_version():
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as file:
        pyproject = tomllib.load(file)
        assert pyproject["project"]["version"] == CURRENT_TREE_CLIPPER_VERSION
