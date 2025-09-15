import pytest

from breki import libraries
from breki.archives import utoplanet


library = libraries.GameLibrary.from_config()
apk_dirs: libraries.LibraryGames = {
    "Mod": {
        "Merubasu": ["Merubasu/shadowland"]}}
# copied from install @ "C:/PlayGra/Merubasu/"

apks = {
    f"{game} | {short_path}": full_path
    for section, game, paths in library.scan(apk_dirs, "*.apk")
    for short_path, full_path in paths}


@pytest.mark.parametrize("filepath", apks.values(), ids=apks.keys())
def test_from_file(filepath: str):
    apk = utoplanet.Apk.from_file(filepath)
    namelist = apk.namelist()
    assert isinstance(namelist, list), ".namelist() failed"
    first_file = apk.read(namelist[0])
    assert isinstance(first_file, bytes), ".read() failed"
