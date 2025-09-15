import pytest

from breki import libraries
from breki.archives import infinity_ward


iwd_dirs: libraries.LibraryGames
iwd_dirs = {
    "Steam": {
        "Call of Duty 2": ["Call of Duty 2/main/"]}}


library = libraries.GameLibrary.from_config()
iwds = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(iwd_dirs, "*.iwd")
    for short_path, full_path in paths}


@pytest.mark.parametrize("filepath", iwds.values(), ids=iwds.keys())
def test_from_file(filepath: str):
    iwd = infinity_ward.Iwd.from_file(filepath)
    namelist = iwd.namelist()
    assert isinstance(namelist, list), ".namelist() failed"
    if len(namelist) != 0:
        first_file = iwd.read(namelist[0])
        assert isinstance(first_file, bytes), ".read() failed"
