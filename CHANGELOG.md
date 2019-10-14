### 1.2.4

Nuke:

* Performance improvement when keying by caching metadata. (#90)
* Fixed for stereo renders by using nuke.thisView() (#103)
* Fixed errors on open with more than 16 layers of Cryptomatte (#95)
* Fixed gizmo for Blender channel names containing "." which get converted to underscores in Nuke, also fixed for Encryptomatte. (#104)

### 1.2.3:

Nuke:

* Fixed bug with hierarchical names (contributed by Jens Lindgren)

### 1.2.2:

Fusion (by C&eacute;dric Duriau):

* Support for EXR images with a data window smaller than display window (builtin DoD)
  * Fixed crash for Redshift frames with DoD [#80](https://github.com/Psyop/Cryptomatte/issues/80)
  * Fixed crash for Mantra frames with DoD [#64](https://github.com/Psyop/Cryptomatte/issues/64)
* Updated README install documentation [#62](https://github.com/Psyop/Cryptomatte/issues/62)
* Minimum Fusion version is now 9.0.2
* Changed repo structure to match Fusion directory structure
* Added Fuse registry information (help, company, version, ...)
* Added dosctrings
* Cleaned up code

### 1.2.1:

A reorganization of this repo, and a minor update to the Nuke plugins.

* Reorganized Fusion and Nuke documentation into separate files. 
* Added some tiny test images showing different cases of Cryptomatte usage.

Nuke:

* Added troubleshooting button to Cryptomatte gizmo
* Fixed Encryptomatte issue where it couldn't start a new Cryptomatte with no inputs
* Added test for Encryptomatte with no inputs
* Do not allow keying IDs with zero coverage
* Fixed some test issues in Nuke 11.3
* Cleaner decryptomatte results, with maximum of 3 nodes in sequence, no dots, and better naming


### 1.2.0:

This is a major update to both the Nuke plugins and Fusion plugins, and a minor update to the Cryptomatte specification. 

Specification:

* Changed specification regarding sidecar manifests, such that they are always sidecars with relative paths.
* Support for UTF-8 Characters in Nuke plugin and specification
* Deprecated preview channels

Nuke:

* Encryptomatte
  * Added Encryptomatte - allows modifying or creating Cryptomattes in Nuke
* Added support for sidecar manifests
* Added layer selection pulldown
* New Eyedropper "picker" knobs which use picker position and not sampled values
  * No longer use Color knob's built in picker
  * Fixed keying problems sometimes caused by GPU-enabled viewers
  * Can pick mattes while viewing downstream node (or looking at the RGB/beauty)
  * Enables new "Preview" (AKA: "Keyable Surface") options
* "Preview" option provides 3 modes of visual feedback
  * "Colors" is an improved version of the old style random colors
  * "Edges" allows viewing input RGBA with borders around keyable regions
  * "None" allows viewing of input RGBA without borders, but with a visible highlight on selected areas
  * Colors now generated dynamically, removing need for preview channels
* Enhancements for multi-channel inline workflow
  * "Matte Output" knob enables output to a custom channel
  * "Remove Channels" now defaults to false
  * "Matte only" now causes mattes to be written to R, G, B, A in addition to specified output
* "Unpremultiply" option to unpremult output matte by input alpha
* Support for special characters and UTF-8
  * Support for non-ascii unicode
  * Added support names containing spaces, commas, and angle brackets
  * Switched matte lists to be YAML-style (names with special characters are enclosed in quotes)
* Added test suite
  * Added failfast with cleanup skipping to Nuke tests, to allow inspecting what went wrong
* Bug fixes
  * Mixed selections of names and raw IDs now work correctly for all cases
  * Gizmo now works when read nodes have "do not attach prefix" enabled
  * Fixed rare issue where connections were lost on script load and copy and paste when used with channelmerge
  * Fixed (Beta only) bug Encryptomatte retains its layer selection properly
  * Fixed (Beta only) bug with PickerAdd and PickerRemove values stored in files
  * Fixed (Beta only) bug with errors on load with invalid Cryptomatte

Fusion (by C&eacute;dric Duriau)

* Minimum Fusion version is now 9.0.1.
  * Redesigned around new Fusion 9.0.1 features
  * Fuse now loads EXRs directly via the EXRIO module
  * For older versions, please use an older release (see GitHub releases)
* Added support for sidecar manifests
* Added layer selection slider with layer name display
* Added "Preview" (AKA "Keyable Surface") options
  * Colors now generated dynamically, removing need for preview channels
* Added shortcut configuration file ("cryptomatte_shortcut.fu")
  * Added "Toggle" button acting as a Add/Remove switch (Shift+T)
* Added support special characters in selection lists
  * Known limitation: Commas in names are not yet supported
* Performance Improvements
  * Optimized multi threaded functions
* Added Support for mixed depth EXR images
* Added Support for proxy mode
* Using EXRIO module
  * Removed loader channel slots workaround
  * Removed "Update Loader" button
  * No longer limited to 8 cryptomatte ranks
* Bug fixes
  * Improved "matte only" previewing
  * Keyable surface feature disabled when in matte only mode
* Code improvements
  * Added version to file headers
  * Added "cryptomatte_utilities.lua" module
  * Added docstrings
  * Removed simplejson.lua module, using builtin dkjson module
  * Removed "struct.lua" dependency

### 1.1.4: 

* Fixes Fusion crash when rendering with FusionRenderConsole

### 1.1.3:

* Adds beta version of Fusion support, also by C&eacute;dric Duriau and Kristof Indeherberge at Grid.
  * Major tool connection workflow improvement. No longer requires multiple loaders to work, instead populates single loader channel slots when viewed. 

### 1.1.2:

* Adds alpha version of Fusion support, created by C&eacute;dric Duriau and Kristof Indeherberge at Grid.

### 1.1.1:

* Store channels on hidden knobs on Cryptomatte gizmo and decryptomatte expression nodes
  * Fixes expression node errors in batch mode
* No longer prompts users on "decryptomatte selected"
  * Allow API users to use decryptomatte without prompt
* Fixed error when loading gizmo in Nuke 7

### 1.1.0:

* Changes to specification regarding storage of metadata
* Enabled Nuke code to read this metadata
  * (1.1.0 Nuke plugin is compatible with older Cryptomattes)
* No longer raises errors if no metadata is available (would happen in batch mode)
* No longer raises errors if picker in is in single value mode rather than RGB

### 1.0.2:

* Updated pymmh3 to output signed ints, in compliance with mmh3

### 1.0.1: 

* Added layer selection to gizmo and utilities (backwards compatible)
* Added menu.py
* Added `__version__` to cryptomatte_utilities.py
* Bug fix - invalid manifest broke keying

### 1.0.0: 

* Initial release of Nuke plugins, specification, and sample images.