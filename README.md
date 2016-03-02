### Cryptomatte Standards Committee ###

This repo contains code and example files for the Cryptomatte Committee. 

### Specification ###

This contains the specification for Cryptomatte in RTF format. 

### Nuke files ###

The Nuke implementation contains an init.py, cryptomatte_utilities.py which must be in the python path, and two gizmos. 

### Change Log ###

* 0.1.0: Initial commit of the specification and Nuke gizmos and plugins needed to use it. 
* 0.2.0: Switched to using MurmurHash3 in nuke scripts and example images
* 0.3.0: Changed the format of the metadata to allow multiple Cryptomattes per image and required the metadata to specify both the hash and conversion method for each of the cryptomatte types in the EXR file. Remove one of the two gizmos, updated images and nuke plugins. 
