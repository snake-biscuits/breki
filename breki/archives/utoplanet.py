from __future__ import annotations
import io
from typing import Dict, List

from .. import binary
from .. import core
from .. import files
from ..files.parsed import parse_first
from . import base


class Apk(base.Archive, files.BinaryFile):
    exts = ["*.apk"]
    header: ApkHeader
    entries: Dict[str, ApkEntry]

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.entries = dict()

    @parse_first
    def __repr__(self) -> str:
        descriptor = f'"{self.filename}" {len(self.entries)} files'
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    @parse_first
    def namelist(self) -> List[str]:
        return sorted(self.entries.keys())

    @parse_first
    def read(self, filepath: str) -> bytes:
        if filepath not in self.namelist():
            raise FileNotFoundError()
        entry = self.entries[filepath]
        self.stream.seek(entry.offset)
        return self.stream.read(entry.length)

    def parse(self):
        self.header = ApkHeader.from_stream(self.stream)
        assert self.header.magic == b"\x57\x23\x00\x00", "not a valid .apk file"
        self.stream.seek(self.header.dir_offset)
        for i in range(self.header.num_files):
            entry = ApkEntry.from_stream(self.stream, self.code_page)
            self.entries[entry.filename] = entry
            self.stream.seek(entry.next_entry_offset)


class ApkEntry:
    filename: str
    offset: int
    length: int
    next_entry_offset: int
    unknown: int  # checksum?
    code_page = files.CodePage("utf-8", "strict")

    def __repr__(self) -> str:
        descriptor = f'"{self.filename}" 0x{self.offset:08X}'
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    @classmethod
    def from_stream(cls, stream: io.BytesIO, code_page=None) -> ApkEntry:
        code_page = cls.code_page if code_page is None else code_page
        out = cls()
        filename_length = binary.read_struct(stream, "I")
        filename = stream.read(filename_length + 1).decode(*code_page)
        assert len(filename) == filename_length + 1, "filename ends prematurely"
        assert filename[-1] == "\0", "filename is not zero terminated"
        out.filename = filename[:-1].replace("\\", "/")
        out.offset, out.length, out.next_entry_offset, out.unknown = binary.read_struct(stream, "4I")
        return out


class ApkHeader(core.Struct):
    magic: bytes
    files_offset: int
    num_files: int
    dir_offset: int
    __slots__ = ["magic", "files_offset", "num_files", "dir_offset"]
    _format = "4s3I"
