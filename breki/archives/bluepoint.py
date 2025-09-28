from .. import files
from . import base


class Bpk(base.Archive, files.BinaryFile):
    """Titanfall (Xbox360) asset archive format"""
    exts = ["*.bpk"]

    def __init__(self, filename: str):
        raise NotImplementedError()
