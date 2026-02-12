# Changelog

## v0.1.0 (??? 2026)

### New
 * Migrated code from `bsp_tool`
 * `archives`
   - `nintendo.Nds`
   - `sega.Vmu`
 * `files`
   - `base`
     * `CodePage`
     * `File`
   - `parsed`
     * `ParsedFile`
       - `BinaryFile`
       - `TextFile`
       - `HybridFile`
     * `FriendlyFile`
       - `BinaryFriendlyFile`
       - `TextFriendlyFile`
       - `HybridFriendlyFile`

### Changed
 * using `ParsedFile` subclasses for `Archive` & `DiscImage` subclasses
