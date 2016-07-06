![](/docs/header.png)

Cryptomatte is a tool created at Psyop by Jonah Friedman and Andy Jones. It creates ID mattes automatically with support for motion blur, transparency, and depth of field, using organizational information already available at render time. This organizational information is usually names, object namespaces, and material names. 

* Demo video: https://vimeo.com/136954966
* Poster: https://github.com/Psyop/Cryptomatte/raw/master/specification/IDmattes_poster.pdf

Cryptomattes are packaged into EXR files for Cryptomattes generated from one set of names. 

The goal of releasing Cryptomatte is to turn it into an ecosystem around an open standard. Any developers who wish to make plugins are welcome and encouraged to create tools that inter-operate with the components we are providing. We hope to see a diverse ecosystem of renderers that can create Cryptomatte images and plugins for compositing applications to decode them. 

## License

Cryptomatte is licenced using the BSD 3-clause license. See [license.txt](license.txt). 

## Repo Contents

The contents of this repository are:

**Nuke:** This contains Python files, an image, and a gizmo. Together these are our implementation for The Foundry's Nuke.

**Sample Images:** These example Cryptomatte images can be used for testing your Nuke installation, or for testing other implimentations. 

**Specification:** This is a technical document describing the Cryptomatte standard. It specifies how Cryptomattes are structured, encoded, and decoded. It also contains our SIGGRAPH 2015 poster on the subject.

## Acknowledgements 

* Anders Langlands
* Alon Gibli
* Jean-Francois Panisset
* Psyop
* Solid Angle
* All the members of the Cryptomatte Committee

## Nuke Installation

See also: https://www.thefoundry.co.uk/products/nuke/developers/63/pythondevguide/installing_plugins.html

The files in the "nuke" folder of the repo need to be in a directory that's in your Nuke plugin path. If you are a single user, the easiest way to do this is to use the .nuke directory in your home directory. This will be referred to as the your install directory. 

Copy the files in the "nuke" directory of this repo into your install directory. These files include include an init.py file, a special file name Nuke looks for. If your install directory already contains one, open it in a text editor, and add the contents of the cryptomatte init.py to the end of the current init.py. The rest of the files, including python files, gizmos and an image should just be copied over.

After launching Nuke, if you've installed the plugin correctly you should be able to tab-create a Cryptomatte gizmo. 

You can test the rest of the functionality by loading one of the sample images supplied. Load the sample images into Nuke, select one of them, and tab-create the gizmo. Viewing the output of the gizmo should show you a 'keyable surface'. Use the color knob, "Picker Add" to eye-dropper colors on the image to create your mattes. 

## Nuke Usage

![](/docs/nukeScreenshot.jpg)

To get started: 
1. Load a Cryptomatte exr file, such as the sample images, using a Read node. 
2. Select it, and tab create a Cryptomatte gizmo. 
2. View the output of the gizmo. You should see a "keyable surface" (pictured). 
3. Use the eyedropper with the 'Picker Add' knob to select objects. They should light up in RGB, and output the matte in Alpha. With the eyedropper, make sure you use control-click and not alt-control click. 

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
* Expression: Internally the gizmo generates an expression to extract the matte. The expression is saved here. 

Advanced Tab: 
* Name Checker: Same as the picker knobs, except this allows you to key objects to see what they are, without changing your matte.
* Keyed Name: The name keyed in using the name checker. 
* Unload Manifest: Generates a keyer for every name in the manifest. 
* Force Update All Gizmos in Script: Same as "Force Update", but runs the force update functionality on all Gizmos in the script. 

### Menu options

* Cryptomatte: Creates a Cryptomatte gizmo
* Decryptomatte All: Replaces all Cryptomatte gizmos with other nodes which are functionally equivalent. This is useful for sending nuke scripts to other users who do not have the Cryptomatte plugins installed. 
* Decryptomatte Selected: Same as "decryptomatte all", except only applies to selected nodes. 

### Troubleshooting

For common issues, see [troubleshooting.](troubleshooting.md)