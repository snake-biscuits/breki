# https://dsibrew.org/wiki/DSi_cartridge_header
# https://chibiakumas.com/arm/nds.php
from __future__ import annotations
import os
from typing import List, Tuple

from .. import binary
from .. import core
from .. import files
from ..files.parsed import parse_first
from . import base


class BootVector(core.Struct):
    __slots__ = ["offset", "entry_address", "load_address", "length"]
    _format = "4I"

    def __repr__(self) -> str:
        args = ", ".join([
            f"{slot}=0x{getattr(self, slot):08X}"
            for slot in self.__slots__])
        return f"{self.__class__.__name__}({args})"


class FileNameTable:
    unknown: int
    folder_table: Tuple[int, int, int]  # parallel w/ folders
    # ^ (offset, first_filename, parent block_id)
    # -- offset within FNT to first byte of filenames
    filenames: List[Tuple[int, str]]
    # ^ [(folder index, "filename")]
    folders: List[Tuple[int, str, int]]
    # ^ [(parent index, "FOLDER", block_id)]
    # NOTE: block_id increments by 1 per folder
    # -- in tree order, nested folders appear later

    def __init__(self):
        self.unknown = 0
        self.folder_table = list()
        self.filenames = list()
        self.folders = list()

    @classmethod
    def from_stream(cls, stream, offset, length, code_page) -> FileNameTable:
        stream.seek(offset)
        out = cls()
        names_offset = binary.read_struct(stream, "I")
        out.unknown = binary.read_struct(stream, "I")
        # folder table
        assert (names_offset - 8) % 8 == 0
        num_folders = (names_offset - 8) // 8
        out.folder_table = [
            binary.read_struct(stream, "I2H")
            for i in range(num_folders)]
        assert stream.tell() == offset + names_offset, f"{stream.tell():06X}"
        # filenames & folders
        parent = -1  # top-level
        while stream.tell() < offset + length:
            str_length = binary.read_struct(stream, "B")
            if str_length & 0x80 == 0x80:  # folder
                filename = code_page.decode(stream.read(str_length - 0x80))
                unknown = binary.read_struct(stream, "H")
                out.folders.append((parent, filename, unknown))
            elif str_length == 0:  # end of folder
                parent += 1
            else:  # regular filename
                raw_filename = stream.read(str_length)
                filename = code_page.decode(raw_filename)
                out.filenames.append((parent, filename))
        # collected files for all folders
        assert str_length == 0
        assert parent == len(out.folders)
        # collected all folders
        assert len(out.folder_table) == len(out.folders)
        # parsed all bytes
        assert stream.tell() == offset + length
        return out


# NOTE: doing a really lazy reverse lookup for filepath -> index
class Nds(base.Archive, files.BinaryFile):
    """Nintendo DS Cartdridge Image"""
    exts = ["*.nds"]
    code_page = files.CodePage("shift_jis", "strict")
    # header
    arm_9: BootVector
    arm_7: BootVector
    # file tables
    fnt: FileNameTable
    fat: List[Tuple[int, int]]
    # ^ [(start, end)]
    full_fat: List[Tuple[int, int]]
    # for when the FAT is oversized

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.full_fat = None

    @parse_first
    def namelist(self) -> List[str]:
        out = list()
        for parent, filename in self.fnt.filenames:
            while parent != -1:
                parent, folder, unknown = self.fnt.folders[parent]
                filename = os.path.join(folder, filename)
            out.append(filename)
        return out

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        # TODO: header
        # -- 12s game name
        # -- ...
        self.stream.seek(0x20)
        self.arm_9 = BootVector.from_stream(self.stream)
        self.arm_7 = BootVector.from_stream(self.stream)
        self.fnt_header = binary.read_struct(self.stream, "2I")
        self.fat_header = binary.read_struct(self.stream, "2I")
        # TODO: header

        # File Name Table
        self.fnt = FileNameTable.from_stream(
            self.stream, *self.fnt_header, self.code_page)

        # File Allocation Table
        fat_offset, fat_length = self.fat_header
        self.stream.seek(fat_offset)
        self.fat = [
            binary.read_struct(self.stream, "2I")  # start, end
            for i in range(fat_length // 8)]
        assert self.stream.tell() == fat_offset + fat_length

        # trim FAT if larger than FNT namelist
        if len(self.fat) > len(self.fnt.filenames):
            self.full_fat = self.fat  # backup
            self.fat = self.fat[-(len(self.fnt.filenames)):]

        # TODO: assert all FAT offsets are in bounds
        # -- not overlapping boot roms, fnt or fat
        # -- not going past end of cartridge
        # -- full_fat can go out of bounds

    @parse_first
    def read(self, filepath: str) -> bytes:
        if filepath.startswith("./"):
            filepath = filepath[2:]
        index = self.namelist().index(filepath)
        start, end = self.fat[index]
        self.stream.seek(start)
        out = self.stream.read(end - start)
        assert len(out) == end - start
        return out

    @parse_first
    def sizeof(self, filepath: str) -> int:
        if filepath.startswith("./"):
            filepath = filepath[2:]
        index = self.namelist().index(filepath)
        start, end = self.fat[index]
        return end - start
