### Cryptomatte Standards Committee ###

This repo is now transitioning into becoming the release version of the Nuke gizmo and scripts. 

### Cryptomatte ###

This is an open source release of Psyop's Cryptomatte. For users, this contains the a Nuke plugin for extracting mattes from Cryptomatte, some example images. For developers, the Nuke plugins implement the standard, and the specification and SIGGRAPH poster are supplied. 

### Nuke files ###

The Nuke implementation contains an init.py, cryptomatte_utilities.py which must be in the python path, and two gizmos.

To install:

Copy the files in the "nuke" directory of this repo into your .nuke directory. It contains python files, a gizmo, and an image. If there is already an init.py there, open it in a text editor, and add the contents of this init.py to the end of the current init.py.

After launching nuke, you should be able to tab-create a cryptomatte gizmo. 

Load the sample images into Nuke, select one of them, and tab-create the gizmo. It should show you a 'keyable surface'. Use the color knobs, "picker add" to eye-dropper colors on the image to create your mattes. 

For full documentation, see the wiki. 

### Cryptomatte Specification ###

This contains the specification for Cryptomatte in RTF format. This describes how Cryptomatte images as structured and contains code examples. 

