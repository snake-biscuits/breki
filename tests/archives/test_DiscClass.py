import pytest

from breki.archives.base import DiscImage
from breki.files.parsed import BinaryFile, TextFile


def all_subclasses_of(cls):
    for sc in cls.__subclasses__():
        yield sc
        for ssc in all_subclasses_of(sc):
            yield ssc


disc_classes = {
    f"{cls.__module__.rpartition('.')[-1]}.{cls.__name__}": cls
    for cls in all_subclasses_of(DiscImage)}


@pytest.mark.parametrize(
    "disc_class", disc_classes.values(), ids=disc_classes.keys())
def test_in_spec(disc_class: object):
    assert issubclass(disc_class, DiscImage), "not a base.DiscImage subclass"
    assert hasattr(disc_class, "exts"), "no exts attr"
    # NOTE: assuming no HybridFile DiscImages
    assert issubclass(disc_class, (BinaryFile, TextFile))
    assert isinstance(disc_class.exts, list), "non-list exts"
    assert len(disc_class.exts) > 0, "no exts"
    for ext in disc_class.exts:
        assert isinstance(ext, str), "non-str ext"
        assert ext.startswith("*."), "ext does not start with wildcard"
    # TODO: parse, read & namelist implemented
    # TODO: parse sets .is_parsed
