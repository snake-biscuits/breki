# TODOs

## General
 * `ParsedFile`
   - `._repr(self, descriptor: str)`
     called w/ `super()` to reduce duplicate code
   - `._get_stream(self, type_)` overrides
     fall back to `_default` on `FileNotFound`
   - `.from_nested_archive(cls, filepath: str, archive_classes: dict)`
     walk down into a nested series of ArchiveClasses & open a file
     `archive_classes = {"*.ext": ArchiveClass}`
     `bsp_tool.autodetect.naps`

## Planned Features
 * path utils
   - split folder & filename
   - expand user / env
   - get extension
   - case insensitive glob / fuzzyfind

### New Base Classes
> a standard file w/ lumps baseclass
> base.Bsp is kinda specific, especially in name

 * classes (both `bff.File` subclasses)
   - `LumpFile`
      * is a lump
      * indexed by a `bff.FriendlyFile`
   - `LumpyFile`
      * has lumps
 * examples
   - `base.Bsp`
   - `bish.DXBC`
   - `lumps.GameLump`
   - `stbsp.StreamBsp`
   - `bspx` & `.vtf` also have some lumps
   - `ExternalLumpManager`
     * could be a `FriendlyFile` w/ no base file
 * key features
   - `.changes` dict to speed up `.lump_as_bytes`
   - deferred SpecialLump parsing
   - branch scripts system for multiple formats
 * universal methods & attrs
   - `.headers: Dict[str, Header]`
   - `.__getattr__` `x.LUMP` / `x.RAW_LUMP`
   - `.loading_errors: Dict[str, Exception]`
   - `.save_as()`
   - `.lump_as_bytes(str) -> bytes`

### Parsers
 * `.ksy` [Kaitai Struct](https://doc.kaitai.io/)
   - official tools feel bloated
   - and a nightmare to install on windows
   - want a lightweight alternative
 * `.bt` Binary Template
   - format used by [010 Hex](https://www.sweetscape.com/010editor/)
   - useful for sharing w/ other reverse engineers
 * `.c` / `.h`
   - convert `core.Struct` to and from `C`
