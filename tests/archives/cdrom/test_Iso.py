import pytest

import os

# archive modules
from breki.archives.base import DiscImage, TrackMode
from breki.archives import cdrom
from breki.archives import golden_hawk
# from breki.archives import padus
from breki.archives import pkware
# from breki.archives import sega
# function
from breki.archives import search_folder

from breki import libraries


library = libraries.GameLibrary.from_config()
disc_dirs: libraries.LibraryGames = {
    "Dreamcast": {
        "Disc Images": [""]}}  # not looking in subdirs

disc_classes = [
    # ("Cdi", "*.cdi", padus.Cdi),
    ("Cue", "*.cue", golden_hawk.Cue),
    # ("Gdi", "*.gdi", sega.Gdi),
]
# NOTE: don't have any `*.cdi` or `*.gdi` w/ a CD-ROM filesystem

discs = {
    f"{section} | {game} | {id_} | {short_path}": (cls, full_path)
    for id_, ext, cls in disc_classes
    for section, game, paths in library.scan(disc_dirs, ext)
    for short_path, full_path in paths}

# scan inside zip files
zip_discs = dict()
if library.Dreamcast is not None:
    for cls_id, pattern, disc_class in disc_classes:
        search_args = (pkware.Zip, library.Dreamcast, pattern)
        for zip_filepath, disc_filepaths in search_folder(*search_args).items():
            zip_filepath = os.path.join(library.Dreamcast, zip_filepath)
            for disc_filepath in disc_filepaths:
                id_ = " | ".join([
                    "Dreamcast", "Archives", cls_id,
                    os.path.basename(disc_filepath)])
                zip_discs[id_] = (disc_class, zip_filepath, disc_filepath)


@pytest.mark.parametrize("disc_class,filepath", discs.values(), ids=discs.keys())
def test_from_disc_file(disc_class: DiscImage, filepath: str):
    try:
        disc = disc_class.from_file(filepath)
        disc.parse()
        # check tracks & track data
        assert len(disc.tracks) != 0
        assert len(disc.friends) == len(disc.tracks)
        for track in disc.tracks:
            assert track.name in disc.friends
    except Exception:
        pytest.xfail(f"couldn't parse disc: {disc_class=}")

    if 16 not in disc:
        pytest.xfail("default PVD not found on disc")
    if disc.sector_track(16).mode == TrackMode.AUDIO:
        pytest.xfail("default PVD is inside an AUDIO track")

    cd = cdrom.Iso.from_disc(disc)
    cd.parse()
    assert cd.is_parsed
    assert hasattr(cd, "pvd")
    # TODO: namelist()
    # TODO: .is_file() / .is_dir()
    # TODO: .read()
    # TODO: filepath w/ leading "./"


@pytest.mark.parametrize(
    "disc_class,zip_filepath,disc_filepath", zip_discs.values(), ids=zip_discs.keys())
def test_from_archive(disc_class: DiscImage, zip_filepath: str, disc_filepath: str):
    try:
        zip_ = pkware.Zip.from_file(zip_filepath)
        zip_.parse()
    except Exception as exc:
        pytest.xfail(f"couldn't parse Zip: {exc}")
    try:
        disc = disc_class.from_archive(zip_, disc_filepath)
        disc.parse()
        # check tracks & track data
        assert len(disc.tracks) != 0
        assert len(disc.friends) == len(disc.tracks)
        for track in disc.tracks:
            assert track.name in disc.friends
    except Exception as exc:
        pytest.xfail(f"couldn't parse {disc_class.__name__}: {exc}")

    if 16 not in disc:
        pytest.xfail("default PVD not found on disc")
    if disc.sector_track(16).mode == TrackMode.AUDIO:
        pytest.xfail("default PVD is inside an AUDIO track")

    cd = cdrom.Iso.from_disc(disc)
    cd.parse()
    assert cd.is_parsed
    assert hasattr(cd, "pvd")
    # TODO: namelist()
    # TODO: .is_file() / .is_dir()
    # TODO: .read()
    # TODO: filepath w/ leading "./"
