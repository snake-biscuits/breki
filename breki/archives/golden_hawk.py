# https://en.wikipedia.org/wiki/Cue_sheet_(computing)
# https://wiki.hydrogenaud.io/index.php?title=Cue_sheet
from __future__ import annotations

from . import base
from .. import files


track_mode = {
    "AUDIO": (base.TrackMode.AUDIO, 2352),
    "MODE1/2352": (base.TrackMode.BINARY_1, 2352),
    "MODE2/2336": (base.TrackMode.BINARY_1, 2336),
    "MODE2/2352": (base.TrackMode.BINARY_1, 2352)}


class Cue(base.DiscImage, files.FriendlyTextFile):
    """plaintext CUE sheet"""
    exts = ["*.cue"]

    def parse(self):
        self.is_parsed = True
        # NOTE: we assume all metadata we need is declared before "TRACK"
        state = dict()
        keywords = ("FILE", "REM", "TRACK")
        # NOTE: "INDEX 00 HH:MM:SS" indicates pregap start
        # -- "INDEX 01 HH:MM:SS" indicates data start
        # NOTE: 75 sectors per second
        lba = None
        for line in self.stream:
            keyword, space, context = line.strip().partition(" ")
            if keyword in keywords:
                state[keyword] = context
                if keyword == "REM" and context.endswith(" AREA"):
                    lba = {
                        "SINGLE-DENSITY AREA": 0,
                        "HIGH-DENSITY AREA": 45000}[context]
                elif keyword == "TRACK":
                    index, mode_str = context.split(" ")
                    mode, sector_size = track_mode[mode_str]
                    name = state["FILE"].rpartition(" ")[0].strip('"')
                    track = base.Track(mode, sector_size, lba, -1, name)
                    self.tracks.append(track)
        self.recalc_track_lengths()
        self.recalc_offsets()

    def recalc_offsets(self):
        """run after getting sector sizes from external files"""
        prev_lba, prev_length = 0, 0
        for track_index, track in enumerate(self.tracks):
            # skip first "HIGH-DENSITY AREA" track
            if not (track.start_lba == 45000 and prev_lba < 45000):
                track.start_lba = prev_lba + prev_length
            self.tracks[track_index] = track
            prev_lba, prev_length = track.start_lba, track.length
