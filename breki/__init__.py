__all__ = [
    "binary", "core", "files", "libraries",
    "find_all", "read_str", "read_struct", "write_struct", "xxd",
    "BitField", "Struct", "MappedArray",
    "CodePage", "DataType", "File", "FriendlyFile",
    "ByteStream", "DataStream", "TextStream",
    "ParsedFile",
    "BinaryFile", "FriendlyBinaryFile",
    "HybridFile", "FriendlyHybridFile",
    "TextFile", "FriendlyTextFile"]

# modules
from . import binary
from . import core
from . import files
from . import libraries

# classes
from .binary import (
    find_all, read_str, read_struct, write_struct, xxd)
from .core import (
    BitField, Struct, MappedArray)
from .files import (
    CodePage, DataType, File, FriendlyFile,
    ByteStream, DataStream, TextStream,  # type hints
    ParsedFile,  # base class
    BinaryFile, FriendlyBinaryFile,
    HybridFile, FriendlyHybridFile,
    TextFile, FriendlyTextFile)
# from .libraries import (
#     ...)
