### Troubleshooting

A couple of really simple things to watch out for:
* Make sure you are viewing the same Cryptomatte gizmo you're keying with. (this is a very easy mistake to make). 
* To use the eyedropper, use the control key. Do not use alt-control, which eyedroppers values from upstream of the node. Many users are in the habbit of using alt-control eye droppering.

### Common issues

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
