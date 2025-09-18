# https://en.wikipedia.org/wiki/Alcohol_120%25
# https://github.com/jkbenaim/mds2iso/blob/master/mds2iso.c
import enum
import os
from typing import List

from .. import binary
from .. import core
from .. import files
from . import base


class MediaType(enum.Enum):
    CD_ROM = 0
    CD_R = 1
    CD_RW = 2
    DVD_ROM = 16
    DVD_R = 18


class MdsHeader(core.Struct):
    __slots__ = [
        "magic", "version", "media_type", "num_sessions",
        "unknown_1", "bca_length", "unknown_2", "bca_offset",
        "unknown_3", "disc_struct_offset", "unknown_4",
        "sessions_offset", "dpm_offset"]
    _format = "16s2B2HIH15I"  # 88 bytes
    _arrays = {
        "version": ["major", "minor"],
        "unknown_2": 2, "unknown_3": 6, "unknown_4": 3}
    _classes = {"media_type": MediaType}


class MdsSessionHeader(core.Struct):
    __slots__ = [
        "first_sector", "last_sector", "num_sessions", "num_tracks",
        "num_tracks_2", "first_track", "last_track", "unknown",
        "tracks_offset"]
    _format = "2IH2B2H2I"


# NOTE: currently unused
class TrackMode(enum.Enum):
    NONE = 0x00
    DVD = 0x02
    AUDIO = 0xA9
    MODE1 = 0xAA
    MODE2 = 0xAB
    MODE2_FORM1 = 0xAC
    MODE2_FORM2 = 0xAD
    MODE2_SUB = 0xEC  # Mode2 w/ subchannels


class MdsTrack(core.Struct):
    index: int  # track_number
    first_sector: int
    num_sectors: int
    sector_size: int
    unknown: List[int]  # 7x 0
    num_filenames: int
    filenames_offset: int  # absolute
    __slots__ = [
        "index", "first_sector", "num_sectors", "sector_size",
        "unknown", "num_filenames", "filenames_offset"]
    _format = "13I"
    _arrays = {"unknown": 7}


class Mds(base.DiscImage, files.BinaryFile):
    """Media Descriptor Sidecar"""
    exts = ["*.mds"]
    # NOTE: needs linked .mdf (Media Descriptor File) data files
    header: MdsHeader
    session_header: MdsSessionHeader  # 1x, not per-session?
    mds_tracks: {List[MdsTrack]: List[str]}
    # ^ {MdsTrack: ["filename"]}

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.mds_tracks = dict()

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        # NOTE: only have 1 test file at present
        self.header = MdsHeader.from_stream(self.stream)
        assert self.header.magic == b"MEDIA DESCRIPTOR"
        assert self.header.version.major == 1
        assert self.header.version.minor == 3
        # sessions
        assert self.header.sessions_offset == 0
        self.stream.seek(self.header.sessions_offset, 1)
        self.session_header = MdsSessionHeader.from_stream(self.stream)
        # NOTE: track offset is a lie
        assert self.session_header.tracks_offset > self.size
        # self.stream.seek(self.session_header.tracks_offset, 1)
        self.mds_tracks = {
            MdsTrack.from_stream(self.stream): list()
            for i in range(self.session_header.num_tracks)}
        # NOTE: skipping a few thousand bytes of mystery data (mostly empty)
        # get external track files
        for track in self.mds_tracks:
            first_sector = track.first_sector
            assert track.num_filenames > 0, "track has no filenames"
            for i in range(track.num_filenames):
                self.stream.seek(track.filenames_offset + (16 * i))
                # parse filename offset
                offset, a, b, c = binary.read_struct(self.stream, "4I")
                assert (a, b, c) == (0, 0, 0)
                # get filename
                self.stream.seek(offset)
                filename = binary.read_str(self.stream, *self.code_page)
                self.mds_tracks[track].append(filename)  # keep a note
                # make a friend
                filepath = os.path.join(self.folder, filename)
                friend = files.File(filepath, self.archive)
                friend.type = files.DataType.BINARY
                self.friends[filename] = friend
                # generate track from friend
                assert track.sector_size == 2048, "track mode matters"
                assert friend.size % track.sector_size == 0, "unexpected EOF"
                num_sectors = friend.size // track.sector_size
                # NOTE: guessing track mode, since sector_size is 2048
                self.tracks.append(base.Track(
                    base.TrackMode.BINARY_1, track.sector_size,
                    first_sector, num_sectors, filename))
                first_sector += num_sectors
            assert first_sector - track.first_sector == track.num_sectors, "bad num_sectors"
