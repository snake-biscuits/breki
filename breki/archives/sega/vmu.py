# http://mc.pp.se/dc/vms/flashmem.html
from __future__ import annotations
import enum
import io
from typing import Dict, List

from ... import binary
from ... import core
from ... import files
from ...files.parsed import parse_first
from .. import base


class BCDTimestamp:
    """binary coded decimal timestamp"""
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    weekday: int  # 0-6, mon-sun

    def __init__(self):
        self.year, self.month, self.day = 0, 0, 0
        self.hour, self.minute, self.second = 0, 0, 0
        self.weekday = 0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {str(self)} @ 0x{id(self):016X}>"

    def __str__(self) -> str:
        date = f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        time = f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"
        day = [
            "Monday", "Tuesday", "Wednesday",
            "Thursday", "Friday", "Saturday",
            "Sunday"]
        return f"{date} {time} ({day[self.weekday]})"

    @staticmethod
    def decode(x: int) -> int:
        return ((x >> 4) * 10) + (x & 0xF)

    @staticmethod
    def encode(x: int) -> int:
        return ((x // 10) << 4) + (x % 10)

    # TODO:
    # -- as_bytes
    # -- as_datetime
    # -- from_datetime

    @classmethod
    def from_bytes(cls, raw: bytes) -> BCDTimestamp:
        data = [cls.decode(b) for b in raw]
        out = cls()
        century, year = data[0:2]
        out.year = (century * 100) + year
        out.month, out.day = data[2:4]
        out.hour, out.minute, out.second = data[4:7]
        out.weekday = data[7]
        return out

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> BCDTimestamp:
        return cls.from_bytes(stream.read(8))


class CopyMode(enum.Enum):
    ALLOW = 0x00  # copy ok
    MAYBE = 0x80  # ???
    BLOCK = 0xFF  # copy protected


class Directory:
    filetype: Filetype
    copy_protected: bool
    first_block: int
    filename: str
    created: BCDTimestamp
    num_blocks: int  # filesize in blocks
    header_offset: int  # "offset of header (in blocks) from file start"

    def __repr__(self) -> str:
        descriptor = f'"{self.filename}" created: {self.created!s}'
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> Directory:
        out = cls()
        out.filetype = Filetype(binary.read_struct(stream, "B"))
        out.copy_protected = CopyMode(binary.read_struct(stream, "B"))
        out.first_block = binary.read_struct(stream, "H")
        out.filename = stream.read(12).decode("ascii")
        out.created = BCDTimestamp.from_stream(stream)
        out.num_blocks = binary.read_struct(stream, "H")
        out.header_offset = binary.read_struct(stream, "H")
        assert stream.read(4) == b"\x00" * 4
        return out


class Filetype(enum.Enum):
    NONE = 0x00
    DATA = 0x33
    GAME = 0xCC


class Root:
    """VMU Root Block"""
    use_colour: bool
    colour: bytes  # RGBA32

    @classmethod
    def from_stream(cls, stream: io.BytesIO) -> Root:
        out = cls()
        assert stream.read(16) == b"U" * 16, "unformatted VMU"
        colour_flag = binary.read_struct(stream, "B")
        assert colour_flag in (0x00, 0x01), "invalid colour flag"
        out.use_colour = bool(colour_flag)
        out.colour = binary.read_struct(stream, "4s")
        assert stream.read(27) == b"\x00" * 27  # 0x15..2F
        out.format_date = BCDTimestamp.from_stream(stream)
        assert stream.read(8) == b"\x00" * 8  # 0x38..3F
        out.unknown_1 = stream.read(6)  # 3H?
        out.fat_index, out.fat_size = binary.read_struct(stream, "2H")
        assert out.fat_index == 254
        assert out.fat_size == 1
        out.dir_index, out.dir_size = binary.read_struct(stream, "2H")
        assert out.dir_index == 253
        assert out.dir_size == 13
        out.icon_index = binary.read_struct(stream, "H")
        assert 0 <= out.icon_index <= 123
        out.num_user_blocks = binary.read_struct(stream, "H")
        assert out.num_user_blocks == 200
        out.unknown_2 = stream.read(430)
        return out


class VMI(core.Struct):
    checksum: bytes  # resource_name[:4] & b"SEGA"
    description: bytes  # padded w/ spaces
    copyright: bytes
    created: List[int]
    # NOTE: created.weekday 0-6, sun-sat
    version: int  # always 0
    file_number: int  # always 1
    resource_name: bytes  # .VMS filename w/o extension
    filename: bytes
    mode: int
    # bit 0: 0=CopyOk, 1=CopyProtect
    # bit 1: 0=Data, 1=Game
    padding: int  # always 0
    filesize: int
    __slots__ = [
        "checksum", "description", "copyright",
        "created", "version", "file_number",
        "resource_name", "filename", "mode",
        "padding", "filesize"]
    _format = "4s32s32sH6B2H8s12s2HI"
    _arrays = {
        "created": [
            "year", "month", "day",
            "hour", "minute", "second",
            "weekday"]}

    @property
    def created_str(self) -> str:
        year = self.created.year
        month = self.created.month
        day = self.created.day
        date = f"{year:04d}-{month:02d}-{day:02d}"
        hour = self.created.hour
        minute = self.created.minute
        second = self.created.second
        time = f"{hour:02d}:{minute:02d}:{second:02d}"
        weekdays = [
            "Sunday", "Monday", "Tuesday",
            "Wednesday", "Thursday", "Friday",
            "Saturday"]
        return f"{date} {time} ({weekdays[self.created.weekday]})"

    def __repr__(self) -> str:
        # NOTE: encoding could be Shift-JIS
        filename = self.filename.decode("latin_1").strip()
        description = self.description.decode("latin_1").strip()
        descriptor = f'{filename} {description} {self.filesize} bytes'
        return f"<{self.__class__.__name__} {descriptor}>"


class VMU(base.Archive, files.BinaryFile):
    """256 blocks of 512 bytes (128KB)"""
    exts = ["*.bin"]  # not "*.vmu"?
    directories: Dict[int, Directory]
    fat: List[int]  # File Allocation Table
    # 0xFFFC unallocated
    # 0xFFFA last block
    # 0x0000..00FF next block in file
    root: Root

    def __init__(self, filepath: str, archive=None, **kwargs):
        super().__init__(filepath, archive, **kwargs)
        self.directories = dict()
        self.fat = [0xFFFC] * 256
        self.root = None

    @parse_first
    def __repr__(self) -> str:
        descriptor = f"{self.pvd.name!r} {len(self.namelist())} files"
        return f"<VMU {descriptor} @ 0x{id(self):016X}>"

    @property
    def directories_by_name(self) -> Dict[str, Directory]:
        return {
            directory.filename: directory
            for i, directory in self.directories.items()}

    @parse_first
    def namelist(self) -> List[str]:
        return sorted(self.directories_by_name.keys())

    def parse(self):
        self.is_parsed = True
        self.stream.seek(255 * 512)  # last block
        self.root = Root.from_stream(self.stream)
        self.stream.seek(254 * 512)
        self.fat = binary.read_struct(self.stream, "256H")
        # directories
        dir_stream = io.BytesIO(self.read_from_block(253, 13))
        for i in range(200):
            directory = Directory.from_stream(dir_stream)
            if directory.filetype == Filetype.NONE:
                continue
            self.directories[i] = directory

    @parse_first
    def read_from_block(self, block_index: int, num_blocks: int) -> bytes:
        out = list()
        while 0x00 <= block_index <= 0xFF:
            self.stream.seek(block_index * 512)
            out.append(self.stream.read(512))
            block_index = self.fat[block_index]
        if block_index == 0xFFFA:  # last block of file
            assert len(out) == num_blocks, f"unexpected length: {num_blocks}"
            return b"".join(out)
        elif block_index == 0xFFFC:
            raise RuntimeError(f"unallocated block: {block_index}")
        else:
            raise RuntimeError(f"invalid index: {block_index}")

    @parse_first
    def read(self, filename: str) -> bytes:
        directory = self.directories_by_name[filename]
        start, length = directory.first_block, directory.num_blocks
        data = self.read_from_block(start, length)
        return data
