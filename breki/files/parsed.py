from __future__ import annotations
import functools
import io
from typing import Dict, List

from . import base


class ParsedFile(base.File):
    exts: List[str] = list()  # class-level definition
    # NOTE: we don't reject filepaths that don't have the right extension
    is_parsed: bool

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.is_parsed = False

    def __getattr__(self, attr: str):
        if not self.is_parsed:
            self.parse()
        return getattr(self, attr)

    def as_bytes(self) -> bytes:
        """unparser"""
        return b"\n".join(map(self.code_page.encode, self.as_lines()))

    def as_lines(self) -> List[str]:
        """unparser"""
        raise NotImplementedError()

    def parse(self):
        """deferred post-init stage"""
        raise NotImplementedError()
        self.is_parsed = True

    # intialisers
    # NOTE: wrapped to force cls.type
    @classmethod
    def from_archive(cls, filepath: str, archive, code_page=None) -> ParsedFile:
        """defers read until .stream is accessed"""
        return super().from_archive(filepath, archive, cls.type, code_page)

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes, code_page=None) -> ParsedFile:
        """-> .from_stream"""
        return super().from_bytes(filepath, raw_bytes, cls.type, code_page)

    @classmethod
    def from_file(cls, filepath: str, code_page=None) -> ParsedFile:
        """defers read until .stream is accessed"""
        return super().from_file(filepath, cls.type, code_page)

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str], code_page=None) -> ParsedFile:
        """-> .from_stream"""
        return super().from_lines(filepath, lines, code_page)

    @classmethod
    def from_stream(cls, filepath: str, stream: base.DataStream, code_page=None) -> ParsedFile:
        """override .stream property"""
        # NOTE: File.from_stream will ensure stream is valid for cls.type
        return super().from_stream(filepath, stream, cls.type, code_page)


class BinaryFile(ParsedFile):
    type = base.DataType.BINARY

    def as_bytes(self) -> bytes:
        """unparser"""
        raise NotImplementedError()

    # initialisers
    @classmethod
    def from_lines(cls, *args, **kwargs) -> None:
        raise RuntimeError("BinaryFile cannot be initialised from_lines")


class FriendlyBinaryFile(BinaryFile, base.FriendlyFile):
    pass


class TextFile(ParsedFile):
    type = base.DataType.TEXT


class FriendlyTextFile(TextFile, base.FriendlyFile):
    pass


class HybridFile(ParsedFile):
    exts: Dict[str, base.DataType] = dict()
    # ^ {".bin": Datatype.BINARY}
    type = base.DataType.EITHER

    def __repr__(self) -> str:
        descriptor = [f'"{self.filename}"']
        if self.type == base.DataType.EITHER:  # match .ext
            ext = f".{self.filename.rpartition('.')[-1]}"
            self.type = self.exts.get(ext, base.DataType.EITHER)
        descriptor.append(f"[{self.type.name}]")
        if self.archive is not None:
            archive_repr = " ".join([
                self.archive.__class__.__name__,
                f'"{self.archive.filename}"'])
            descriptor.append(f"in {archive_repr}")
        descriptor = " ".join(descriptor)
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    def as_bytes(self) -> List[str]:
        """binary unparser"""
        raise NotImplementedError()

    def as_lines(self) -> List[str]:
        """text unparser"""
        raise NotImplementedError()

    # NOTE: for .stream & .parse if type == EITHER
    @classmethod
    def identify(cls, filepath: str, stream: base.ByteStream) -> base.DataType:
        """determine type if ambiguous"""
        # get DataType from extension
        ext = f".{filepath.rpartition('.')[-1]}"
        type_ = cls.exts.get(ext, base.DataType.EITHER)
        return type_
        # NOTE: subclasses should test stream if type_ == EITHER
        # -- brute force solution: (checks every byte)
        # -- stream.seek(0)
        # -- return DataType.TEXT if stream.read().isascii() else DataType.BINARY

    def parse(self, type_: base.DataType = None):
        type_ = self.type if type_ is None else type_
        if type_ == base.DataType.EITHER:
            type_ = self.identify(self.filename, self.stream)
        if type_ == base.DataType.BINARY:
            self.parse_binary()
        elif type_ == base.DataType.TEXT:
            self.parse_text()
        else:
            raise RuntimeError(f"Invalid type: {type!r}")
        self.type = type_
        self.is_parsed = True

    def parse_binary(self):
        """binary parser"""
        raise NotImplementedError()
        self.is_parsed = True

    def parse_text(self):
        """text parser"""
        # for line in self.stream: ...
        raise NotImplementedError()
        self.is_parsed = True

    @functools.cached_property
    def stream(self) -> base.DataStream:
        """deferring opening the file until it's touched"""
        out = super().stream
        if self.type == base.DataType.EITHER:
            type_ = self.identify(self.filename, out)
            out = super()._get_stream(type_)
            self.type = type_
        return out

    # initialisers
    @classmethod
    def from_archive(cls, filepath: str, archive, type_=None, code_page=None) -> HybridFile:
        """defers read until .stream is accessed"""
        return super().from_archive(filepath, archive, type_, code_page)

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes, type_=None, code_page=None) -> HybridFile:
        """-> .from_stream + immediate parse"""
        type_ = cls.type if type_ is None else type_
        if type_ == base.DataType.EITHER:
            type_ = cls.identify(io.BytesIO(raw_bytes))
        out = super().from_bytes(filepath, raw_bytes, type_, code_page)
        out.parse(type_)
        return out

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str], code_page=None) -> HybridFile:
        """-> .from_stream + immediate parse"""
        out = super().from_lines(filepath, lines, code_page)
        out.parse()
        return out

    @classmethod
    def from_stream(cls, filepath: str, stream: base.DataStream, type_=None, code_page=None) -> HybridFile:
        """override .stream property + immediate parse"""
        out = super().from_stream(filepath, stream, type_, code_page)
        out.parse()
        return out

    @classmethod
    def from_file(cls, filepath: str, parse: bool = False, type_=None, code_page=None) -> HybridFile:
        """defers read until .stream is accessed"""
        out = super().from_file(filepath, type_, code_page)
        if parse:
            out.parse()
        return out


class FriendlyHybridFile(HybridFile, base.FriendlyFile):
    pass
