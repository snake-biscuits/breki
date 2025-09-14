# https://github.com/ValvePython/vpk
from __future__ import annotations
from typing import Dict, List, Union

from .. import binary
from .. import core
from .. import files
from ..files.parsed import parse_first
from . import base


class VpkHeader(core.Struct):
    magic: int  # should always be 0x55AA1234
    version: List[int]  # should always be (1, 0)
    tree_length: int
    __slots__ = ["magic", "version", "tree_length"]
    _format = "I2HI"
    _arrays = {"version": ["major", "minor"]}


class VpkHeaderv2(core.Struct):
    # attributed to http://forum.xentax.com/viewtopic.php?f=10&t=11208
    magic: int  # should always be 0x55AA1234
    version: List[int]  # should always be (1, 0)
    tree_length: int
    # new in v2.0
    embed_chunk_length: int
    chunk_hashes_length: int
    self_hashes_length: int  # always 48
    signature_length: int
    __slots__ = [
        "magic", "version", "tree_length",
        "embed_chunk_length", "chunk_hashes_length",
        "self_hashes_length", "signature_length"]
    _format = "I2H5I"
    _arrays = {"version": ["major", "minor"]}
    # NOTE: v2 has embed_chunk & chunk hashes after tree
    # -- followed by MD5 char[16] checksums for tree, chunk_hashes & file


class VpkEntry(core.Struct):
    crc: int  # CRC32 hash
    preload_length: int  # length of preload data
    archive_index: int
    archive_offset: int  # if archive_index == 0x7FFF: + end of tree
    file_length: int
    __slots__ = [
        "crc", "preload_length", "archive_index",
        "archive_offset", "file_length"]
    _format = "I2H2I"


class Vpk(base.Archive, files.FriendlyBinaryFile):
    exts = ["*.vpk", "*_dir.vpk"]
    header: Union[VpkHeader, VpkHeaderv2]
    entries: Dict[str, VpkEntry]
    friends: Dict[str, files.File]
    preload_offset: Dict[str, int]
    versions = {
        (1, 0): VpkHeader,
        (2, 0): VpkHeaderv2}

    def __init__(self, filepath: str, archive=None):
        super().__init__(filepath, archive)  # archive, folder, filename
        self.entries = dict()
        self.extras = dict()
        self.preload_offset = dict()

    @parse_first
    def __repr__(self) -> str:
        descriptor = f'"{self.filename}" {len(self.entries)} files'
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    @property
    def friend_patterns(self) -> Dict[str, files.DataType]:
        if self.filename.endswith("_dir.vpk"):
            return {
                f"{self.filename[:-8]}_{index:03d}.vpk": files.DataType.BINARY
                for index in {
                    entry.archive_index
                    for entry in self.entries.values()
                    if entry.archive_index != 0x7FFF}}
        return dict()

    @parse_first
    def namelist(self) -> List[str]:
        return sorted(self.entries)

    @parse_first
    def read(self, filename: str) -> bytes:
        assert filename in self.namelist()
        entry = self.entries[filename]
        if entry.archive_index != 0x7FFF:
            assert self.filename.endswith("_dir.vpk")
            stream = self.archive_vpk(entry.archive_index)
        else:
            stream = self.stream
        stream.seek(entry.archive_offset)
        data = stream.read(entry.file_length)
        assert len(data) == entry.file_length, "unexpected EOF"
        return data

    def archive_vpk(self, index: int) -> files.File:
        assert self.filename.endswith("_dir.vpk"), "not a _dir.vpk"
        return self.friends[f"{self.filename[:-8]}_{index:03d}.vpk"]

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        # verify magic
        magic = binary.read_struct(self.stream, "I")
        assert magic == 0x55AA1234
        # get structs for this version
        version = binary.read_struct(self.stream, "2H")
        if version not in self.versions:
            version_str = ".".join(map(str, version))
            raise NotImplementedError(f"Vpk v{version_str} is not supported")
        # header
        self.stream.seek(0)
        HeaderClass = self.versions[version]
        self.header = HeaderClass.from_stream(self.stream)
        end_of_tree = len(self.header.as_bytes()) + self.header.tree_length
        # tree
        assert self.header.tree_length != 0, "no files?"
        while True:
            extension = binary.read_str(self.stream, encoding="latin_1")
            if extension == "":
                break  # end of tree
            while True:
                folder = binary.read_str(self.stream, encoding="latin_1")
                if folder == "":
                    break  # end of extension
                while True:
                    filename = binary.read_str(self.stream, encoding="latin_1")
                    if filename == "":
                        break  # end of folder
                    # entry
                    if folder != " ":  # not in root folder
                        entry_path = f"{folder}/{filename}.{extension}"
                    else:
                        entry_path = f"{filename}.{extension}"
                    entry = VpkEntry.from_stream(self.stream)
                    assert binary.read_struct(self.stream, "H") == 0xFFFF
                    if entry.archive_index == 0x7FFF:
                        entry.archive_offset += end_of_tree
                    self.entries[entry_path] = entry
                    self.preload_offset[entry_path] = self.stream.tell()
                    self.stream.seek(entry.preload_length, 1)
        assert self.stream.tell() == end_of_tree, "overshot tree"
