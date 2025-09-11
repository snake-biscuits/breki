import pytest

import os

# archive modules
from breki.archives import golden_hawk
from breki.archives import pkware
# function
from breki.archives import search_folder
from breki import libraries


cue_dirs: libraries.LibraryGames
cue_dirs = {
    "Dreamcast": {
        "Disc Images": [""]}}  # not looking in subdirs


library = libraries.game_library()
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
    for track in cue.tracks:
        assert track.name in cue.friends
