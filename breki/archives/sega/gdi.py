# https://multimedia.cx/eggs/understanding-the-dreamcast-gd-rom-layout/
from ... import files
from .. import base


class Gdi(base.DiscImage, files.TextFile):
    exts = ["*.gdi"]

    def parse(self):
        if self.is_parsed:
            return
        self.is_parsed = True
        num_tracks = int(self.stream.readline())
        modes = {
            "0": base.TrackMode.AUDIO,
            "4": base.TrackMode.BINARY_1}
        for i, line in enumerate(self.stream):
            line = line.rstrip()
            assert line.count(" ") == 5
            track_number, start_lba, mode, sector_size, name, zero = line.split(" ")
            assert int(track_number) == i + 1
            assert zero == "0"
            mode = modes[mode]
            sector_size = int(sector_size)
            start_lba = int(start_lba)
            # NOTE: length of -1 means we get it from filesize
            self.tracks.append(base.Track(mode, sector_size, start_lba, -1, name))
        assert len(self.tracks) == num_tracks
        self.recalc_track_lengths()
