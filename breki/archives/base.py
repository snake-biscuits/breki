from __future__ import annotations
import enum
import fnmatch
import os
from typing import List, Tuple

from .. import files
from ..files.parsed import parse_first


def path_tuple(path: str) -> Tuple[str]:
    out = tuple(path.replace("\\", "/").strip("/").split("/"))
    if len(out) > 1 and out[0] == ".":
        return out[1:]
    else:
        return out


class Archive(files.ParsedFile):
    archive: Archive

    def __repr__(self) -> str:
        descriptor = f"{len(self.namelist())} files"
        if self.archive is not None:
            archive_repr = " ".join([
                self.archive.__class__.__name__,
                f'"{self.archive.filename}"'])
            descriptor += f" in {archive_repr}"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    def extract(self, filename, to_path=None):
        if filename not in self.namelist():
            raise FileNotFoundError(f"Couldn't find {filename!r} to extract")
        to_path = "./" if to_path is None else to_path
        out_filename = os.path.join(to_path, filename)
        os.makedirs(os.path.dirname(out_filename), exist_ok=True)
        with open(out_filename, "wb") as out_file:
            out_file.write(self.read(filename))

    def extract_all(self, to_path=None):
        for filename in self.namelist():
            self.extract(filename, to_path)

    def extract_all_matching(self, pattern: str, to_path=None, case_sensitive=False):
        for filepath in self.search(pattern, case_sensitive):
            self.extract(filepath, to_path)

    def is_dir(self, filepath: str) -> bool:
        # NOTE: all_dirs could be a cached property
        all_dirs = {
            path_tuple(fn)[:-1]
            for fn in self.namelist()}
        all_dirs.update({
            tuple_[:i]
            for tuple_ in all_dirs
            for i in range(1, len(tuple_))})
        all_dirs.update({
            path_tuple(root)
            for root in (".", "./", "/")})
        return path_tuple(filepath) in all_dirs

    def is_file(self, filepath: str) -> bool:
        return filepath in self.namelist()

    def listdir(self, folder: str) -> List[str]:
        if not self.is_dir(folder):
            raise FileNotFoundError(f"no such directory: {folder}")
        folder_tuple = path_tuple(folder)
        if folder_tuple in {path_tuple(root) for root in (".", "./", "/")}:
            folder_tuple = tuple()  # empty
        folder_contents = set()
        for fn in self.namelist():
            path = path_tuple(fn)
            if path[:-1] == folder_tuple:
                base = path[-1]
                if self.is_dir(fn):
                    base += "/"
                folder_contents.add(base)  # file
            elif self.is_dir(fn):
                continue
            elif path[:len(folder_tuple)] == folder_tuple:  # descendant
                subfolder = path[len(folder_tuple):][0] + "/"
                folder_contents.add(subfolder)
        return sorted(folder_contents)

    @parse_first
    def namelist(self) -> List[str]:
        # NOTE: we assume namelist only contains filenames, no folders
        raise NotImplementedError("ArchiveClass has not defined .namelist()")

    def path_exists(self, filename: str) -> bool:
        return self.is_file(filename) or self.is_dir(filename)

    def read(self, filename: str) -> bytes:
        """read the contents of a file inside archive"""
        raise NotImplementedError("ArchiveClass has not defined .read()")

    def search(self, pattern: str, case_sensitive: bool = False) -> List[str]:
        if case_sensitive:
            return [
                filepath
                for filepath in self.namelist()
                if fnmatch.fnmatchcase(filepath, pattern)]
        else:
            return fnmatch.filter(self.namelist(), pattern)

    def sizeof(self, filename: str) -> int:
        return len(self.read(filename))

    def tree(self, folder: str = ".", depth: int = 0):
        """namelist pretty printer"""
        for filename in self.listdir(folder):
            print(f"{'  ' * depth}{filename}")
            full_filename = os.path.join(folder, filename)
            if self.is_dir(full_filename):
                self.tree(full_filename, depth + 1)


class TrackMode(enum.Enum):
    AUDIO = 0
    BINARY_1 = 1
    BINARY_2 = 2


class Track:
    mode: TrackMode
    sector_size: int  # 2048, 2336 or 2352
    start_lba: int
    length: int  # in sectors, not bytes
    name: str  # can be a filename
    size: int = property(lambda s: s.length * s.sector_size)

    def __init__(self, mode, sector_size, start_lba, length, name):
        self.mode = mode
        assert sector_size in (2048, 2336, 2352)
        self.sector_size = sector_size
        self.start_lba = start_lba
        self.length = length
        self.name = name

    def __repr__(self) -> str:
        args = ", ".join([
            str(getattr(self, a))
            for a in ("mode", "sector_size", "start_lba", "length")])
        return f'Track({args}, "{self.name}")'

    def __contains__(self, lba: int) -> bool:
        return self.start_lba <= lba < self.start_lba + self.length

    def data_slice(self) -> slice:
        """index raw sector with this slice to get just the data"""
        if self.mode == TrackMode.AUDIO or self.sector_size == 2048:
            return slice(0, self.sector_size)
        elif self.mode == TrackMode.BINARY_1:
            header_size = {2352: 16}[self.sector_size]
        elif self.mode == TrackMode.BINARY_2:
            header_size = {2336: 8, 2352: 24}[self.sector_size]
        return slice(header_size, 2048 + header_size)


class DiscImage(files.FriendlyFile):
    archive: Archive
    # NOTE: track data is stored in friends
    # unique to DiscImage
    tracks: List[Track]
    _cursor: Tuple[int, int]
    # ^ (track_index, sub_lba)
    # NOTE: true_lba = track.start_lba + sub_lba

    def __init__(self, filepath: str, archive=None, *args, **kwargs):
        super().__init__(filepath, archive, *args, **kwargs)
        self.tracks = list()
        self._cursor = (0, 0)

    def __repr__(self):
        descriptor = f"{len(self)} sectors ({len(self.tracks)} tracks)"
        # TODO: length in MB / seconds
        # Red Book CD-DA: 44.1 KHz 16-bit PCM Stereo -> 176400 bytes / second
        if self.archive is not None:
            archive_repr = " ".join([
                self.archive.__class__.__name__,
                f'"{self.archive.filename}"'])
            descriptor += f" in {archive_repr}"
        return f"<{self.__class__.__name__} {descriptor} @ 0x{id(self):016X}>"

    @parse_first
    def __contains__(self, lba: int) -> bool:
        return any(lba in track for track in self.tracks)

    @parse_first
    def __len__(self):
        if len(self.tracks) > 0:
            return max(t.start_lba + t.length for t in self.tracks)
        else:
            return 0

    @parse_first
    def sector_track(self, lba: int) -> Track:
        hits = [
            track
            for track in self.tracks
            if lba in track]
        if len(hits) == 0:
            return None
        else:  # assuming 2x hits is the edge between 2 tracks
            # print(f"sector #{lba} is in the following tracks:")
            # {print(hit) for hit in hits}
            return hits[0]

    @parse_first
    def export_wav(self, track_index: int, filename: str = None):
        # https://docs.fileformat.com/audio/wav/
        track = self.tracks[track_index]
        assert track.mode == TrackMode.AUDIO, "track is not audio"
        if filename is None:
            if track.name.endswith(".raw"):
                filename = track.name.replace(".raw", ".wav")
            else:
                filename = f"track_{track_index:02d}.wav"
        # generate header
        wav_header = [
            b"RIFF", (track.size + 36).to_bytes(4, "little"), b"WAVEfmt ",
            b"\x10\x00\x00\x00", b"\x01\x00", b"\x02\x00",
            (44100).to_bytes(4, "little"), (176400).to_bytes(4, "little"),
            b"\x04\x00", b"\x10\x00", b"data", track.size.to_bytes(4, "little")]
        self.sector_seek(track.start_lba)
        with open(filename, "wb") as wav_file:
            wav_file.write(b"".join(wav_header))
            wav_file.write(self.sector_read(track.length))

    # NOTE: for FriendlyFile subclasses
    @property
    def friend_patterns(self) -> List[str]:
        return {
            track.name: files.DataType.BINARY
            for track in self.tracks}

    def read(self, length: int = -1) -> bytes:
        """moves cursor to end of sector, use with caution"""
        if length == -1:
            return self.sector_read()
        sector_length = length // 2048
        if length % 2048 != 0:
            sector_length += 1
        return self.sector_read(sector_length)[:length]

    # NOTE: FriendlyFile subclasses should call this at the end of parsing
    def recalc_track_lengths(self):
        """get track lengths from filesizes (if nessecary)"""
        if len(self.friends) == 0:
            self.make_friends()
        for track_index, track in enumerate(self.tracks):
            if track.length == -1:  # unknown
                try:
                    file_size = self.friends[track.name].size
                except KeyError:
                    raise FileNotFoundError(f'"{track.name}"')
                assert file_size % track.sector_size == 0, f"{track=}, {file_size=}"
                track.length = file_size // track.sector_size
                self.tracks[track_index] = track

    @parse_first
    def sector_read(self, length: int = -1) -> bytes:
        """expects length in sectors"""
        track_index, sub_lba = self._cursor
        track = self.tracks[track_index]
        if length == -1:
            if track.start_lba + track.length == len(self):  # last track
                length = track.length - sub_lba
            else:
                raise NotImplementedError("cannot read past end of current track")
        if sub_lba + length > track.length:
            raise NotImplementedError("cannot read past end of current track")
        data_slice = track.data_slice()
        track_stream = self.friends[track.name].stream
        track_stream.seek(sub_lba * track.sector_size)
        sector_data = [
            track_stream.read(track.sector_size)[data_slice]
            for i in range(length)]
        # NOTE: we're assuming that all tracks have gaps between them
        # -- so we don't need to worry about changing tracks here
        self._cursor = (track_index, sub_lba + length)
        return b"".join(sector_data)

    @parse_first
    def sector_seek(self, lba: int, whence: int = 0) -> int:
        assert whence in (0, 1, 2)
        current_lba = self.sector_tell()
        if whence == 1:
            lba = current_lba + lba
        elif whence == 2:
            lba = len(self) + lba
        for track_index, track in enumerate(self.tracks):
            if track.start_lba <= lba < track.start_lba + track.length:
                self._cursor = (track_index, lba - track.start_lba)
                return lba
        raise RuntimeError(f"couldn't find a track containing sector: {lba}")

    @parse_first
    def sector_tell(self) -> int:
        track_index, sub_lba = self._cursor
        track = self.tracks[track_index]
        return track.start_lba + sub_lba
