import pytest

from breki import libraries
from breki.archives import ion_storm


library = libraries.GameLibrary.from_config()
pak_dirs: libraries.LibraryGames = {
    "Steam": {
        "Daikatana": ["Daikatana/data"]}}

paks = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(pak_dirs, "*.pak")
    for short_path, full_path in paths}


@pytest.mark.parametrize("filename", paks.values(), ids=paks.keys())
def test_from_file(filename: str):
    pak = ion_storm.Pak.from_file(filename)
    namelist = pak.namelist()
    assert isinstance(namelist, list), ".namelist() failed"
    # NOTE: all entries in pak2.pak are compressed
    # -- decompression takes approx. 1min per MB
    if len(namelist) != 0:
        first_file = pak.read(namelist[0])
        assert isinstance(first_file, bytes), ".read() failed"
        # TODO: .read() w/ leading "./"
