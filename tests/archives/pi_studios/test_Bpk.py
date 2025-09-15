import pytest

from breki import libraries
from breki.archives import pi_studios


library = libraries.GameLibrary.from_config()
bpk_dirs: libraries.LibraryGames = {
    "Xbox360": {
        "Quake Arena Arcade": ["QuakeArenaArcade/baseq3/"]}}
# NOTE: this may be the only publically existing Pi Studios .bpk

bpks = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(bpk_dirs, "*.bpk")
    for short_path, full_path in paths}


@pytest.mark.parametrize("filepath", bpks.values(), ids=bpks.keys())
def test_from_file(filepath: str):
    bpk = pi_studios.Bpk.from_file(filepath)
    assert isinstance(bpk.headers, list)
    assert isinstance(bpk.files, list)
    # NOTE: no .namelist() or .read() yet
    # TODO: .read() w/ leading "./"
