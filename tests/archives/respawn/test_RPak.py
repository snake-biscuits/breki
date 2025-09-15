import pytest

from breki import libraries
from breki.archives import respawn


library = libraries.GameLibrary.from_config()
rpak_dirs: libraries.LibraryGames = {
    "Steam": {
        "Apex Legends": ["Apex Legends/paks/Win64/"],
        "Titanfall 2": ["Titanfall2/r2/paks/Win64/"]},
    "PS4": {
        "Titanfall 2 (Tech Test)": ["Titanfall2_tech_test/r2/paks/PS4/"]}}

rpaks = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(rpak_dirs, "*.rpak")
    for short_path, full_path in paths}


@pytest.mark.parametrize("filepath", rpaks.values(), ids=rpaks.keys())
def test_from_file(filepath: str):
    rpak = respawn.RPak.from_file(filepath)
    rpak.parse()  # have to parse before checking for compression
    if rpak.header.compression == respawn.rpak.Compression.NONE:
        assert isinstance(rpak.namelist(), list)
        # TODO: test .read() (NotYetImplemented)
        # TODO: .read() w/ leading "./"
    else:
        pytest.xfail("skipping compressed RPak")
