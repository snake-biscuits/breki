import pytest

import os

# archive modules
from breki.archives import padus
from breki.archives import pkware
# function
from breki.archives import search_folder

from breki import libraries


cdi_dirs: libraries.LibraryGames
cdi_dirs = {
    "Dreamcast": {
        "Disc Images": [""]}}  # not looking in subdirs


library = libraries.GameLibrary.from_config()
cdis = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(cdi_dirs, "*.cdi")
    for short_path, full_path in paths}


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


# scan inside zip files
if library.Dreamcast is not None:
    search_args = (pkware.Zip, library.Dreamcast, "*.cdi")
    zip_cdis = {
        f"Dreamcast | Archives | {os.path.split(cdi_)[-1]}": (zip_, cdi_)
        for zip_, zip_cdis in search_folder(*search_args).items()
        for cdi_ in zip_cdis}
    zip_cdis = {
        id_: (os.path.join(library.Dreamcast, zip_), cdi_)
        for id_, (zip_, cdi_) in zip_cdis.items()}


@pytest.mark.parametrize(
    "zip_filepath,cdi_filepath", zip_cdis.values(), ids=zip_cdis.keys())
def test_from_archive(zip_filepath: str, cdi_filepath: str):
    try:
        zip_ = pkware.Zip.from_file(zip_filepath)
        zip_.parse()
        assert zip_.is_parsed
    except Exception as exc:
        pytest.xfail(f"couldn't parse Zip: {exc}")
    cdi = padus.Cdi.from_archive(zip_, cdi_filepath)
    if not cdi.is_parsed:
        cdi.parse()
    assert cdi.is_parsed
    # check tracks & track data
    assert len(cdi.tracks) != 0
    assert len(cdi.friends) == len(cdi.tracks)
    for track in cdi.tracks:
        assert track.name in cdi.friends
