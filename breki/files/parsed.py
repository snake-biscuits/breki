from __future__ import annotations
import io
from typing import Dict, List

from . import base


class BinaryFile(base.File):
    exts: List[str] = list()
    type = base.DataType.BINARY

    def as_bytes(self) -> bytes:
        """unparser"""
        raise NotImplementedError()

    def parse(self):
        """deferred post-init stage"""
        raise NotImplementedError()

    # initialisers
    # NOTE: wrapped to ensure type is always BINARY
    @classmethod
    def from_archive(cls, filepath: str, archive) -> BinaryFile:
        """defers read until .stream is accessed"""
        return super().from_archive(filepath, archive)

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes) -> BinaryFile:
        """-> .from_stream + immediate parse"""
        out = super().from_bytes(filepath, raw_bytes)
        out.parse()
        return out

    @classmethod
    def from_file(cls, filepath: str) -> BinaryFile:
        """defers read until .stream is accessed"""
        return super().from_file(filepath)

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str]) -> None:
        raise RuntimeError("BinaryFile cannot be initialised from_lines")

    @classmethod
    def from_stream(cls, filepath: str, stream: base.ByteStream) -> BinaryFile:
        """override .stream property + immediate parse"""
        assert isinstance(stream, (io.BytesIO, io.BufferedReader))
        out = super().from_stream(filepath, stream)
        assert out.type == base.DataType.BINARY
        out.parse()
        return out


class FriendlyBinaryFile(BinaryFile, base.FriendlyFile):
    pass


class TextFile(base.File):
    exts: List[str] = list()
    type = base.DataType.TEXT

    def lines(self) -> List[str]:
        """unparser"""
        raise NotImplementedError()

    def parse(self):
        """deferred post-init stage"""
        raise NotImplementedError()

    # initialisers
    # NOTE: wrapped ensure type is always TEXT
    @classmethod
    def from_archive(cls, filepath: str, archive) -> TextFile:
        """defers read until .stream is accessed"""
        return super().from_archive(filepath, archive)

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes) -> TextFile:
        """-> .from_stream + immediate parse"""
        out = super().from_bytes(filepath, raw_bytes)
        out.parse()
        return out

    @classmethod
    def from_file(cls, filepath: str) -> TextFile:
        """defers read until .stream is accessed"""
        return super().from_file(filepath)

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str]) -> TextFile:
        """-> .from_stream + immediate parse"""
        out = super().from_lines(filepath, lines)
        out.parse()
        return out

    @classmethod
    def from_stream(cls, filepath: str, stream: base.ByteStream) -> TextFile:
        """override .stream property + immediate parse"""
        assert isinstance(stream, (io.StringIO, io.TextIOWrapper))
        out = stream.from_stream(filepath, stream)
        assert out.type == base.DataType.TEXT
        out.parse()
        return out


class FriendlyTextFile(TextFile, base.FriendlyFile):
    pass


class HybridFile(base.File):
    exts: Dict[str, base.DataType] = dict()
    type = base.DataType.EITHER

    # NOTE: whether or not unparsers can convert is up to the subclass
    def as_bytes(self) -> List[str]:
        """binary unparser"""
        raise NotImplementedError()

    def lines(self) -> List[str]:
        """text unparser"""
        raise NotImplementedError()

    def identify(self) -> base.DataType:
        """determine type if ambiguous"""
        raise NotImplementedError()

    def parse(self, type_: base.DataType = None):
        type_ = self.type if type_ is None else type_
        if type_ == base.DataType.EITHER:
            type_ = self.identify()
        if type_ == base.DataType.BINARY:
            self.parse_binary()
            self.type = base.DataType.BINARY
        elif type_ == base.DataType.TEXT:
            self.parse_text()
            self.type = base.DataType.TEXT
        else:
            raise RuntimeError(f"Invalid type: {type!r}")

    def parse_binary(self):
        """binary parser"""
        raise NotImplementedError()

    def parse_text(self):
        """text parser"""
        # for line in self.stream: ...
        raise NotImplementedError()

    # initialisers
    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes, type_=None) -> HybridFile:
        """-> .from_stream + immediate parse"""
        type_ = cls.type if type_ is None else type_
        out = super().from_bytes(filepath, raw_bytes)
        out.parse(type_)
        return out

    @classmethod
    def from_lines(cls, filepath: str, lines: List[str]) -> HybridFile:
        """-> .from_stream + immediate parse"""
        out = super().from_lines(filepath, lines)
        out.type = base.DataType.TEXT
        out.parse()
        return out

    @classmethod
    def from_stream(cls, filepath: str, stream: base.DataStream) -> HybridFile:
        """override .stream property + immediate parse"""
        out = super().from_stream(filepath, stream)
        out.parse()
        return out


class FriendlyHybridFile(HybridFile, base.FriendlyFile):
    pass
