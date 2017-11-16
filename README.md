![Cryptomatte Logo](/docs/header.png)

Cryptomatte is a tool created at Psyop by Jonah Friedman and Andy Jones. It creates ID mattes automatically with support for motion blur, transparency, and depth of field, using organizational information already available at render time. This organizational information is usually names, object namespaces, and material names.

* Demo video: [https://vimeo.com/136954966](https://vimeo.com/136954966)
* Poster: [https://github.com/Psyop/Cryptomatte/raw/master/specification/IDmattes_poster.pdf](https://github.com/Psyop/Cryptomatte/raw/master/specification/IDmattes_poster.pdf)

The goal of releasing Cryptomatte is to turn it into an ecosystem around an open standard. Any developers who wish to make plugins are welcome and encouraged to create tools that inter-operate with the components we are providing. We hope to see a diverse ecosystem of renderers that can create Cryptomatte images and plugins for compositing applications to decode them.

## License

Cryptomatte is licenced using the BSD 3-clause license. See [license.txt](license.txt).

## Repo Contents

The contents of this repository are:

**Nuke:** This contains Python files, an image, and a gizmo. Together these are our implementation for The Foundry's Nuke.

**Fusion:** Fusion integration, including a Fuse and Lua scripts

**Sample Images:** These example Cryptomatte images can be used for testing your Nuke installation, or for testing other implimentations. 

**Specification:** This is a technical document describing the Cryptomatte standard. It specifies how Cryptomattes are structured, encoded, and decoded. It also contains our SIGGRAPH 2015 poster on the subject.

## Implementations

A list of released implementations and links:

Encoders:

* [Isotropix Clarisse 3.5 (By Isotropix)](http://www.isotropix.com/products/clarisse-3.5) [Demo](https://www.youtube.com/watch?v=V_ov8B24jq0)
* [Chaos Group V-Ray 3.6 (By Chaos Group)](https://docs.chaosgroup.com/display/VRAY3MAX/Cryptomatte+%7C+VRayCryptomatte) [3DSMax demo](https://www.youtube.com/watch?v=tlahITki4xg) [Maya demo](https://www.youtube.com/watch?v=iVHcuke_aWk) [Nuke demo](https://www.youtube.com/watch?v=Vb4OX7UNIMw)
* [3Delight for Katana and Maya 9.0](https://3delight.atlassian.net/wiki/spaces/3DFK/pages/220135565/Exporting+CryptoMatte+IDs)
* [Houdini 16.5 Mantra (By Sidefx)](http://www.sidefx.com/docs/houdini/render/cryptomatte.html) [Demo](https://vimeo.com/241036613#t=2862s)
* Blender Cycles (By Tangent Animation and Blender Foundation): [Demo](https://www.youtube.com/watch?v=_2Ia4h8q3xs) [Build](https://twitter.com/stefan_3d/status/928556500045516800)
* [Arnold 4 (AlShaders), by Jonah Friedman, Andy Jones, Anders Langlands.](http://www.anderslanglands.com/alshaders/index.html)
* [Arnold 5 (AlShaders 2), by Jonah Friedman, Andy Jones, Anders Langlands.](https://github.com/anderslanglands/alShaders2)
* Nuke 7+ "Encryptomatte", by Andy Jones. In this repo.

Decoders:

* Nuke 7+, by Jonah Friedman, Andy Jones. In this repo.
* Fusion: by C&eacute;dric Duriau and Kristof Indeherberge at Grid. In this repo.
* [Houdini 16.5 Compositor (By Sidefx)](http://www.sidefx.com/docs/houdini/render/cryptomatte.html) [Demo](https://vimeo.com/241036613#t=2862s)
* Blender Compositor (By Tangent Animation and Blender Foundation): [Demo](https://www.youtube.com/watch?v=_2Ia4h8q3xs) [Build](https://twitter.com/stefan_3d/status/928556500045516800)

## Acknowledgements 

* Anders Langlands
* Alon Gibli
* Jean-Francois Panisset
* Psyop
* Solid Angle
* All the members of the Cryptomatte Committee
* Benoit Leveau
* C&eacute;dric Duriau
* Kristof Indeherberge
* Vladimir Koylazov
* Peter Loveday
* Andrew Hazelden

## Release Notes

1.2.0:

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

1.1.4: 

* Fixes Fusion crash when rendering with FusionRenderConsole

1.1.3:

* Adds beta version of Fusion support, also by C&eacute;dric Duriau and Kristof Indeherberge at Grid.
  * Major tool connection workflow improvement. No longer requires multiple loaders to work, instead populates single loader channel slots when viewed. 

1.1.2:

* Adds alpha version of Fusion support, created by C&eacute;dric Duriau and Kristof Indeherberge at Grid.

1.1.1:

* Store channels on hidden knobs on Cryptomatte gizmo and decryptomatte expression nodes
  * Fixes expression node errors in batch mode
* No longer prompts users on "decryptomatte selected"
  * Allow API users to use decryptomatte without prompt
* Fixed error when loading gizmo in Nuke 7

1.1.0:

* Changes to specification regarding storage of metadata
* Enabled Nuke code to read this metadata
  * (1.1.0 Nuke plugin is compatible with older Cryptomattes)
* No longer raises errors if no metadata is available (would happen in batch mode)
* No longer raises errors if picker in is in single value mode rather than RGB


1.0.2:

* Updated pymmh3 to output signed ints, in compliance with mmh3


1.0.1: 

* Added layer selection to gizmo and utilities (backwards compatible)
* Added menu.py
* Added `__version__` to cryptomatte_utilities.py
* Bug fix - invalid manifest broke keying

1.0.0: 

* Initial release of Nuke plugins, specification, and sample images.

## Nuke Installation

1. Download the entire Cryptomatte GitHub repository using the green "Clone or download" button. Select "Download Zip" and then extract the contents.
2. Copy the contents of the "nuke" folder from Cryptomatte into a folder in your Nuke plugin path, such as your home directory's ".nuke" folder.
3. If the destination folder already contains an "init.py" and/or "menu.py" file, open those files in a text editor, and append the contents of the Cryptomatte "init.py" and "menu.py" to those files.
4. After launching Nuke, if you've installed the plugin correctly you should be able to tab-create a Cryptomatte gizmo.

For more information on installing Nuke plugins, see:

[https://www.thefoundry.co.uk/products/nuke/developers/105/pythondevguide/installing_plugins.html](https://www.thefoundry.co.uk/products/nuke/developers/105/pythondevguide/installing_plugins.html)

To test the functionality, you can try loading one of the sample images supplied. Load the sample images into Nuke, select one of them, and tab-create the gizmo. Viewing the output of the gizmo should show you a preview of the available mattes. Use the color knob, "Picker Add" to eye-dropper colors on the image to create your mattes.

## Nuke Usage

![Cryptomatte in Nuke](/docs/nukeScreenshot.jpg)

To get started: 

1. Load a Cryptomatte exr file, such as the sample images, using a Read node.
2. Select it, and tab create a Cryptomatte gizmo.
3. View the output of the gizmo. You should see a preview image (pictured).
4. Use the eyedropper with the 'Picker Add' knob to select objects. They should light up in RGB, and output the matte in Alpha. With the eyedropper, make sure you use control-click and not alt-control click.

### Cryptomatte Gizmo

![Cryptomatte Gizmo Properties in Nuke](/docs/gizmoProperties.png)

Psyop Cryptomatte Tab:

* Picker Add: This adds "keyed" objects to the matte selection, meant to be used with Nuke's eyedropper.
* Picker Remove: This removes "keyed" objects from the matte selection, meant to be used with Nuke's eyedropper.
* Preview: Controls whether or not previews of the matte boundaries are drawn. A pulldown controls how they are drawn.
  * "Edges" allows viewing input RGBA with borders around keyable regions
  * "Colors" is random colors per matte
  * "None" allows viewing of input RGBA without borders, but with a visible highlight on selected areas
* Matte Only: Also write the matte to RGBA channels
* Single Selection: Changes the gizmo behavior so that only one object may be selected at a time.
* Remove Channels: Removes the Cryptomatte channels so that downstream of the gizmo, the additional channels are not present.
* Matte Output: Which channel the extracted matte is written to.
* Unpremultiply: Unpremults the extracted matte against by the alpha.
* Matte List: A list of names to extract mattes from. This list may be modified in text form or using the Picker color knobs.
* Clear: Clears the matte list.
* Force Update: The python scripts keep Cryptomatte gizmos updated when inputs or relevant knobs are changed. If there's a case that it does not update, this button will manually update it.
* Stop Auto Update: Stops the automatic updating described above.
* Layer Selection: If there are multiple Cryptomattes, this is how you select the layer. This is filled in automatically, but may be changed manually.
* Lock Layer Selection: Stops the automatic updating of layer selection, which occurs if the specified selection is not available.
* Expression: Internally the gizmo generates an expression to extract the matte. The expression is saved here.

Advanced Tab:

* Decryptomatte: Replaces gizmo with equivalent nodes
* Unload Manifest: Generates a keyer for every name in the manifest.
* Force Update All Gizmos in Script: Same as "Force Update", but runs the force update functionality on all Gizmos in the script.

### Encryptomatte Gizmo

![Encryptomatte Gizmo Properties in Nuke](/docs/encryptomatteProperties.png)

Encryptomatte is a gizmo that can modify existing Cryptomattes, or start new ones. One Encryptomatte node adds one matte to a Cryptomatte.

To get started:

1. Load a Cryptomatte with a read node. 
2. Select it, and tab-create an Encryptomatte. 
3. Feed in a matte that you would like to add to that Cryptomatte. You can put it over or under all other mattes.
4. Write it out as a 32 bit EXR with all metadata, or attach a Cryptomatte node to it to test the mattes.

Encryptomatte tab:

* Matte Name: The name your new matte will have in the Cryptomatte
* Merge Operation: Where in the stack of mattes your matte will be added, over or under the rest
* Layer selection: Same as Cryptomatte, see above.
* Force Update: Same as Cryptomatte, see above.
* Layers: If starting a fresh Cryptomatte, sets how many Cryptomatte layers are to be created. If starting from scratch, fill in Layer Selection manually.
* Setup Layers: If on, starts a fresh Cryptomatte. Otherwise, modifies one from the input.

### Menu options

* Cryptomatte: Creates a Cryptomatte gizmo
* Decryptomatte All: Replaces all Cryptomatte gizmos with other nodes which are functionally equivalent. This is useful for sending nuke scripts to other users who do not have the Cryptomatte plugins installed.
* Decryptomatte Selected: Same as "decryptomatte all", except only applies to selected nodes. 
* Encryptomatte: Creates an Encryptomatte gizmo

### Troubleshooting

For common issues, see [troubleshooting.](troubleshooting.md)

### Testing (developers)

Nuke Cryptomatte has a suite of unit and integration tests. These cover hashing, CSV resolution, operations of the Cryptomatte and Encryptomatte gizmos, and Decryptomatte. Use of these is strongly encouraged if working with the Cryptomatte code.

```
# To run tests in an ad-hoc style in a Nuke session, in the script editor: 
import cryptomatte_utilities as cu
cu.tests.run_nuke_tests()
```

Tests require the provided `sample_images` directory. If it is not located in the default location relative to the Python files, its location may be specified using an env variable, `$CRYPTOMATTE_TESTING_SAMPLES`. This can also be done ad-hoc in Nuke prior to running tests:

```
import os
os.environ["CRYPTOMATTE_TESTING_SAMPLES"] = "" #  < specify sample_images dir here
```

## Fusion Installation

1. Download the entire Cryptomatte GitHub repository using the green "Clone or download" button. Select "Download Zip" and then extract the contents.
2.  Copy the `fusion/cryptomatte_utilities.lua` module into the standard Fusion Lua "package.path" location. The Lua modules can also be added to a folder that is listed in your `LUA_PATH` based environment variable.
    * Windows : `C:\Program Files\Blackmagic Design\Fusion 9\lua`
    * Linux : `/usr/local/share/lua/5.1/`
    * Mac : `/usr/local/share/lua/5.1/`
3. Copy the `fusion/cryptomatte.fuse` file into the Fusion user preferences based `Fuses:/` PathMap directory, or the "Fuses" subfolder in the Fusion installation folder.
    * Windows : `C:\Program Files\Blackmagic Design\Fusion 9\Fuses\`
    * Linux : `/opt/BlackmagicDesign/Fusion9/Fuses/`
    * Mac : `/Applications/Blackmagic Fusion 9/Fusion.app/Contents/MacOS/Fuses/`
4. Copy the `fusion/cryptomatte_hotkeys.fu` file into the Fusion user preferences based `Config:/` PathMap directory.
    * Windows : `%APPDATA%\Blackmagic Design\Fusion 9\Config\`
    * Linux : `/opt/BlackmagicDesign/Fusion9/Config/`
    * Mac : `/Applications/Blackmagic Fusion 9/Fusion.app/Contents/MacOS/Config/`

### Fusion Usage:

![Cryptomatte for Fusion](/docs/fusionScreenshot.png)

The Cryptomatte Fuse works in Fusion (Free) and Fusion Studio v9.0.1+. The Fuse allows you to create matte selections using a Cryptomatte "Matte Locator" control that is positioned using transform control the Fusion Viewer window.

To get started:

1. Add a Cryptomatte exr file to your composite, such as the sample images, using a Loader node. 
2. Select the Loader node and use the Select Tool window (Shift + Spacebar) to add a new Cryptomatte node to your composite.
3. Select the Cryptomatte node in the Flow area and display the output in a Viewer window.
4. Position the Cryptomatte "Matte Locator" control in the Viewer window over an object in the frame.
5. Press the "Add" button in the Cryptomatte Tools view to add a new matte entry to the Matte List. Alternatively, you could press the "Shift + T" hotkey in the Fusion Viewer window to toggle the active Cryptomatte "Matte Locator" state between the "Add" and "Remove" selection modes.

### Cryptomatte Fuse

![Cryptomatte for Fusion Tools View](/docs/fusionToolsView.png)
