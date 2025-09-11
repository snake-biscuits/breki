"""Dreamcast 'Giga-Disc' Handler"""
# https://multimedia.cx/eggs/understanding-the-dreamcast-gd-rom-layout/

from __future__ import annotations
import fnmatch
import io
from typing import List

from .. import files
from ..files.parsed import parse_first
from . import alcohol
from . import base
from . import cdrom
from . import golden_hawk
from . import mame
from . import padus


class Gdi(base.DiscImage, files.TextFile):
    ext = "*.gdi"

    def parse(self):
        num_tracks = int(self.stream.readline().decode())
        modes = {
            "0": base.TrackMode.AUDIO,
            "4": base.TrackMode.BINARY_1}
        for i, line in enumerate(self.stream):
            line = line.decode().rstrip()
            assert line.count(" ") == 5
            track_number, start_lba, mode, sector_size, name, zero = line.split(" ")
            assert int(track_number) == i + 1
            assert zero == "0"
            mode = modes[mode]
            sector_size = int(sector_size)
            start_lba = int(start_lba)
            # NOTE: length of -1 means we get it from filesize
            self.tracks.append(base.Track(mode, sector_size, start_lba, -1, name))
        assert len(self.tracks) == num_tracks


# Boot Header
class Region:  # string-based flags
    symbols: str
    JPN = 0
    USA = 1
    EUR = 2

    def __init__(self, area_symbols: str):
        assert area_symbols[self.JPN] in "J "
        assert area_symbols[self.USA] in "U "
        assert area_symbols[self.EUR] in "E "
        self.symbols = area_symbols

    def __repr__(self) -> str:
        regions = [
            name
            for i, name in enumerate(("JPN", "USA", "EUR"))
            if self.symbols[i] != " "]
        return f"<Region {'|'.join(regions)}>"


# TODO: Peripherals string-based flags


class Header:
    # https://github.com/KallistiOS/KallistiOS/blob/master/utils/makeip/src/field.c#L36
    device: str  # GD-ROM1/1 etc.
    region: Region
    peripherals: str  # TODO: use Peripherals class
    product_number: str
    version: str
    release_date: str  # TODO: Date class
    boot_file: str
    developer: str
    game: str

    def __repr__(self) -> str:
        descriptor = f"{self.product_number} {self.game!r} {self.version}"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    @classmethod
    def from_bytes(cls, raw_header: bytes) -> Header:
        return cls.from_stream(io.BytesIO(raw_header))

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> Header:
        out = cls()
        assert stream.read(16) == b"SEGA SEGAKATANA "  # Hardware ID
        assert stream.read(16) == b"SEGA ENTERPRISES"  # Maker ID
        out.device = stream.read(16).decode().rstrip(" ")
        area_symbols = stream.read(8).decode()
        assert area_symbols[3:] == " " * 5, area_symbols
        out.region = Region(area_symbols[:3])  # :3
        out.peripherals = stream.read(8).decode().rstrip(" ")  # TODO: class
        out.product_number = stream.read(10).decode().rstrip(" ")
        out.version = stream.read(6).decode().rstrip(" ")  # TODO: class
        out.release_date = stream.read(16).decode().rstrip(" ")  # TODO: class
        out.boot_file = stream.read(16).decode().rstrip(" ")  # "Boot Filename"
        out.developer = stream.read(16).decode().rstrip(" ")  # "Software Maker Name"
        out.game = stream.read(16).decode().rstrip(" ")  # "Game Title"
        return out


class GDRom(base.Archive, files.HybridFile):
    """DiscImage wrapper for GD-ROM filesystems"""
    exts = {
        "*.cdi": files.DataType.BINARY,
        "*.chd": files.DataType.BINARY,
        "*.cue": files.DataType.TEXT,
        "*.gdi": files.DataType.TEXT,
        "*.iso": files.DataType.BINARY,
        "*.mds": files.DataType.BINARY}
    # TODO: derive exts dict (w/ types) from disc_classes
    disc_classes = {
        "*.cdi": padus.Cdi,
        "*.chd": mame.Chd,
        "*.cue": golden_hawk.Cue,
        "*.iso": cdrom.Iso,
        "*.gdi": Gdi,
        "*.mds": alcohol.Mds}
    disc: base.DiscImage
    cd_rom: cdrom.Iso  # CD-ROM filesystem @ lba 0
    gd_rom: cdrom.Iso  # GD-ROM filesystem @ lba 45000
    # TODO: filesystems: List[cdrom.Iso]  # sometimes you get 3
    header: Header

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page=None)
        # TODO: defaults equivalent to a blank GD-ROM
        self.disc = None
        self.cd_rom = None
        self.gd_rom = None
        self.header = None

    @parse_first
    def __repr__(self):
        descriptor = " ".join(
            getattr(self.header, attr)
            for attr in ("product_number", "game", "version"))
        return f"<GDRom {descriptor} @ 0x{id(self):016X}>"

    @parse_first
    def listdir(self, search_folder: str) -> List[str]:
        return self.gd_rom.listdir(search_folder)

    @parse_first
    def namelist(self) -> List[str]:
        return self.gd_rom.namelist()

    @parse_first
    def read(self, filename: str) -> bytes:
        return self.gd_rom.read(filename)

    def parse(self):
        if self.disc is None:
            for pattern, disc_class in self.disc_classes.items():
                if fnmatch.fnmatch(self.filename, pattern):
                    break  # use disc_class matching pattern
            else:  # default to Iso
                disc_class = cdrom.Iso
            if self.archive is None:
                self.disc = disc_class.from_stream(self.filepath, self.stream)
            else:
                self.disc = disc_class.from_archive(self.archive, self.filepath)
        if not self.disc.is_parsed:
            self.disc.parse()
        if isinstance(self.disc, padus.Cdi):
            self.parse_cdi()
        else:
            self.parse_disc()
        self.type = self.disc.type

    def parse_cdi(self):
        # if 16 in self.disc:
        #     self.cd_rom = cdrom.Iso.from_disc(self.disc)
        # else:
        #     self.cd_rom = None
        # DEBUG: the 1 .cdi I'm testing doesn't start the GD-ROM area @ 45000
        assert "Session 02 Track 01" in self.disc.friends
        # NOTE: should be 2 sessions (cd_rom & gd_rom)
        data_track = {track.name: track for track in self.disc.tracks}["Session 02 Track 01"]
        assert data_track.mode != base.TrackMode.AUDIO
        # build the GD-ROM
        # TODO: check for a binary track at the start of the cd_rom sectors
        self.gd_rom = cdrom.Iso.from_disc(self.disc)
        self.gd_rom.pvd_sector = data_track.start_lba + 16
        self.disc.sector_seek(data_track.start_lba)  # boot header
        self.header = Header.from_bytes(self.disc.read(0x90))

    def parse_disc(self):
        if 16 in self.disc:
            self.cd_rom = cdrom.Iso.from_disc(self.disc)
        else:
            self.cd_rom = None
        # NOTE: gd_rom filesystem & header might not start at 45000
        # -- should be in "Session 02 Track 01"
        self.gd_rom = cdrom.Iso.from_disc(self.disc)
        self.gd_rom.pvd_sector = 45016
        # NOTE: might also have a header @ lba 0
        self.disc.sector_seek(45000)  # boot header
        self.header = Header.from_bytes(self.disc.read(0x90))

    # TODO: override .save_as to detect disc_class
    # -- could use this to convert .cue to .gdi
    # -- tho you can do that without loading the tracks

    @classmethod
    def from_disc(cls, disc: base.DiscImage):
        out = cls(disc.filename)
        out.disc = disc
        return out
