from __future__ import annotations
import enum
import functools
import io
import os
from typing import List, Union


TextStream = Union[io.StringIO, io.TextIOWrapper]
ByteStream = Union[io.BytesIO, io.BufferedReader]
DataStream = Union[TextStream, ByteStream]


class CodePage:
    encoding: str
    errors: str

    def __init__(self, encoding="utf-8", errors="strict"):
        self.encoding = encoding
        self.errors = errors

    def __repr__(self) -> str:
        args = ", ".join([
            f'"{getattr(self, attr)}"'
            for attr in ("encoding", "errors")])
        return f'{self.__class__.__name__}({args})'

    def __eq__(self, other: CodePage):
        return self.__hash__() == other.__hash__()

    def __hash__(self):
        return hash((self.encoding, self.errors))

    def decode(self, raw_bytes: bytes) -> str:
        return raw_bytes.decode(self.encoding, self.errors)

    def encode(self, text: str) -> bytes:
        return text.encode(self.encoding, self.errors)


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
    code_page = CodePage("utf-8", "strict")
    stream: DataStream  # cached_property

    def __init__(self, filepath: str, archive=None, code_page=None):
        self.archive = archive
        folder, filename = os.path.split(filepath)
        self.folder = folder if folder != "" else "."
        self.filename = filename
        self.code_page = self.code_page if code_page is None else code_page

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
        filepath = os.path.join(self.folder, self.filename)
        if self.archive is None:
            mode = "rb" if type_ != DataType.TEXT else "r"
            out = open(filepath, mode)
        else:
            if not self.archive.is_parsed:
                self.archive.parse()
            raw_bytes = self.archive.read(filepath)
            if type_ == DataType.TEXT:
                raw_text = self.code_page.decode(raw_bytes)
                out = io.StringIO(raw_text)
            else:
                out = io.BytesIO(raw_bytes)
        self.type = type_  # side effect!
        return out

    stream = functools.cached_property(_get_stream)

    @functools.cached_property
    def filepath(self) -> str:
        return os.path.join(self.folder, self.filename)

    @functools.cached_property
    def size(self) -> int:
        if self.archive is None:
            size = os.path.getsize(self.filepath)
        else:
            size = self.archive.sizeof(self.filepath)
        return size

    # initialisers
    # NOTE: all initialisers must provide a filepath
    @classmethod
    def from_archive(cls, archive, filepath: str, type_=None, code_page=None) -> File:
        """defers read until .stream is accessed"""
        type_ = cls.type if type_ is None else type_
        assert isinstance(type_, DataType)
        out = cls(filepath, archive, code_page)
        out.type = type_
        return out

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes, type_=None, code_page=None) -> File:
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
        out = cls.from_stream(filepath, stream, code_page)
        out.size = len(raw_bytes)
        out.type = type_
        return out

    @classmethod
    def from_file(cls, filepath: str, type_=None, code_page=None) -> File:
        """defers read until .stream is accessed"""
        type_ = cls.type if type_ is None else type_
        assert isinstance(type_, DataType)
        out = cls(filepath)
        out.size = os.path.getsize(filepath)
        out.type = type_
        # NOTE: data loading is deferred to .stream property
        out.code_page = cls.code_page if code_page is None else code_page
        return out

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str], code_page=None) -> File:
        """-> .from_stream"""
        raw_text = "\n".join(lines)
        out = cls.from_stream(filepath, io.StringIO(raw_text))
        out.type = DataType.TEXT
        out.code_page = cls.code_page if code_page is None else code_page
        return out

    @classmethod
    def from_stream(cls, filepath: str, stream: DataStream, type_=None, code_page=None) -> File:
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
        out.code_page = cls.code_page if code_page is None else code_page
        return out
