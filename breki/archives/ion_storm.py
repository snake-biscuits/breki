"""based on Anachronox DAT File Extractor Version 2 by John Rittenhouse"""
# https://archive.thedatadungeon.com/anachronox_2001/community/datextract2.zip
from __future__ import annotations
from typing import Dict, List
import zlib

from .. import core
from .. import binary
from .. import files
from ..files.parsed import parse_first
from . import base
from . import id_software


class DatHeader(core.Struct):
    magic: bytes  # always b"ADAT"
    fileinfo_offset: int  # offset to fileinfo list
    fileinfo_length: int  # length (in bytes) of fileinfo list
    unknown: int  # always 9? version number?
    __slots__ = ["magic", "fileinfo_offset", "fileinfo_length", "unknown"]
    _format = "4s3I"


class DatFileInfo(core.Struct):
    filename: bytes
    offset: int
    length: int  # length of uncompressed data
    compressed_length: int  # uncompressed if 0
    unknown: int  # checksum?
    __slots__ = ["filename", "offset", "length", "compressed_length", "unknown"]
    _format = "128s4I"


class Dat(base.Archive, files.BinaryFile):
    """Used by Anachronox"""
    exts = ["*.dat"]
    header: DatHeader
    entries: Dict[str, DatFileInfo]

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
        entry = self.entries[filepath]
        self.stream.seek(entry.offset)
        if entry.compressed_length == 0:
            data = self.stream.read(entry.length)
        else:
            data = zlib.decompress(self.stream.read(entry.compressed_length))
            assert len(data) == entry.length
        return data

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        self.header = DatHeader.from_stream(self.stream)
        assert self.header.magic == b"ADAT", "not a dat file"
        assert self.header.unknown == 9
        assert self.header.fileinfo_length % 144 == 0, "invalid fileinfo_size"
        self.stream.seek(self.header.fileinfo_offset)
        for i in range(self.header.fileinfo_length // 144):
            file_info = DatFileInfo.from_stream(self.stream)
            filename = file_info.filename.partition(b"\0")[0].decode()
            self.entries[filename] = file_info


class PakFileEntry(core.Struct):
    filename: bytes  # can contain multiple filenames
    # for maps, looks to be attached scripts
    # use filename.strip(b"\0").split(b"\0") to get the list
    offset: int
    length: int
    compressed_length: int
    is_compressed: int
    __slots__ = [
        "filename", "offset", "length",
        "compressed_length", "is_compressed"]
    _format = "56s4I"
    _classes = {"is_compressed": bool}


class Pak(id_software.Pak):
    # https://github.com/yquake2/pakextract
    exts = ["*.pak"]
    code_page = files.CodePage("ascii", "strict")
    entries: Dict[str, PakFileEntry]

    @parse_first
    def decompress(self, entry: PakFileEntry) -> bytes:
        """average time to decompress is ~1min per MB"""
        # https://github.com/yquake2/pakextract/blob/master/pakextract.c#L254
        out = b""
        self.stream.seek(entry.offset)
        while self.stream.tell() < entry.offset + entry.compressed_length:
            x = int.from_bytes(self._file.read(1))
            if x < 64:
                out += self.stream.read(x + 1)
            elif x < 128:
                out += b"\x00" * (x - 62)
            elif x < 192:
                out += self.stream.read(1) * (x - 126)
            elif x < 255:
                ptr = int.from_bytes(self.stream.read(1)) + 1
                out += out[-ptr].to_bytes(1) * (x - 190)
            else:  # x == 255
                break  # terminator
        else:
            raise RuntimeError("no terminator at end of compressed data")
        assert len(out) == entry.length
        return out

    @parse_first
    def read(self, filepath: str) -> bytes:
        if filepath not in self.entries:
            raise FileNotFoundError(f"{filepath!r} is not in this Pak")
        entry = self.entries[filepath]
        self.stream.seek(entry.offset)
        if not entry.is_compressed:
            return self.stream.read(entry.length)
        else:
            return self.decompress(entry)

    @parse_first
    def namelist(self) -> List[str]:
        return sorted(self.entries.keys())

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        assert self.stream.read(4) == b"PACK", "not a .pak file"
        # file table
        offset, length = binary.read_struct(self.stream, "2I")
        sizeof_entry = len(PakFileEntry().as_bytes())
        assert length % sizeof_entry == 0, "unexpected file table size"
        self.stream.seek(offset)
        self.entries = {
            self.code_page.decode(entry.filename.partition(b"\0")[0]): entry
            for entry in [
                PakFileEntry.from_stream(self.stream)
                for i in range(length // sizeof_entry)]}
