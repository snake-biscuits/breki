# https://github.com/craftablescience/sourcepp/blob/main/src/vpkpp/format/VPK_VTMB.cpp
from __future__ import annotations
import io
import struct
from typing import Dict, List

from .. import binary
from .. import files
from ..files.parsed import parse_first
from . import base


class VpkEntry:
    filename: str
    offset: int
    length: int

    def __repr__(self) -> str:
        return f'<VpkEntry "{self.filename}" ({self.length} bytes)>'

    def as_bytes(self) -> bytes:
        raw_filename = self.filename.encode("latin_1")
        return b"".join([
            struct.pack("I", len(raw_filename)), raw_filename,
            struct.pack("2I", self.offset, self.length)])

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> VpkEntry:
        out = cls()
        filename_length = binary.read_struct(stream, "I")
        out.filename = stream.read(filename_length).decode(encoding="latin_1")
        # NOTE: no trailing \0
        out.offset, out.length = binary.read_struct(stream, "2I")
        return out


class Vpk(base.Archive, files.BinaryFile):
    exts = ["pack*.vpk"]
    entries: Dict[str, VpkEntry]

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.entries = dict()

    @parse_first
    def namelist(self) -> List[str]:
        return sorted(self.entries)

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        self.stream.seek(-9, 2)
        num_entries, dir_offset, version = binary.read_struct(self.stream, "2IB")
        assert version in (0, 1), f"unsupported version: {version}"
        # NOTE: if version == 1 the file is only entries, no data
        # -- version is only 1 for pack010.vpk
        # -- might be a flag, rather than a version, but idk
        self.stream.seek(dir_offset)
        for i in range(num_entries):
            entry = VpkEntry.from_stream(self.stream)
            self.entries[entry.filename] = entry

    @parse_first
    def read(self, filepath: str) -> bytes:
        entry = self.entries[filepath]
        self.stream.seek(entry.offset)
        data = self.stream.read(entry.length)
        assert len(data) == entry.length, "unexpected EOF"
        return data

    @parse_first
    def sizeof(self, filepath: str) -> int:
        return self.entries[filepath].length
