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

**Fusion:** Alpha version of Fusion integration, including a Fuse and Lua scripts

**Sample Images:** These example Cryptomatte images can be used for testing your Nuke installation, or for testing other implimentations. 

**Specification:** This is a technical document describing the Cryptomatte standard. It specifies how Cryptomattes are structured, encoded, and decoded. It also contains our SIGGRAPH 2015 poster on the subject.

## Implementations

A list of released implementations and links:

Encoders:

* [Isotropix Clarisse 3.5 (By Isotropix)](http://www.isotropix.com/products/clarisse-3.5)
* [Chaos Group V-Ray 3.6 (By Chaos Group)](https://docs.chaosgroup.com/display/VRAY3MAX/Cryptomatte+%7C+VRayCryptomatte)
* [Arnold 4 (AlShaders), by Jonah Friedman, Andy Jones, Anders Langlands.]( http://www.anderslanglands.com/alshaders/index.html )
* [Arnold 5 (AlShaders 2), by Jonah Friedman, Andy Jones, Anders Langlands.]( https://github.com/anderslanglands/alShaders2 )
* Nuke 10 "Encryptomatte", by Andy Jones. In this repo. 

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

## Release Notes

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

See also: https://www.thefoundry.co.uk/products/nuke/developers/63/pythondevguide/installing_plugins.html

The files in the "nuke" folder of the repo need to be in a directory that's in your Nuke plugin path. If you are a single user, the easiest way to do this is to use the .nuke directory in your home directory. This will be referred to as the your install directory. 

Copy the files in the "nuke" directory of this repo into your install directory. These files include include an init.py and a menu.py file, special file names Nuke looks for. If your install directory already contains a init.py, open it in a text editor, and add the contents of the cryptomatte init.py to the end of the current init.py. Similarly for the menu.py file. The rest of the files, including python files, gizmos and an image should just be copied over.

After launching Nuke, if you've installed the plugin correctly you should be able to tab-create a Cryptomatte gizmo. 

You can test the rest of the functionality by loading one of the sample images supplied. Load the sample images into Nuke, select one of them, and tab-create the gizmo. Viewing the output of the gizmo should show you a 'keyable surface'. Use the color knob, "Picker Add" to eye-dropper colors on the image to create your mattes. 

## Nuke Usage

![](/docs/nukeScreenshot.jpg)

To get started: 

1. Load a Cryptomatte exr file, such as the sample images, using a Read node. 
2. Select it, and tab create a Cryptomatte gizmo. 
3. View the output of the gizmo. You should see a "keyable surface" (pictured). 
4. Use the eyedropper with the 'Picker Add' knob to select objects. They should light up in RGB, and output the matte in Alpha. With the eyedropper, make sure you use control-click and not alt-control click. 

### Cryptomatte Gizmo

![](/docs/gizmoProperties.png)

Psyop Cryptomatte Tab:
* Picker Add: This adds "keyed" objects to the matte selection, meant to be used with Nuke's eyedropper. 
* Picker Remove: This removes "keyed" objects from the matte selection, meant to be used with Nuke's eyedropper. 
* Matte Only: This changes the output of the picker to output the matte in RGB channels as well. 
* Single Selection: Changes the gizmo behavior so that only one object may be selected at a time. 
* Remove Channels: Removes the Cryptomatte channels so that downstream of the gizmo, the additional channels are not present. 
* Matte List: A list of names to extract mattes from. This list may be modified in text form or using the Picker color knobs. 
* Clear: Clears the matte list. 
* Force Update: The python scripts keep Cryptomatte gizmos updated when inputs or relevant knobs are changed. If there's a case that it does not update, this button will manually update it. 
* Stop Auto Update: Stops the automatic updating described above.
* Layer Selection: If there are multiple cryptomattes, this is how you select the layer. This is filled in automatically, but may be changed manually. 
* Lock Layer Selection: Stops the automatic updating of layer selection, which occurs if the specified selection is not available. 
* Expression: Internally the gizmo generates an expression to extract the matte. The expression is saved here. 

Advanced Tab: 
* Name Checker: Same as the picker knobs, except this allows you to key objects to see what they are, without changing your matte.
* Keyed Name: The name keyed in using the name checker. 
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
