# breki

**B**ikkie's **R**everse **E**ngineering **Ki**t


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


## Installation

> TODO


## Usage

> TODO
