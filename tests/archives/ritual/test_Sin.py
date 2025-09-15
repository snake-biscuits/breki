import pytest

from breki import libraries
from breki.archives import ritual


library = libraries.GameLibrary.from_config()
sin_dirs: libraries.LibraryGames = {
    "Steam": {
        "SiN (2015)": ["SiN 1/2015"],
        "SiN (base)": ["SiN 1/base"],
        "SiN (ctf)": ["SiN 1/ctf"],
        "SiN Multiplayer (2015)": ["SiN 1 Multiplayer/2015"],
        "SiN Multiplayer (base)": ["SiN 1 Multiplayer/base"],
        "SiN Multiplayer (ctf)": ["SiN 1 Multiplayer/ctf"]}}

sins = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(sin_dirs, "*.sin")
    for short_path, full_path in paths}


@pytest.mark.parametrize("filepath", sins.values(), ids=sins.keys())
def test_from_file(filepath: str):
    sin = ritual.Sin.from_file(filepath)
    assert not sin.is_parsed
    namelist = sin.namelist()
    assert sin.is_parsed
    assert isinstance(namelist, list), ".namelist() failed"
    if len(namelist) != 0:
        first_file = sin.read(namelist[0])
        assert isinstance(first_file, bytes), ".read() failed"
    # TODO: .read() w/ leading "./"
