Cryptomatte is a tool created at Psyop by Jonah Friedman and Andy Jones. It creates ID mattes automatically with support for motion blur, transparency, and depth of field, using organizational information already available at render time. This organizational information is usually names, object namespaces, and material names. 

## About Cryptomatte

* Demo video: https://vimeo.com/136954966
* Poster: https://github.com/Psyop/cryptomatte-committee/raw/master/specification/IDmattes_poster.pdf

Cryptomattes are packaged into EXR files for cryptomattes generated from one set of names. 

The goal of releasing Cryptomatte is to turn it into an ecosystem around an open standard. Any developers who wish to make plugins are welcome and encouraged to create tools that inter-operate with the components we are providing. We hope to see a diverse ecosystem of renderers that can create Cryptomatte images and plugins for compositing applications to decode them. 

## Repo Contents

The contents of this repository are:

**Nuke:** This contains Python files, an image, and a gizmo. Together these are our implementation for The Foundry's Nuke.

**Sample Images:** These example Cryptomatte images can be used for testing your Nuke installation, or for testing other implimentations. 

**Specification:** This is a technical document describing the Cryptomatte standard. It specifies how Cryptomattes are structured, encoded, and decoded. It also contains our SIGGRAPH 2015 poster on the subject.


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

A couple of really simple things to watch out for:
* Make sure you are viewing the same Cryptomatte gizmo you're keying with. (this is a very easy mistake to make). 
* To use the eyedropper, use the control key. Do not use alt-control, which eyedroppers values from upstream of the node. Many users are in the habbit of using alt-control eye droppering.

#### Keyed mattes have incorrect pixelated edges.

Make sure there are no "Reformat" or "LensDistortion" or similar nodes applied to your Cryptomattes before trying to key them. Cryptomatte relies on exact values in channels, and operations that mix values with neighboring values will damage this information, resulting in only being able to extract mattes on pixels containing only one object. These operations should be applied to the extracted mattes instead. 

Likewise, using proxy mode gives bad results for similar reasons. 

#### Keying just selects numbers such as `<0.1234>` but nothing lights up and no mattes are created. 

Make sure your nuke viewer has "Use GPU for viewer when possible" set to off. Mouse over the viewer window and press S to get to your viewer options. If this is set to on, sometimes the values are changed by an infinitesmal amount and keying no longer works. 

Also make sure nothing upstream of the Gizmo may be changing the values of the Cryptomatte image. 

#### Things key properly, but not as their names, instead they key as numbers like `<0.1234>`

The object keyed is not in the manifest provided with this EXR file, or no manifest is provided. This is a problem on the 3D side. However, objects keyed this way will be stable and will work. 

#### I can't tab-create the Cryptomatte gizmo. 

The scripts are not installed correctly. See installation instructions. 

#### I don't get a keyable surface when I connect my gizmo to a read node. 

Try running, "Force Update". If an error dialogue box pops up, the scripts are not installed correctly. See installation instructions. 

Also, test if it works on one of the sample images. 

#### Objects under the Arnold watermark aren't keyable.

They sure aren't! 

#### I can't key the background (black pixels).

You can key the background by manaully entering the value, `<0.0>` into the matte list of the gizmo. 
