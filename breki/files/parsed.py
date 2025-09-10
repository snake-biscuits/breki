from __future__ import annotations
import functools
import io
from typing import Dict, List

from . import base


class ParsedFile(base.File):
    exts: List[str] = list()  # class-level definition
    # NOTE: we don't check filepaths for extension

    def as_bytes(self) -> bytes:
        """unparser"""
        return b"\n".join(map(
            lambda line: line.encode("utf-8", "strict"),
            self.as_lines()))

    def as_lines(self) -> List[str]:
        """unparser"""
        raise NotImplementedError()

    def parse(self):
        """deferred post-init stage"""
        raise NotImplementedError()

    # intialisers
    # NOTE: wrapped to force cls.type
    @classmethod
    def from_archive(cls, filepath: str, archive, parse: bool = False) -> ParsedFile:
        """defers read until .stream is accessed"""
        out = super().from_archive(filepath, archive, cls.type)
        if parse:
            out.parse()
        return out

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes) -> ParsedFile:
        """-> .from_stream + immediate parse"""
        out = super().from_bytes(filepath, raw_bytes, cls.type)
        out.parse()
        return out

    @classmethod
    def from_file(cls, filepath: str, parse: bool = False) -> ParsedFile:
        """defers read until .stream is accessed"""
        out = super().from_file(filepath, cls.type)
        if parse:
            out.parse()
        return out

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str]) -> ParsedFile:
        """-> .from_stream + immediate parse"""
        out = super().from_lines(filepath, lines)
        out.parse()
        return out

    @classmethod
    def from_stream(cls, filepath: str, stream: base.DataStream) -> ParsedFile:
        """override .stream property + immediate parse"""
        out = super().from_stream(filepath, stream, cls.type)
        out.parse()
        return out


class BinaryFile(ParsedFile):
    type = base.DataType.BINARY

    def as_bytes(self) -> bytes:
        """unparser"""
        raise NotImplementedError()

    # initialisers
    @classmethod
    def from_lines(cls, filepath: str, lines: List[str]) -> None:
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
            ext = f".{self.rpartition('.')[-1]}"
            self.type = self.exts.get(ext, base.DataType.EITHER)
        descriptor.append(f"[{self.type.name}]")
        if self.archive is not None:
            descriptor.append(f"in {self.archive!r}")
        descriptor = " ".join(descriptor)
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    def as_bytes(self) -> List[str]:
        """binary unparser"""
        raise NotImplementedError()

    def as_lines(self) -> List[str]:
        """text unparser"""
        raise NotImplementedError()

    # NOTE: for .stream & .parse if type == EITHER
    @staticmethod
    def identify(filepath: str, stream: base.ByteStream) -> base.DataType:
        """determine type if ambiguous"""
        # test filepath against extensions
        raise NotImplementedError()

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

    @functools.cached_property
    def stream(self) -> base.DataStream:
        """deferring opening the file until it's touched"""
        out = super().stream
        if self.type == base.DataType.EITHER:
            type_ = self.identify(self.filename, out)
            out = super()._get_stream(type_)
            self.type = type_
        return out

    def parse_binary(self):
        """binary parser"""
        raise NotImplementedError()

    def parse_text(self):
        """text parser"""
        # for line in self.stream: ...
        raise NotImplementedError()

    # initialisers
    @classmethod
    def from_archive(cls, filepath: str, archive, parse: bool = False, type_: base.DataType = None) -> HybridFile:
        """defers read until .stream is accessed"""
        out = super().from_archive(filepath, archive, type_)
        if parse:
            out.parse()
        return out

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes, type_: base.DataType = None) -> HybridFile:
        """-> .from_stream + immediate parse"""
        type_ = cls.type if type_ is None else type_
        if type_ == base.DataType.EITHER:
            type_ = cls.identify(io.BytesIO(raw_bytes))
        out = super().from_bytes(filepath, raw_bytes, type_)
        out.parse(type_)
        return out

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str]) -> HybridFile:
        """-> .from_stream + immediate parse"""
        out = super().from_lines(filepath, lines)
        out.parse()
        return out

    @classmethod
    def from_stream(cls, filepath: str, stream: base.DataStream, type_: base.DataType = None) -> HybridFile:
        """override .stream property + immediate parse"""
        out = super().from_stream(filepath, stream, type_)
        out.parse()
        return out

    @classmethod
    def from_file(cls, filepath: str, parse: bool = False, type_: base.DataType = None) -> HybridFile:
        """defers read until .stream is accessed"""
        out = super().from_file(filepath, type_)
        if parse:
            out.parse()
        return out


class FriendlyHybridFile(HybridFile, base.FriendlyFile):
    pass
