import bpy

from pathlib import Path

from .util import save_failed, round_trip_with_same_external, make_everything_local

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

_DIR = Path("tests") / "binary_blend_files" / "erindales_nodevember_2025"


def test_erindales_nodevember_01():
    path = _DIR / testdata[0]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

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


def test_erindales_nodevember_02():
    path = _DIR / testdata[1]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="02 Fire", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)

        round_trip_with_same_external(name="02 Fire", is_material=True)
        round_trip_with_same_external(name="Backdrop", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_02.__name__}")
        raise


def test_erindales_nodevember_03():
    path = _DIR / testdata[2]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="03 Ice ", is_material=False)
        round_trip_with_same_external(name="03 Ice Edge Card", is_material=False)
        round_trip_with_same_external(name="03 Ice Smalls", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Separate Cylindrical", is_material=False)
        round_trip_with_same_external(name="Tune Image", is_material=False)

        round_trip_with_same_external(name="03 Ice", is_material=True)
        round_trip_with_same_external(name="03 Ice Edge Breaker", is_material=True)
        round_trip_with_same_external(name="Backdrop", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_03.__name__}")
        raise


def test_erindales_nodevember_04():
    path = _DIR / testdata[3]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="04 Bouquet", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Tune Image", is_material=False)

        round_trip_with_same_external(name="04 Bouquet", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_04.__name__}")
        raise


def test_erindales_nodevember_05():
    path = _DIR / testdata[4]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="05 Feather", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Rounded Square Mask", is_material=False)
        round_trip_with_same_external(name="Tune Image", is_material=False)
        round_trip_with_same_external(name="Vignette", is_material=False)

        round_trip_with_same_external(name="05 Feather", is_material=True)
        round_trip_with_same_external(name="Backdrop", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_05.__name__}")
        raise


def test_erindales_nodevember_06():
    path = _DIR / testdata[5]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="06 Rivetted", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)

        round_trip_with_same_external(name="06 Rivetted", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_06.__name__}")
        raise


def test_erindales_nodevember_07():
    path = _DIR / testdata[6]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="07 Precious", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Chromatic Aberration", is_material=False)
        round_trip_with_same_external(name="Rounded Square Mask", is_material=False)
        round_trip_with_same_external(name="Tune Image", is_material=False)
        round_trip_with_same_external(name="Vignette", is_material=False)

        round_trip_with_same_external(name="Precious Her", is_material=True)
        round_trip_with_same_external(name="Precious Him", is_material=True)
        round_trip_with_same_external(name="Precious Phone", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_07.__name__}")
        raise


def test_erindales_nodevember_08():
    path = _DIR / testdata[7]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="08 Bejewelled", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Rounded Square Mask", is_material=False)
        round_trip_with_same_external(name="Vignette", is_material=False)
        round_trip_with_same_external(name="Sensor Noise", is_material=False)

        round_trip_with_same_external(name="Fabric", is_material=True)
        round_trip_with_same_external(name="Floor", is_material=True)
        round_trip_with_same_external(name="Gambeson", is_material=True)
        round_trip_with_same_external(name="Gold", is_material=True)
        round_trip_with_same_external(name="Rope", is_material=True)
        round_trip_with_same_external(name="Ruby", is_material=True)
        round_trip_with_same_external(name="Saphire", is_material=True)
        round_trip_with_same_external(name="Steel", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_08.__name__}")
        raise


def test_erindales_nodevember_09():
    path = _DIR / testdata[8]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="09 Soft", is_material=False)
        round_trip_with_same_external(name="Camera FOV Clip", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Simple Painterly", is_material=False)
        round_trip_with_same_external(name="Chromatic Aberration", is_material=False)
        round_trip_with_same_external(name="Rounded Square Mask", is_material=False)
        round_trip_with_same_external(name="Sensor Noise", is_material=False)
        round_trip_with_same_external(name="Vignette", is_material=False)

        round_trip_with_same_external(name="Grass", is_material=True)
        round_trip_with_same_external(name="Ground", is_material=True)
        round_trip_with_same_external(name="Lens", is_material=True)
        round_trip_with_same_external(name="Seeds", is_material=True)
        round_trip_with_same_external(name="Stone", is_material=True)
        round_trip_with_same_external(name="Water", is_material=True)
        round_trip_with_same_external(name="Wood", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_09.__name__}")
        raise


def test_erindales_nodevember_10():
    path = _DIR / testdata[9]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="10 Zip", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Simple Painterly", is_material=False)
        round_trip_with_same_external(name="Rounded Square Mask", is_material=False)
        round_trip_with_same_external(name="Sensor Noise", is_material=False)
        round_trip_with_same_external(name="Tune Image", is_material=False)
        round_trip_with_same_external(name="Vignette", is_material=False)

        round_trip_with_same_external(name="10 Zip", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_10.__name__}")
        raise


def test_erindales_nodevember_11():
    path = _DIR / testdata[10]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="11 Hive", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Chromatic Aberration", is_material=False)
        round_trip_with_same_external(name="Rounded Square Mask", is_material=False)
        round_trip_with_same_external(name="Sensor Noise", is_material=False)
        round_trip_with_same_external(name="Vignette", is_material=False)

        round_trip_with_same_external(name="Ground", is_material=True)
        round_trip_with_same_external(name="Honey", is_material=True)
        round_trip_with_same_external(name="Honeycomb", is_material=True)
        round_trip_with_same_external(name="Wood", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_11.__name__}")
        raise


def test_erindales_nodevember_12():
    path = _DIR / testdata[11]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="12 Monument", is_material=False)

        round_trip_with_same_external(name="Compositing Nodetree", is_material=False)
        round_trip_with_same_external(name="Deform", is_material=False)
        round_trip_with_same_external(name="Simple Painterly", is_material=False)
        round_trip_with_same_external(name="Sensor Noise", is_material=False)

        round_trip_with_same_external(name="12 Monument", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_11.__name__}")
        raise


def test_erindales_nodevember_13():
    path = _DIR / testdata[12]
    try:
        bpy.ops.wm.open_mainfile(filepath=str(path))
        make_everything_local()

        round_trip_with_same_external(name="13 Cabin", is_material=False)

        round_trip_with_same_external("Compositing Nodetree", is_material=False)
        round_trip_with_same_external("Compositing Nodetree.001", is_material=False)
        round_trip_with_same_external("Simple Painterly", is_material=False)
        round_trip_with_same_external("Chromatic Aberration", is_material=False)
        round_trip_with_same_external("Rounded Square Mask", is_material=False)
        round_trip_with_same_external("Sensor Noise", is_material=False)
        round_trip_with_same_external("Vignette", is_material=False)

        round_trip_with_same_external(name="13 Cabin", is_material=True)

    except:
        # store in case of failure for easy debugging
        save_failed(f"{test_erindales_nodevember_13.__name__}")
        raise
