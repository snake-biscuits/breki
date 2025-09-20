import pytest

import os

from breki import libraries
# archive modules
from breki.archives import golden_hawk
from breki.archives import pkware
# function
from breki.archives import search_folder


library = libraries.GameLibrary.from_config()
cue_dirs: libraries.LibraryGames = {
    "Dreamcast": {
        "Disc Images": [""]}}  # not looking in subdirs

cues = {
    f"{section} | {game} | {short_path}": full_path
    for section, game, paths in library.scan(cue_dirs, "*.cue")
    for short_path, full_path in paths}


@pytest.mark.parametrize(
    "filepath", cues.values(), ids=cues.keys())
def test_from_file(filepath: str):
    cue = golden_hawk.Cue.from_file(filepath)
    if not cue.is_parsed:
        cue.parse()
    assert cue.is_parsed
    # check tracks & track data
    assert len(cue.tracks) != 0
    assert len(cue.friends) == len(cue.tracks)
    for track in cue.tracks:
        assert track.name in cue.friends


# scan inside zip files
zip_cues = dict()
if library.Dreamcast is not None:
    search_args = (pkware.Zip, library.Dreamcast, "*.cue")
    zip_cues = {
        f"Dreamcast | Archives | {os.path.split(cue_)[-1]}": (zip_, cue_)
        for zip_, zip_cues in search_folder(*search_args).items()
        for cue_ in zip_cues}
    zip_cues = {
        id_: (os.path.join(library.Dreamcast, zip_), cue_)
        for id_, (zip_, cue_) in zip_cues.items()}


@pytest.mark.parametrize(
    "zip_filepath,cue_filepath", zip_cues.values(), ids=zip_cues.keys())
def test_from_archive(zip_filepath: str, cue_filepath: str):
    zip_ = pkware.Zip.from_file(zip_filepath)
    cue = golden_hawk.Cue.from_archive(zip_, cue_filepath)
    if not cue.is_parsed:
        cue.parse()
    assert cue.is_parsed
    # check tracks & track data
    assert len(cue.tracks) != 0
    assert len(cue.friends) == len(cue.tracks)
    start_lbas = [track.start_lba for track in cue.tracks]
    # NOTE: SINGLE DENSITY AREA is optional
    assert start_lbas.count(45000) == 1, "no high density area"
    prev_end = 0
    for track in cue.tracks:
        assert track.name in cue.friends
        if track.start_lba != 45000:  # HIGH DENSITY AREA always starts @ 45000
            assert track.start_lba == prev_end
        prev_end = track.start_lba + track.length
