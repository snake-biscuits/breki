from __future__ import annotations
import enum
import fnmatch
import functools
import io
import os
from typing import Dict, List, Union


TextStream = Union[io.StringIO, io.TextIOWrapper]
ByteStream = Union[io.BytesIO, io.BufferedReader]
DataStream = Union[TextStream, ByteStream]


class DataType(enum.Enum):
    TEXT = 0
    BINARY = 1
    EITHER = 2  # for HybridFile
# NOTE: EITHER data will be loaded as BINARY

# NOTE: ETYMOLOGY: the term "filepath" is used for "folder/filename"
# -- "filename" is reserved for basenames (filename w/o folder)


class File:
    """basic wrapper for reading file data + basic metadata"""
    # metadata
    folder: str
    filename: str
    size: int  # filesize in bytes
    type: DataType = DataType.EITHER
    # data access
    archive: object  # ArchiveClass
    stream: DataStream  # cached_property

    def __init__(self, filepath: str, archive=None):
        self.archive = archive
        folder, filename = os.path.split(filepath)
        self.folder = folder if folder != "" else "."
        self.filename = filename
        self.size = 0

    def __repr__(self) -> str:
        descriptor = [f'"{self.filename}"']
        if self.type != DataType.EITHER:
            descriptor.append(f"[{self.type.name}]")
        if self.archive is not None:
            archive_repr = " ".join([
                self.archive.__class__.__name__,
                f'"{self.archive.filename}"'])
            descriptor.append(f"in {archive_repr}")
        descriptor = " ".join(descriptor)
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    # .stream property getter
    def _get_stream(self, type_: DataType = None) -> DataStream:
        """deferring opening the file until it's touched"""
        type_ = self.type if type_ is None else type_
        assert isinstance(type_, DataType)
        if self.archive is None:
            mode = "rb" if type_ != DataType.TEXT else "r"
            out = open(self.filename, mode)
        else:
            raw_bytes = self.archive.read(self.filename)
            if type_ == DataType.TEXT:
                # TODO: expose charset & error mode settings
                raw_text = raw_bytes.decode("utf-8", "strict")
                out = io.StringIO(raw_text)
            else:
                out = io.BytesIO(raw_bytes)
        self.type = type_  # side effect!
        return out

    stream = functools.cached_property(_get_stream)

    # initialisers
    # NOTE: all initialisers must provide a filepath
    @classmethod
    def from_archive(cls, filepath: str, archive, type_=None) -> File:
        """defers read until .stream is accessed"""
        type_ = cls.type if type_ is None else type_
        assert isinstance(type_, DataType)
        out = cls(filepath, archive)
        out.size = archive.sizeof(filepath)
        out.type = type_
        return out

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes, type_=None) -> File:
        """-> .from_stream"""
        type_ = cls.type if type_ is None else type_
        assert isinstance(type_, DataType)
        if type_ == DataType.TEXT:
            # TODO: expose charset & error mode settings
            raw_text = raw_bytes.decode("utf-8", "strict")
            stream = io.StringIO(raw_text)
        else:  # default to BINARY
            stream = io.BytesIO(raw_bytes)
            type_ = DataType.BINARY
        out = cls.from_stream(filepath, stream)
        out.size = len(raw_bytes)
        out.type = type_
        return out

    @classmethod
    def from_file(cls, filepath: str, type_: DataType = None) -> File:
        """defers read until .stream is accessed"""
        type_ = cls.type if type_ is None else type_
        assert isinstance(type_, DataType)
        out = cls(filepath)
        out.size = os.path.getsize(filepath)
        out.type = type_
        # NOTE: data loading is deferred to .stream property
        return out

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str]) -> File:
        """-> .from_stream"""
        raw_text = "\n".join(lines)
        out = cls.from_stream(filepath, io.StringIO(raw_text))
        out.type = DataType.TEXT
        return out

    @classmethod
    def from_stream(cls, filepath: str, stream: DataStream, type_: DataType = None) -> File:
        """override .stream property"""
        type_ = cls.type if type_ is None else type_
        assert isinstance(type_, DataType)
        is_binary = isinstance(stream, (io.BytesIO, io.BufferedReader))
        is_text = isinstance(stream, (io.StringIO, io.TextIOWrapper))
        if not (is_binary or is_text):
            raise RuntimeError(
                f"Could not determine DataType of stream: {stream!r}")
        out = cls(filepath)
        out.stream = stream
        # NOTE: always reports bytesize, regardless of stream type
        out.size = out.stream.seek(0, 2)
        out.stream.seek(0)
        # type check
        if type_ == DataType.BINARY:
            assert is_binary
        elif type_ == DataType.TEXT:
            assert is_text
        elif type_ in (None, DataType.EITHER):  # assign type
            out.type = DataType.BINARY if is_binary else DataType.TEXT
        else:
            raise RuntimeError("Invalid type_: {type_!r}")
        return out


class FriendlyFile(File):
    friend_patterns: Dict[str, DataType]
    friends: Dict[str, File]

    def __init__(self, filepath: str, archive=None):
        super().__init__(filepath, archive)
        self.friends = dict()

    def make_friends(self, candidates: Dict[str, str], archive=None):
        """post-initialisation friend collection"""
        archive = self.archive if archive is None else archive
        # NOTE: friends can come from other archives
        friends = {
            filename: (filepath, type_)
            for filename, filepath in candidates.items()
            for pattern, type_ in self.friend_patterns.items()
            if fnmatch.fnmatch(filename, pattern)}
        for filename, (filepath, type_) in friends.items():
            if archive is not None:
                friend = File.from_archive(filepath, archive, type_)
            else:
                friend = File.from_file(filepath, type_)
            self.friends[filename] = friend

    @functools.cached_property
    def friend_patterns(self) -> Dict[str, DataType]:
        """glob patterns for files we can befriend"""
        # NOTE: you can derive patterns from self.filename w/ a cached_property
        raise NotImplementedError()

    # intialisers
    # NOTE: by default, friends must be in the same folder as the main file
    # -- and in the same archive as the main file, if applicable
    @classmethod
    def from_archive(cls, filepath: str, archive, type_=None) -> File:
        out = super().from_archive(filepath, archive, type_)
        candidates = {
            filename: os.path.join(out.folder, filename)
            for filename in archive.listdir(out.folder)}
        out.make_friends(candidates, archive)
        return out

    @classmethod
    def from_file(cls, filepath: str, type_=None) -> File:
        out = super().from_file(filepath, type_)
        candidates = {
            filename: os.path.join(out.folder, filename)
            for filename in os.listdir(out.folder)}
        out.make_friends(candidates)
        return out
