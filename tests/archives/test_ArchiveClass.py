import pytest

from breki.archives.base import Archive
from breki.files.parsed import BinaryFile, HybridFile, TextFile


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
    assert hasattr(archive_class, "exts"), "no exts attr"
    if not issubclass(archive_class, HybridFile):
        assert issubclass(archive_class, (BinaryFile, TextFile))
        assert isinstance(archive_class.exts, list), "non-list exts"
    else:
        assert isinstance(archive_class.exts, dict), "non-dict exts"
    # NOTE: sega.GDRom is a FriendlyHybridFile, since it wraps multiple DiscImage formats
    assert len(archive_class.exts) > 0, "no exts"
    for ext in archive_class.exts:
        assert isinstance(ext, str), "non-str ext"
        assert "*" in ext, "ext does not contain wildcard"
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
