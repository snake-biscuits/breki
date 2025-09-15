# https://github.com/ZoneTool/zonetool/
# https://github.com/RagdollPhysics/zonebuilder/
import enum
import io
from typing import List
import zlib

from .. import binary
from .. import core
from .. import files
from . import base
from . import id_software


class Iwd(id_software.Pk3):
    exts = ["*.iwd"]


class Header(core.Struct):
    decompressed_size: int  # size of decompressed data - header size
    total_size: int  # size of all indexed assets
    unknown: List[int]  # 8 streams + 1 other int?
    __slots__ = ["decompressed_size", "total_size", "unknown"]
    _format = "11I"
    _arrays = {"unknown": 9}


class Header2(core.Struct):
    num_pointers: int
    unknown: int  # -1 if num_pointers != 0, else 0
    num_assets: int
    unused: int  # always -1
    __slots__ = ["num_pointers", "unknown", "num_assets", "unused"]
    _format = "4i"


class AssetType(enum.Enum):
    XMODEL_PIECES = 0x00
    PHYS_PRESET = 0x01
    XANIM = 0x02
    XMODEL = 0x03
    MATERIAL = 0x04
    PIXEL_SHADER = 0x05
    TECH_SET = 0x06
    IMAGE = 0x07
    SND_CURVE = 0x08
    LOADED_SOUND = 0x09
    COL_MAP_SP = 0x0A
    COL_MAP_MP = 0x0B
    COM_MAP = 0x0C
    GAME_MAP_SP = 0x0D  # .d3dbsp?
    GAME_MAP_MP = 0x0E  # .d3dbsp?
    MAP_ENTS = 0x0F  # .ent?
    GFX_MAP = 0x10
    LIGHT_DEF = 0x11
    UI_MAP = 0x12
    FONT = 0x13
    MENU_FILE = 0x14
    MENU = 0x15
    LOCALISATION = 0x16
    WEAPON = 0x17  # .gsc?
    SND_DRIVER_GLOBALS = 0x18
    IMPACT_FX = 0x19
    AI_TYPE = 0x1a
    MP_TYPE = 0x1b
    CHARACTER = 0x1c
    XMODEL_ALIAS = 0x1D
    UNKNOWN_30 = 0x1E
    RAW_FILE = 0x1F
    STRING_TABLE = 0x20  # .csv


class FastFile(base.Archive, files.BinaryFile):
    """specifically for IW3 (Call of Duty 4: Modern Warfare)"""
    exts = ["*.ff"]
    header: Header
    header2: Header2
    pointers: List[int]  # linked to strings? almost always -1; sometimes 0
    strings: List[str]
    asset_types: List[AssetType]

    def __init__(self, filepath: str, archive=None, code_page=None):
        super().__init__(filepath, archive, code_page)
        self.pointers = list()
        self.strings = list()
        self.asset_types = list()

    # TODO: .namelist() & .read() [@parse_first]

    def parse(self):
        magic, version = binary.read_struct(self.stream, "8sI")
        assert magic == b"IWffu100", "not a FastFile"
        if version != 5:
            raise NotImplementedError(f"FastFile v{version} not supported")
        # decompress
        decompressed_data = zlib.decompress(self.stream.read())
        self.stream = io.BytesIO(decompressed_data)  # OVERRIDE
        # parse
        self.header = Header.from_stream(self.stream)
        assert self.header.decompressed_size + 44 == len(decompressed_data)
        self.header2 = Header2.from_stream(self.stream)
        # optional block of pointers? & strings
        if self.header2.num_pointers != 0:
            assert self.header2.unknown == -1  # observed, but not understood
            self.pointers = binary.read_struct(
                self.stream, f"{self.header2.num_pointers}i")
            num_strings = self.pointers.count(-1)
            self.strings = [
                binary.read_str(self.stream, *self.code_page)
                for i in range(num_strings)]
            assert self.strings[-1] != ""
        else:  # "*_load.ff"?
            assert self.header2.unknown == 0  # observed, but not understood
        assert self.header2.unused == -1
        # block of asset types
        for i in range(self.header2.num_assets):
            asset_type, separator = binary.read_struct(self.stream, "Ii")
            try:
                self.asset_types.append(AssetType(asset_type))
                assert separator == -1
            except Exception:  # code_post_gfx{,_mp}
                print(f"!!! FAIL !!! {i=} {asset_type=:08X} {separator=:08X}")
                return
        assert binary.read_struct(self.stream, "i") == -1  # terminator
        # NOTE: from here we have a list of assets (matching asset_types)
        # -- no indication of offset or length anywhere
        # -- we will have to parse enough to calcuate lengths
        # NOTE: afaik assets are separated by 0xFFFFFFFF
        # TODO: create lookup table for .namelist() & .read()
        # -- out.assets = {"filename": (AssetType, offset, length)}
        ...
