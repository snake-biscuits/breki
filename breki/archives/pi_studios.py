"""Pi Studios Quake Arena Arcade .bpk format"""
from __future__ import annotations
import io
import struct
from typing import List

from .. import binary
from .. import core
from .. import files
from ..files.parsed import parse_first
from . import base


class Bpk(base.Archive, files.BinaryFile):
    exts = ["*.bpk"]
    headers: List[CentralHeader]
    files: List[(LocalHeader, bytes)]

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.headers = list()
        self.files = list()

    @parse_first
    def __repr__(self) -> str:
        descriptor = f'"{self.filename}" {len(self.headers)} files'
        return f"<{self.__class__.__name__} {descriptor} @ {id(self):016X}>"

    @parse_first
    def namelist(self) -> List[str]:
        # TODO: get filenames somehow
        # -- reverse hashes in CentralHeader?
        raise NotImplementedError()

    @parse_first
    def read(self, filename: str) -> bytes:
        raise NotImplementedError()

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        one, num_headers = binary.read_struct(self.stream, ">2I")
        self.headers = [
            CentralHeader.from_stream(self.stream)
            for i in range(num_headers)]
        assert all(header.one == 1 for header in self.headers)
        for header in self.headers:
            assert header.size >= 0x48
            self.stream.seek(header.offset)
            local_header = LocalHeader.from_stream(self.stream)
            data = self.stream.read(header.size - 0x48)[1:-5]
            # NOTE: trimmed bytes are always 0
            self.files.append((local_header, data))


class CentralHeader(core.Struct):
    key: int  # filename hash?
    offset: int
    data_size: int  # matches text length if uncompressed plaintext
    one: int  # always 1
    size: int
    __slots__ = ["key", "offset", "data_size", "one", "size"]
    _format = ">Q4I"

    def __repr__(self) -> str:
        attrs = ", ".join([
            f"key=0x{self.key:016X}",
            f"offset=0x{self.offset:08X}",
            f"data_size=0x{self.data_size:06X}",
            f"one={self.one}",
            f"size=0x{self.size:06X}"])
        return f"EntryHeader({attrs})"


class LocalHeader:
    uncompressed_size: int
    unknown: List[int]
    # 0, 1 & 2 usually all match
    # 3 always FF ?? ?? ??

    def __init__(self, uncompressed_size, *unknown):
        self.uncompressed_size = uncompressed_size
        self.unknown = unknown

    def __repr__(self) -> str:
        plain_args = ", ".join(map(str, [self.uncompressed_size, *self.unknown[:3]]))
        hex_args = ", ".join(f"0x{a:08X}" for a in self.unknown[3:])
        return f"LocalHeader({plain_args}, {hex_args})"

    def as_bytes(self) -> bytes:
        return b"".join([
            b"\x0F\xF5\x12\xEE\x01\x03\x00\x00",
            struct.pack(">5I", 0, 0, 0x8000, 0x8000, 0),
            struct.pack(">I", self.uncompressed_size),
            struct.pack(">I", 0),
            struct.pack(">I", self.unknown[0]),
            struct.pack(">I", 0x8000),
            struct.pack(">7I", *self.unknown[1:])])

    @classmethod
    def from_bytes(cls, raw: bytes) -> LocalHeader:
        assert len(raw) == 0x48
        return cls.from_stream(io.BytesIO(raw))

    @classmethod
    def from_stream(cls, stream) -> LocalHeader:
        assert stream.read(8) == b"\x0F\xF5\x12\xEE\x01\x03\x00\x00"
        assert binary.read_struct(stream, ">5I") == (0, 0, 0x8000, 0x8000, 0)
        uncompressed_size = binary.read_struct(stream, ">I")
        assert binary.read_struct(stream, ">I") == 0
        unknown_1 = binary.read_struct(stream, ">I")
        assert binary.read_struct(stream, ">I") == 0x8000
        unknown_2 = binary.read_struct(stream, ">7I")
        return cls(uncompressed_size, unknown_1, *unknown_2)
