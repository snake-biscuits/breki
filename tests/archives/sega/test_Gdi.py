import pytest

import os

from breki import libraries
# archive modules
from breki.archives import pkware
from breki.archives import sega
# function
from breki.archives import search_folder


library = libraries.GameLibrary.from_config()
gdi_dirs: libraries.LibraryGames = {
    "Dreamcast": {
        "Disc Images": [""]}}  # not looking in subdirs

gdis = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(gdi_dirs, "*.gdi")
    for short_path, full_path in paths}

# scan inside zip files
zip_gdis = dict()
if library.Dreamcast is not None:
    search_args = (pkware.Zip, library.Dreamcast, "*.gdi")
    zip_gdis = {
        f"Dreamcast | Archives | {os.path.split(gdi_)[-1]}": (zip_, gdi_)
        for zip_, zip_gdis in search_folder(*search_args).items()
        for gdi_ in zip_gdis}
    zip_gdis = {
        id_: (os.path.join(library.Dreamcast, zip_), gdi_)
        for id_, (zip_, gdi_) in zip_gdis.items()}


@pytest.mark.parametrize("filename", gdis.values(), ids=gdis.keys())
def test_from_file(filename: str):
    gdi = sega.Gdi.from_file(filename)
    if not gdi.is_parsed:
        gdi.parse()
    assert gdi.is_parsed
    # check tracks & track data
    assert len(gdi.tracks) != 0
    assert len(gdi.friends) == len(gdi.tracks)
    for track in gdi.tracks:
        assert track.name in gdi.friends


@pytest.mark.parametrize(
    "zip_filepath,gdi_filepath", zip_gdis.values(), ids=zip_gdis.keys())
def test_from_archive(zip_filepath: str, gdi_filepath: str):
    zip_ = pkware.Zip.from_file(zip_filepath)
    gdi = sega.Gdi.from_archive(zip_, gdi_filepath)
    if not gdi.is_parsed:
        gdi.parse()
    assert gdi.is_parsed
    # check tracks & track data
    assert len(gdi.tracks) != 0
    assert len(gdi.friends) == len(gdi.tracks)
    for track in gdi.tracks:
        assert track.name in gdi.friends
