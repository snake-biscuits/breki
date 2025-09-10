# TODOs

copied from `utils_split.md` planning doc


## Dependencies
> Currently standard library only


## Migration from `bsp_tool`
 * `utils.binary` -> `binary`
 * `core`
 * `archives`
   - ArchiveClasses
   - DiscClasses
 * `tests.files` -> `libraries`
   - GameLibrary
   - Librarians
   - TODO: `~/.library_map.json` config
   - bulk file parsing
     * optionally defer w/ a generator

### Maybes
 * `lumps`
   - `LumpClass.from_count` is handy
   - `BasicLumpClass` is just as handy
 * `apex_archive`
   - but not hardcoded for apex
   - for managing an archive of game updates


## Features
 * `archives`
   - `Archive`: virtual filesystem (similar to `zipfile.ZipFile`)
   - `DiscImage`: virtual disc image (tracks & sectors; behaves like a `BinaryStream`)
 * `binary`
   - `xxd`: hex view for terminal
   - `find_all`: `.find` but it keeps looking
   - `read_str`: read stream until null byte
   - `read_struct` & `write_struct`: `struct` wrappers for working with binary streams
 * `core`
   - built on `struct` from the standard library
   - `Struct`: robust base class for parsing objects from bytes
   - `MappedArray`: used by `Struct` for handling nested structures
   - `BitField`: basic bitfield parser
 * `files`
   - `CodePage`: string encoding & decoding tool
   - `File`: virtual file wrapper (stream + metadata)
   - `FriendlyFile`: base class for objects w/ data spread over multiple files
   - `ParsedFile`: base class for objects representing file data
   - `BinaryFile` & `TextFile`: `ParsedFile` subclasses for their matching `DataType`s
   - `HybridFile`: `ParsedFile` subclass for files with both binary & text representations


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
