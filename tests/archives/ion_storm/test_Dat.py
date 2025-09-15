import pytest

from breki import libraries
from breki.archives import ion_storm


library = libraries.GameLibrary.from_config()
dat_dirs: libraries.LibraryGames = {
    "Steam": {
        "Anachronox": ["Anachronox/anoxdata"]}}

dats = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(dat_dirs, "*.dat")
    for short_path, full_path in paths}


@pytest.mark.parametrize("filepath", dats.values(), ids=dats.keys())
def test_from_file(filepath: str):
    dat = ion_storm.Dat.from_file(filepath)
    namelist = dat.namelist()
    assert isinstance(namelist, list), ".namelist() failed"
    if len(namelist) != 0:
        first_file = dat.read(namelist[0])
        assert isinstance(first_file, bytes), ".read() failed"
        # TODO: .read() w/ leading "./"
