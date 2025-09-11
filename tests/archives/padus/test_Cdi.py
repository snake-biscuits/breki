import pytest

from breki.archives import padus
from breki import libraries


cdi_dirs: libraries.LibraryGames
cdi_dirs = {
    "Dreamcast": {
        "Disc Images": [""]}}  # not looking in subdirs


library = libraries.game_library()
cdis = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(cdi_dirs, "*.cdi")
    for short_path, full_path in paths}
# TODO: check inside `.zip`s


@pytest.mark.parametrize("filename", cdis.values(), ids=cdis.keys())
def test_from_file(filename: str):
    cdi = padus.Cdi.from_file(filename)
    if not cdi.is_parsed:
        cdi.parse()
    assert cdi.is_parsed
    # check tracks & track data
    assert len(cdi.tracks) != 0
    assert len(cdi.friends) == len(cdi.tracks)
    for track in cdi.tracks:
        assert track.name in cdi.friends
