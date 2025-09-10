from __future__ import annotations
import fnmatch
import functools
import io
import os
from typing import Dict, List

from . import base


def parse_first(method):
    def wrapper(self, *args, **kwargs):
        if not self.is_parsed:
            self.parse()
            self.is_parsed = True
        return method(self, *args, **kwargs)
    return wrapper


class ParsedFile(base.File):
    exts: List[str] = list()  # class-level definition
    # ^ ["*.ext"]
    # NOTE: just a hint, not enforced
    is_parsed: bool
    log: List[str]

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.is_parsed = False
        self.log = list()

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

    def save(self):
        """save changes, overwriting original file"""
        self.save_as(os.path.join(self.folder, self.filename))

    def save_as(self, filepath: str):
        """save changes to file"""
        with open(filepath, "wb") as out_file:
            out_file.write(self.as_bytes())

    # intialisers
    # NOTE: wrapped to enforce cls.type
    @classmethod
    def from_archive(cls, archive, filepath: str, type_=None, code_page=None) -> ParsedFile:
        """defers read until .stream is accessed"""
        assert type_ in (None, cls.type)
        return super().from_archive(archive, filepath, cls.type, code_page)

    @classmethod
    def from_bytes(cls, filepath: str, raw_bytes: bytes, type_=None, code_page=None) -> ParsedFile:
        """-> .from_stream"""
        assert type_ in (None, cls.type)
        return super().from_bytes(filepath, raw_bytes, cls.type, code_page)

    @classmethod
    def from_file(cls, filepath: str, type_=None, code_page=None) -> ParsedFile:
        """defers read until .stream is accessed"""
        assert type_ in (None, cls.type)
        return super().from_file(filepath, cls.type, code_page)

    # @classmethod
    # def from_lines(cls, filepath: str, lines: List[str], code_page=None) -> ParsedFile:
    #     """-> .from_stream"""
    #     return super().from_lines(filepath, lines, code_page)

    @classmethod
    def from_stream(cls, filepath: str, stream: base.DataStream, type_=None, code_page=None) -> ParsedFile:
        """override .stream property"""
        assert type_ in (None, cls.type)
        # NOTE: File.from_stream will ensure stream is valid for cls.type
        return super().from_stream(filepath, stream, cls.type, code_page)


class FriendlyFile(ParsedFile):
    friend_patterns: Dict[str, base.DataType]
    friends: Dict[str, base.File]

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.friends = dict()

    def make_friends(self, candidates: Dict[str, str] = None, archive=None):
        """post-initialisation friend collection"""
        # NOTE: friends can be found in all sorts of places
        archive = self.archive if archive is None else archive
        if candidates is None:
            if self.archive is None:
                neighbours = os.listdir(self.folder)
            else:
                neighbours = self.archive.listdir(self.folder)
            candidates = {
                filename: os.path.join(self.folder, filename)
                for filename in neighbours}
        friends = {
            filename: (filepath, type_)
            for filename, filepath in candidates.items()
            for pattern, type_ in self.friend_patterns.items()
            if fnmatch.fnmatch(filename, pattern)}
        for filename, (filepath, type_) in friends.items():
            if archive is not None:
                friend = base.File.from_archive(archive, filepath, type_)
            else:
                friend = base.File.from_file(filepath, type_)
            self.friends[filename] = friend

    @functools.cached_property
    def friend_patterns(self) -> Dict[str, base.DataType]:
        """glob patterns for files we can befriend"""
        return dict()

    # intialisers
    @classmethod
    def from_archive(cls, archive, filepath: str, type_=None, code_page=None) -> FriendlyFile:
        out = super().from_archive(archive, filepath, type_, code_page)
        out.make_friends()
        return out

    @classmethod
    def from_file(cls, filepath: str, type_=None, code_page=None) -> FriendlyFile:
        out = super().from_file(filepath, type_, code_page)
        out.make_friends()
        return out


class BinaryFile(ParsedFile):
    type = base.DataType.BINARY

    def as_bytes(self) -> bytes:
        """unparser"""
        raise NotImplementedError()

    # initialisers
    @classmethod
    def from_lines(cls, *args, **kwargs) -> None:
        raise RuntimeError("BinaryFile cannot be initialised from_lines")


class FriendlyBinaryFile(BinaryFile, FriendlyFile):
    pass


class TextFile(ParsedFile):
    type = base.DataType.TEXT


class FriendlyTextFile(TextFile, FriendlyFile):
    pass


class HybridFile(ParsedFile):
    exts: Dict[str, base.DataType] = dict()
    # ^ {"*.bin": Datatype.BINARY}
    type = base.DataType.EITHER

    def __repr__(self) -> str:
        descriptor = [f'"{self.filename}"']
        if self.type == base.DataType.EITHER:
            for pattern, type_ in self.exts.items():
                if fnmatch.fnmatch(self.filename, pattern):
                    self.type = type_
                    break
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
        for pattern, type_ in cls.exts.items():
            if fnmatch.fnmatch(cls.filename, pattern):
                return type_
        else:
            return base.DataType.EITHER
        # NOTE: subclasses should do further testing for patterns w/ type EITHER
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
        elif type_ == base.DataType.EITHER:
            raise RuntimeError("failed to identify DataType")
        else:
            raise RuntimeError(f"Invalid DataType: {type_!r}")
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

    def _get_stream(self, type_=None) -> base.DataStream:
        """deferring opening the file until it's touched"""
        type_ = self.type if type_ is None else type_
        stream = super()._get_stream(type_)
        if type_ == base.DataType.EITHER:
            type_ = self.identify(self.filename, stream)
            stream = super()._get_stream(type_)
        self.type = type_
        return stream

    stream = functools.cached_property(_get_stream)

    # initialisers
    @classmethod
    def from_archive(cls, archive, filepath: str, type_=None, code_page=None) -> HybridFile:
        """defers read until .stream is accessed"""
        return super().from_archive(archive, filepath, type_, code_page)

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


class FriendlyHybridFile(HybridFile, FriendlyFile):
    pass
