import pytest

from breki.archives.base import Archive


def all_subclasses_of(cls):
    for sc in cls.__subclasses__():
        yield sc
        for ssc in all_subclasses_of(sc):
            yield ssc


archive_classes = {
    f"{cls.__module__.rpartition('.')[-1]}.{cls.__name__}": cls
    for cls in all_subclasses_of(Archive)}


@pytest.mark.parametrize("archive_class", archive_classes.values(), ids=archive_classes.keys())
def test_in_spec(archive_class: object):
    assert issubclass(archive_class, Archive), "not a base.Archive subclass"
    assert hasattr(archive_class, "exts"), "exts not specified"
    assert isinstance(archive_class.exts, (list, dict)), "exts must be of type list"
    # NOTE: sega.GDRom is a FriendlyHybridFile, since it wraps multiple DiscImage formats
    for ext in archive_class.exts:
        assert isinstance(ext, str), "ext must be of type str"
        assert "*" in ext, "ext must contain a wildcard"
        # NOTE: mostly "*.ext", but "*_dir.vpk" breaks that pattern
        # -- "pack*.vpk" for troika.Vpk breaks the pattern even more
    # NOTE: base.Archive provides defaults for all essential methods
    # -- but most raise NotImplementedError
    # -- .parse(), .namelist() & .read() must all be implemented by the subclass
    # -- each subclass will need it's own tests for those methods
    # -- as well as confirming __init__ creates an empty ArchiveClass
    # -- we also need to confirm parse() is called before namelist, read, extract etc.
    # -- and that .parse() sets .is_parsed to True
    # NOTE: .read() w/ leading "./" is important to test for
    # -- since FriendlyFile always looks in "./" for friends in top-level folders
