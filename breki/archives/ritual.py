from typing import Dict, List

from .. import core
from .. import binary
from .. import files
from ..files.parsed import parse_first
from . import base


class SPakEntry(core.Struct):
    filepath: bytes
    offset: int
    length: int
    __slots__ = ["filepath", "offset", "length"]
    _format = "120s2I"


class Sin(base.Archive, files.BinaryFile):
    exts = ["*.sin"]
    code_page = files.CodePage("ascii", "strict")
    entries: Dict[str, SPakEntry]

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.entries = dict()

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
        if self.is_parsed:
            return
        self.is_parsed = True
        assert self.stream.read(4) == b"SPAK", "not a .pak file"
        # file table
        offset, length = binary.read_struct(self.stream, "2I")
        sizeof_entry = 0x80
        assert length % sizeof_entry == 0, "unexpected file table size"
        self.stream.seek(offset)
        self.entries = {
            self.code_page.decode(entry.filepath.partition(b"\0")[0]): entry
            for entry in [
                SPakEntry.from_stream(self.stream)
                for i in range(length // sizeof_entry)]}
