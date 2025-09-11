from __future__ import annotations
import functools
import io
from typing import List
import zipfile

from .. import files
from ..files.parsed import parse_first
from . import base


class Zip(base.Archive, files.BinaryFile):
    exts = ["*.zip"]

    def __repr__(self) -> str:
        descriptor = f"{len(self.namelist())} files mode='{self._zip.mode}'"
        if self.archive is not None:
            archive_repr = " ".join([
                self.archive.__class__.__name__,
                f'"{self.archive.filename}"'])
            descriptor += f" in {archive_repr}"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    def _get_stream(self, type_=None) -> files.DataStream:
        try:
            return super()._get_stream(type_)
        except FileNotFoundError:
            # default to an empty zip
            return io.BytesIO(b"".join([
                b"PK\x05\x06", b"\x00" * 16,
                b"\x20\x00XZP1 0", b"\x00" * 26]))

    stream = functools.cached_property(_get_stream)

    @parse_first
    def extract(self, filepath: str, to_path=None):
        if filepath.startswith("./"):
            filepath = filepath[2:]
        self._zip.extract(filepath, to_path)

    @parse_first
    def namelist(self) -> List[str]:
        return self._zip.namelist()

    @parse_first
    def read(self, filepath: str) -> bytes:
        if filepath.startswith("./"):
            filepath = filepath[2:]
        return self._zip.read(filepath)

    def parse(self, mode: str = "a", **kwargs):
        if self.is_parsed:
            return
        self.is_parsed = True
        self._zip = zipfile.ZipFile(self.stream, mode=mode, **kwargs)

    @parse_first
    def sizeof(self, filepath: str) -> int:
        if filepath.startswith("./"):
            filepath = filepath[2:]
        return self._zip.getinfo(filepath).file_size

    @parse_first
    def as_bytes(self) -> bytes:
        # write ending records if edits were made (adapted from ZipFile.close)
        if self._zip.mode in "wxa" and self._zip._didModify and self._zip.fp is not None:
            with self._zip._lock:
                if self._zip._seekable:
                    self._zip.fp.seek(self._zip.start_dir)
                self._zip._write_end_record()
        self._zip._didModify = False  # don't double up when .close() is called
        # NOTE: _zip.close() can get funky but it's OK because .stream isn't a real file
        self.stream.seek(0)
        return self.stream.read()
