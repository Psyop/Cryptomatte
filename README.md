![Cryptomatte Logo](/docs/header.png)

Cryptomatte is a tool created at Psyop by Jonah Friedman and Andy Jones. It creates ID mattes automatically with support for motion blur, transparency, and depth of field, using organizational information already available at render time. This organizational information is usually names, object namespaces, and material names.

* Demo video: [https://vimeo.com/136954966](https://vimeo.com/136954966)
* Poster: [https://github.com/Psyop/Cryptomatte/raw/master/specification/IDmattes_poster.pdf](https://github.com/Psyop/Cryptomatte/raw/master/specification/IDmattes_poster.pdf)

The goal of releasing Cryptomatte is to turn it into an ecosystem around an open standard. Any developers who wish to make plugins are welcome and encouraged to create tools that inter-operate with the components we are providing. We hope to see a diverse ecosystem of renderers that can create Cryptomatte images and plugins for compositing applications to decode them.

Cryptomatte is licenced using the BSD 3-clause license. See [license.txt](license.txt).

Version 1.2.4. See [changelog](CHANGELOG.md) for version history. 

## Repo Contents

The contents of this repository are:

**Nuke:** This contains Python files, an image, and a gizmo. Together these are our implementation for The Foundry's Nuke.

**Fusion:** Fusion integration, including a Fuse file, a Lua module and a Fusion shortcut configuration file.

**Sample Images:** These example Cryptomatte images can be used for testing your Nuke installation, or for testing other implimentations. 

**Specification:** This is a technical document describing the Cryptomatte standard. It specifies how Cryptomattes are structured, encoded, and decoded. It also contains our SIGGRAPH 2015 poster on the subject.

## Documentation

* [Nuke Documentation](/docs/nuke.md) - Installation, usage instructions, troubleshooting
* [Fusion Documentation](/docs/fusion.md) - Installation, usage instructions

## Implementations

A list of released implementations and links:

Encoders:

* [Isotropix Clarisse 3.5 (By Isotropix)](http://www.isotropix.com/products/clarisse-3.5), [Demo](https://www.youtube.com/watch?v=V_ov8B24jq0)
* [Chaos Group V-Ray 3.6 (By Chaos Group)](https://docs.chaosgroup.com/display/VRAY3MAX/Cryptomatte+%7C+VRayCryptomatte), [3DSMax demo](https://www.youtube.com/watch?v=tlahITki4xg), [Maya demo](https://www.youtube.com/watch?v=iVHcuke_aWk), [Nuke demo](https://www.youtube.com/watch?v=Vb4OX7UNIMw)
* [3Delight for Katana and Maya 9.0](https://3delight.atlassian.net/wiki/spaces/3DFK/pages/220135565/Exporting+CryptoMatte+IDs)
* [Houdini 16.5 Mantra (By Sidefx)](http://www.sidefx.com/docs/houdini/render/cryptomatte.html), [Demo](https://vimeo.com/241036613#t=2862s)
* Blender 2.8.0 Cycles (By Tangent Animation and Blender Foundation): [Cryptomatte in Blender 2.8 Alpha 2! demo](https://www.youtube.com/watch?v=lTJJqAGnWFM), [Tutorial by Zacharias Reinhardt](https://zachariasreinhardt.com/blender-2-8-cryptomatte-tutorial), [Cycles for Animated Feature Film Production by Stefan Werner](https://www.youtube.com/watch?v=_2Ia4h8q3xs), [Docs](https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Cycles#Cryptomatte)
* [Pixar RenderMan 21.7](https://rmanwiki.pixar.com/display/REN/RenderMan+21.7), [Docs](https://rmanwiki.pixar.com/display/REN/PxrCryptomatte)
* LightWave 3D 2018 ([DB&W EXRTrader plugin](https://www.db-w.com/products/exrtrader))
* [Redshift 2.6.11](https://www.redshift3d.com)
* [Arnold 4 (AlShaders), by Jonah Friedman, Andy Jones, Anders Langlands.](http://www.anderslanglands.com/alshaders/index.html)
* [Arnold 5 (AlShaders 2), by Jonah Friedman, Andy Jones, Anders Langlands.](https://github.com/anderslanglands/alShaders2)
* Nuke 7+ "Encryptomatte", by Andy Jones. In this repo.

Decoders:

* Nuke 7+, by Jonah Friedman, Andy Jones. In this repo.
* Fusion: by C&eacute;dric Duriau and Kristof Indeherberge at Grid. In this repo.
* [Houdini 16.5 Compositor (By Sidefx)](http://www.sidefx.com/docs/houdini/render/cryptomatte.html), [Demo](https://vimeo.com/241036613#t=2862s)
* Blender 2.8.0 Compositor (By Tangent Animation and Blender Foundation): [Cryptomatte in Blender 2.8 Alpha 2! demo](https://www.youtube.com/watch?v=lTJJqAGnWFM), [Tutorial by Zacharias Reinhardt](https://zachariasreinhardt.com/blender-2-8-cryptomatte-tutorial), [Cycles for Animated Feature Film Production by Stefan Werner](https://www.youtube.com/watch?v=_2Ia4h8q3xs), [Docs](https://wiki.blender.org/wiki/Reference/Release_Notes/2.80/Cycles#Cryptomatte)
* [Autodesk Flame (By Lewis Saunders)](https://logik-matchbook.org/shader/Cryptomatte)
* [After Effects (Fnordware ProEXR plugin 2.0)](https://www.fnordware.com/ProEXR/)


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
* Jens Lindgren
