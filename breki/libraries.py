import fnmatch
import os
import socket  # gethostname
from types import ModuleType
from typing import Dict, Generator, List, Tuple


# "Types"
LocalBranches = Dict[ModuleType, List[str]]
# ^ {branch_script: ["local_game_dir"]}
# NOTE: local_game_dir is pretty enough on it's own


LibraryGames = Dict[str, Dict[str, List[str]]]
# ^ {"section": {"game": ["paths"]}
# NOTE: "game" is not part of the path, it's the Pretty name
# NOTE: try to group dirs by Game+Mod (e.g. "Quake (Id1)")
# -- this avoids overlapping map names (e.g. e1m1)


LibraryBranches = Dict[ModuleType, LibraryGames]
# ^ {branch_script: {"section": {"game": ["paths"]}}}


PrettyFiles = Dict[str, object]
# ^ {"Pretty | Filename": SomeClass.from_file(full_path)}


ScanResult = Tuple[str, str, List[Tuple[str, str]]]
# ^ ("section", "game", [("short_path", "full_path")])
# -> {"Section | Game | ShortPath": SomeClass.from_file(full_path)}


# MegaTest Scan & Collect
class GameLibrary:
    _sections = [
        "Steam", "GoG", "Mod",  # PC
        "Dreamcast", "PS4", "Xbox360"]  # Console
    # TODO: allow for multiple SteamLibrary dirs

    def __init__(self, **paths: Dict[str, str]):
        if not set(paths).issubset(set(self._sections)):
            invalid_sections = set(paths) - set(self._sections)
            raise RuntimeError(f"{invalid_sections=}")
        for section in self._sections:
            path = paths.get(section, None)
            setattr(self, section, path)

    def __repr__(self) -> str:
        attrs = ",\n".join([
            "\t" + f"{section}={getattr(self, section)!r}"
            for section in self._sections
            if getattr(self, section) is not None])
        return "".join([self.__class__.__name__, "(\n", attrs, ")"])

    def __getitem__(self, section: str) -> str:
        if section not in self._sections:
            raise AttributeError(f"{section!r} is not a valid section")
        return getattr(self, section)

    def scan(self, search_area: LibraryGames, pattern: str) -> Generator[ScanResult, None, None]:
        for section, games in search_area.items():
            if self[section] is None:
                continue  # not registered in library, skip
            for game, paths in games.items():
                for path in paths:
                    file_dir = os.path.join(self[section], path)
                    if not os.path.isdir(file_dir):
                        continue  # not installed, skip
                    filenames = fnmatch.filter(os.listdir(file_dir), pattern)
                    file_paths = [
                        (filename, os.path.join(file_dir, filename))
                        for filename in filenames]
                    yield section, game, file_paths


librarians = {
    # Windows Desktop
    ("bikkie", "ITANI_WAYSOUND"): GameLibrary(
        Steam="D:/SteamLibrary/steamapps/common/",
        GoG="D:/GoG Galaxy/Games/",
        Mod="E:/Mod/",
        Dreamcast="D:/Emulators/Sega/Dreamcast/",
        PS4="E:/Mod/PS4/",
        Xbox360="E:/Mod/X360/"),
    # Linux Laptop
    ("bikkie", "coplandbentokom-9876"): GameLibrary(
        Mod="/media/bikkie/3964-39352/Mod/"),
    # Linux Desktop
    ("bikkie", "megalodon"): GameLibrary(
        Steam="/home/bikkie/.steam/steam/steamapps/common/",
        Mod="/home/bikkie/drives/ssd1/Mod/",
        Dreamcast="/home/bikkie/drives/ssd1/Emulators/Sega/Dreamcast/")}

librarian_aliases = {
    "Jared@ITANI_WAYSOUND": "bikkie"}


def library_card() -> (str, str):
    user = os.getenv("USERNAME", os.getenv("USER"))
    host = os.getenv("HOSTNAME", os.getenv("COMPUTERNAME", socket.gethostname()))
    user = librarian_aliases.get(f"{user}@{host}", user)
    return (user, host)


def game_library() -> GameLibrary:
    """returns the GameLibrary for the current library_card"""
    # TODO: allow pytest flags to set/override GameLibrary paths
    return librarians.get(library_card(), GameLibrary())


# TODO: collecting multiple Files inside Library
# -- choose init & params
# -- hints
# -- nested archive path search (NAPS)
