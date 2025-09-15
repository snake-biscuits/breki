from __future__ import annotations
from typing import Dict, List

from .. import core
from .. import binary
from .. import files
from ..files.parsed import parse_first
from . import base
from . import pkware


class PakFileEntry(core.Struct):
    filename: bytes  # plaintext
    offset: int
    length: int
    __slots__ = ["filename", "offset", "length"]
    _format = "56s2I"


class Pak(base.Archive, files.BinaryFile):
    # https://quakewiki.org/wiki/.pak
    exts = ["*.pak"]
    entries: Dict[str, PakFileEntry]
    code_page = files.CodePage("ascii", "strict")

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.entries = dict()

    @parse_first
    def __repr__(self) -> str:
        descriptor = f'"{self.filename}" {len(self.entries)} files'
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    @parse_first
    def read(self, filepath: str) -> bytes:
        assert filepath in self.entries
        entry = self.entries[filepath]
        self.stream.seek(entry.offset)
        return self.stream.read(entry.length)

    @parse_first
    def namelist(self) -> List[str]:
        return sorted(self.entries.keys())

    def parse(self):
        assert self.stream.read(4) == b"PACK", "not a .pak file"
        # file table
        offset, length = binary.read_struct(self.stream, "2I")
        sizeof_entry = 64
        assert length % sizeof_entry == 0, "unexpected file table size"
        self.stream.seek(offset)
        self.entries = {
            self.code_page.decode(entry.filename.partition(b"\0")[0]): entry
            for entry in [
                PakFileEntry.from_stream(self.stream)
                for i in range(length // sizeof_entry)]}


class Pk3(pkware.Zip):
    exts = ["*.pk3"]
