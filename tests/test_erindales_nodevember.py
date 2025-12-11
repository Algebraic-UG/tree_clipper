import bpy

from tests.util import save_failed
from tree_clipper.import_nodes import ImportIntermediate, ImportParameters
from tree_clipper.specific_handlers import BUILT_IN_EXPORTER, BUILT_IN_IMPORTER
from tree_clipper.export_nodes import ExportIntermediate, ExportParameters
from pathlib import Path

import pytest

testdata = [
    "01 Pumpkin.blend",  # "https://www.patreon.com/file?h=142546933&m=557444276"
    "02 Fire 2.blend",  # "https://www.patreon.com/file?h=142684584&m=558482337"
    "03 Ice.blend",  # "https://www.patreon.com/file?h=142740029&m=558876052"
    "04 Bouquet 2.blend",  # "https://www.patreon.com/file?h=142989683&m=560585416"
    "05 Feather.blend",  # "https://www.patreon.com/file?h=143208083&m=562194268"
    "06 Rivetted.blend",  # "https://www.patreon.com/file?h=143211117&m=562217374"
    "07 Precious.blend",  # "https://www.patreon.com/file?h=143354206&m=563224402"
    "08 Bejewelled.blend",  # "https://www.patreon.com/file?h=144050634&m=568106345"
    "09 Soft.blend",  # "https://www.patreon.com/file?h=144413788&m=570742561"
    "10 Zip.blend",  # "https://www.patreon.com/file?h=144415098&m=570752167"
    "11 Hive.blend",  # "https://www.patreon.com/file?h=144490070&m=571267284"
    "12 Monument 4.blend",  # "https://www.patreon.com/file?h=144619214&m=572188000"
    "13 Cabin.blend",  # "https://www.patreon.com/file?h=144813310&m=573633551"
]

_DIR = Path("tests") / "erindale" / "nodevember_2025"


def test_erindales_nodevember_01():
    path = _DIR / testdata[0]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))

        export_intermediate = ExportIntermediate(
            parameters=ExportParameters(
                is_material=False,
                name="Pumpkin",
                specific_handlers=BUILT_IN_EXPORTER,
                export_sub_trees=True,
                skip_defaults=True,
                debug_prints=True,
                write_from_roots=False,
            )
        )

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_01.__name__}")
        raise
