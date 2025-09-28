from .. import files
from . import base


class Nightfire007(base.Archive, files.BinaryFile):
    exts = ["*.007"]

    def __init__(self, filename: str):
        raise NotImplementedError()
