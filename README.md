![](/docs/header.png)

Cryptomatte is a tool created at Psyop by Jonah Friedman and Andy Jones. It creates ID mattes automatically with support for motion blur, transparency, and depth of field, using organizational information already available at render time. This organizational information is usually names, object namespaces, and material names. 

* Demo video: https://vimeo.com/136954966
* Poster: https://github.com/Psyop/Cryptomatte/raw/master/specification/IDmattes_poster.pdf

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

* [Isotropix Clarisse 3.5 (By Isotropix)](http://www.isotropix.com/products/clarisse-3.5)
* [Chaos Group V-Ray 3.6 (By Chaos Group)](https://docs.chaosgroup.com/display/VRAY3MAX/Cryptomatte+%7C+VRayCryptomatte)
* [Arnold 4 (AlShaders), by Jonah Friedman, Andy Jones, Anders Langlands.]( http://www.anderslanglands.com/alshaders/index.html )
* [Arnold 5 (AlShaders 2), by Jonah Friedman, Andy Jones, Anders Langlands.]( https://github.com/anderslanglands/alShaders2 )
* Nuke 7+ "Encryptomatte", by Andy Jones. In this repo. 

Decoders:

* Nuke 7+, by Jonah Friedman, Andy Jones. In this repo.
* Fusion: by Cedric Duriau and Kristof Indeherberge at Grid. In this repo.

## Acknowledgements 

* Anders Langlands
* Alon Gibli
* Jean-Francois Panisset
* Psyop
* Solid Angle
* All the members of the Cryptomatte Committee
* Benoit Leveau
* Cedric Duriau
* Kristof Indeherberge
* Vladimir Koylazov
* Peter Loveday

## Release Notes

1.2.0 (Beta 5):

* Nuke - Added layer selection pulldown
* Nuke - New Eyedropper "picker" knobs which use picker position and not sampled values
  * No longer use Color knob's built in picker
  * Fixed keying problems sometimes caused by GPU-enabled viewers
  * Can pick mattes while viewing downstream node (or looking at the RGB/beauty)
  * Enables new "Preview" (AKA: "Keyable Surface") options
* Nuke - "Preview" option provides 3 modes of visual feedback
  * "Colors" is an improved version of the old style random colors
  * "Edges" allows viewing input RGBA with borders around keyable regions
  * "None" allows viewing of input RGBA without borders, but with a visible highlight on selected areas
  * Colors now generated dynamically, removing need for preview channels
* Nuke - Enhancements for multi-channel inline workflow
  * "Matte Output" knob enables output to a custom channel
  * "Remove Channels" now defaults to false
  * "Matte only" now causes mattes to be written to R, G, B, A in addition to specified output
* Nuke - "Unpremultiply" option to unpremult output matte by input alpha
* Nuke - Bug fixes
  * Mixed selections of names and raw IDs now work correctly for all cases
  * Encryptomatte retains its layer selection properly
* Nuke - Added unit tests and integration tests. 
* Fusion
  * Added cryptomatte_utilities.lua module
  * Removed simplejson.lua module, using builtin dkjson module
  * Added layer selection slider with layer name display
  * Added "Preview" (AKA "Keyable Surface") options
  * Colors now generated dynamically, removing need for preview channels
  * Implemented EXRIO to read exr channel data
  * Removed "Update Loader" button
  * Removed loader channel slots workaround
  * No longer limited to 8 ranks
  * Improved matte only previewing
  * Optimized multi threaded functions
  * Added docstrings

1.2.0 (Beta 4):

* Fusion - Support for names containing special characters in selection lists
* Fusion - Known limitation: Commas in names are not yet supported. 

1.2.0 (Beta 3):

* Fusion - Support for sidecar manifests
* Fixed updating issue when connecting fuse to different cryptomatte types
* Performance improvements in Fusion

1.2.0 (Beta 2):

* Removed dependency of yaml
* Added some testing utility functions to cryptomatte_utilities.py

1.2.0 (Beta!):

* Changed specification regarding sidecar manifests, such that they are always sidecars with relative paths. 
* Supported sidecar files in Nuke plugin
* Support for UTF-8 Characters in Nuke plugin and specification
* Encryptomatte for modifying or creating Cryptomattes in Nuke
* Support names containing spaces, commas, and angle brackets. 
  * Switched matte lists to be yaml-style. This mainly effects names containing spaces, commas, or quotes. 
  * Names with special character (or names that look like numbers) will be enclosed in quotes. 

1.1.4: 

* Fixes Fusion crash when rendering with FusionRenderConsole

1.1.3:

* Adds beta version of Fusion support, also by Cedric Duriau and Kristof Indeherberge at Grid. 
  * Major tool connection workflow improvement. No longer requires multiple loaders to work, instead populates single loader channel slots when viewed. 

1.1.2:

* Adds alpha version of Fusion support, created by Cedric Duriau and Kristof Indeherberge at Grid. 

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
* Added `__version__` to cryptomatte_utilities
* Bug fix - invalid manifest broke keying

1.0.0: 

* Initial release of Nuke plugins, specification, and sample images.

## Nuke Installation

1. Download the entire Cryptomatte GitHub repository using the green “Clone or download” button. Select “Download Zip” and then extract the contents.
2. Copy the contents of the “nuke” folder from Cryptomatte into a folder in your Nuke plugin path, such as your home directory’s “.nuke” folder.
3. If the destination folder already contains an “init.py” and/or “menu.py” file, open those files in a text editor, and append the contents of the Cryptomatte “init.py” and “menu.py” to those files.
4. After launching Nuke, if you've installed the plugin correctly you should be able to tab-create a Cryptomatte gizmo.

For more information on installing Nuke plugins, see: https://www.thefoundry.co.uk/products/nuke/developers/70/pythondevguide/installing_plugins.html

To test the functionality, you can try loading one of the sample images supplied. Load the sample images into Nuke, select one of them, and tab-create the gizmo. Viewing the output of the gizmo should show you a preview of the available mattes. Use the color knob, "Picker Add" to eye-dropper colors on the image to create your mattes.

## Nuke Usage

![](/docs/nukeScreenshot.jpg)

To get started: 

1. Load a Cryptomatte exr file, such as the sample images, using a Read node. 
2. Select it, and tab create a Cryptomatte gizmo. 
3. View the output of the gizmo. You should see a preview image (pictured). 
4. Use the eyedropper with the 'Picker Add' knob to select objects. They should light up in RGB, and output the matte in Alpha. With the eyedropper, make sure you use control-click and not alt-control click. 

### Cryptomatte Gizmo

![](/docs/gizmoProperties.png)

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
* Decryptomatte: Replaces gizmo with equivelant nodes
* Unload Manifest: Generates a keyer for every name in the manifest. 
* Force Update All Gizmos in Script: Same as "Force Update", but runs the force update functionality on all Gizmos in the script. 

### Encryptomatte Gizmo

![](/docs/encryptomatteProperties.png)

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

Nuke Cryptomatte has a suite of unit and integration tests. These cover hashing, CSV resolution, operations of the Cryptomatte and Encryptomatte gizmos, and decryptomatte. Use of these is strongly encouraged if working with the Cryptomatte code.  

```
# To run tests in an ad-hoc style in a Nuke session, in the script editor: 
import cryptomatte_utilities as cu
cu.tests.run_nuke_tests()
```

Tests require the provided sample_images directory. If it is not located in the default location relative to the Python files, its location may be specified using an env variable, $CRYPTOMATTE_TESTING_SAMPLES. This can also be done ad-hoc in Nuke prior to running tests:

```
import os
os.environ["CRYPTOMATTE_TESTING_SAMPLES"] = "" #  < specify sample_images dir here
```

## Fusion Installation

1. Download the entire Cryptomatte GitHub repository using the green “Clone or download” button. Select “Download Zip” and then extract the contents.
2. Copy the fusion/cryptomatte.fuse file into one of the directories mentioned in Fusion's Path Map for Fuses.
3. Create a "lua" directory in the install root of Fusion and paste all the fusion/*.lua modules in this directory.