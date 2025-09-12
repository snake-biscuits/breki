import pytest

from breki.archives.base import DiscImage


def all_subclasses_of(cls):
    for sc in cls.__subclasses__():
        yield sc
        for ssc in all_subclasses_of(sc):
            yield ssc


disc_classes = {
    f"{cls.__module__.rpartition('.')[-1]}.{cls.__name__}": cls
    for cls in all_subclasses_of(DiscImage)}
# should be:
# -- alcohol.Mds
# -- golden_hawk.Cue
# -- mame.Chd
# -- padus.Cdi
# -- sega.Gdi


@pytest.mark.parametrize(
    "disc_class", disc_classes.values(), ids=disc_classes.keys())
def test_in_spec(disc_class: object):
    assert issubclass(disc_class, DiscImage), "not a base.DiscImage subclass"
    assert hasattr(disc_class, "exts"), "ext not specified"
    assert isinstance(disc_class.exts, list), "ext must be of type str"
    for ext in disc_class.exts:
        assert isinstance(ext, str), "ext must be of type str"
        assert ext.startswith("*."), "ext must start with wildcard"
    # TODO: parse, read & namelist implemented
    # TODO: parse sets .is_parsed
