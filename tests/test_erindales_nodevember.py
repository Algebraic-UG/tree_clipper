import bpy

from pathlib import Path

from .util import save_failed, round_trip_with_same_external

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

        round_trip_with_same_external(name="Pumpkin", is_material=False)
        round_trip_with_same_external(name="Foliage", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)

        round_trip_with_same_external(name="Candle Flame", is_material=True)
        round_trip_with_same_external(name="Candle Wax", is_material=True)
        round_trip_with_same_external(name="Grass", is_material=True)
        round_trip_with_same_external(name="Material", is_material=True)
        round_trip_with_same_external(name="Pumpkin", is_material=True)
        round_trip_with_same_external(name="Stalk", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_01.__name__}")
        raise
