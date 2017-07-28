#
#
#  Copyright (c) 2014, 2015, 2016 Psyop Media Company, LLC
#  See license.txt
#
#

__version__ = "1.2.0-beta4"

GIZMO_CHANNEL_KNOBS = ["previewChannel", "in00", "in01", "in02", "in03", "in04", "in05", "in06", "in07"]
GIZMO_REMOVE_CHANNEL_KNOBS = ["removePreviewChannel", "remove00", "remove01", "remove02", "remove03", "remove04", "remove05", "remove06", "remove07"]
GIZMO_ADD_CHANNEL_KNOBS = ["addPreviewChannel", "add00", "add01", "add02", "add03", "add04", "add05", "add06", "add07"]

CRYPTOMATTE_METADATA_PREFIX = "exr/cryptomatte/"

import nuke
import struct

def setup_cryptomatte_ui():
    if nuke.GUI:
        toolbar = nuke.menu("Nodes")
        automatte_menu = toolbar.addMenu("Cryptomatte", "cryptomatte_logo.png",index=-1)
        automatte_menu.addCommand("Cryptomatte", "import cryptomatte_utilities as cu; cu.cryptomatte_create_gizmo();")
        automatte_menu.addCommand("Decryptomatte All", "import cryptomatte_utilities as cu; cu.decryptomatte_all();")
        automatte_menu.addCommand("Decryptomatte Selection", "import cryptomatte_utilities as cu; cu.decryptomatte_selected();")
        automatte_menu.addCommand("Encryptomatte", "import cryptomatte_utilities as cu; cu.encryptomatte_create_gizmo();")

def setup_cryptomatte():
    nuke.addKnobChanged(lambda: cryptomatte_knob_changed_event(
        nuke.thisNode(), nuke.thisKnob()), nodeClass='Cryptomatte')
    nuke.addKnobChanged(lambda: encryptomatte_knob_changed_event(
        nuke.thisNode(), nuke.thisKnob()), nodeClass='Encryptomatte')
    nuke.addOnCreate(lambda: encryptomatte_on_create_event(
        nuke.thisNode(), nuke.thisKnob()), nodeClass='Encryptomatte')


#############################################
# Hash to float
#############################################

try:
    # try with a fast c-implementation, if available ...
    import mmh3 as mmh3
except ImportError:
    # ... otherwise fallback to the pure python version
    import pymmh3 as mmh3


def mm3hash_float(name):
    hash_32 = mmh3.hash(name)
    if hash_32 < 0:
        hash_32 = (-hash_32 - 1) ^ 0xFFFFFFFF

    mantissa = hash_32 & ((1 << 23) - 1)
    exp = (hash_32 >> 23) & ((1 << 8) - 1)
    exp = max(exp, 1)
    exp = min(exp, 254)
    exp =  exp << 23
    sign = (hash_32 >> 31)
    float_bits = exp | mantissa
    packed = struct.pack('=I', float_bits)
    packed = '\0' * (4 - len(packed)) + packed     # packed must be exactly 4 long
    if sign == 1:
        return -struct.unpack('=f', packed)[0]
    elif sign == 0:
        return struct.unpack('=f', packed)[0]


def single_precision(float_in):
    import array
    return array.array("f", [float_in])[0]


def id_to_rgb(id):
    # This takes the hashed id and converts it to a preview color

    import ctypes
    bits = ctypes.cast(ctypes.pointer(ctypes.c_float(id)), ctypes.POINTER(ctypes.c_uint32)).contents.value

    mask = 2 ** 32 - 1
    return [0.0, float((bits << 8) & mask) / float(mask), float((bits << 16) & mask) / float(mask)]

def id_to_hex(id):
    return "{0:08x}".format(struct.unpack('<I', struct.pack('<f', id))[0])

def layer_hash(layer_name):
    return id_to_hex(mm3hash_float(layer_name))[:-1]

#############################################
# Cryptomatte file processing
############################################# 

global g_cryptomatte_manf_from_names
global g_cryptomatte_manf_from_IDs

g_cryptomatte_manf_from_names = {}
g_cryptomatte_manf_from_IDs = {}


class CryptomatteInfo(object):
    def __init__(self, node_in):
        """Take a nuke node, such as a read node or a Cryptomatte gizmo,
        and Reformat metadata into a dictionary, and collect channel
        information."""
        self.cryptomattes = {}
        self.nuke_node = node_in
        self.selection = None
        self.filename = None

        if not node_in:
            return

        exr_metadata_dict = node_in.metadata() or {}

        #prefix = "exr/cryptomatte/"
        default_selection = None
        for key, value in exr_metadata_dict.iteritems():
            if key == "input/filename":
                self.filename = value
            if not key.startswith(CRYPTOMATTE_METADATA_PREFIX): 
                continue
            numbered_key = key[len(CRYPTOMATTE_METADATA_PREFIX):] # ex: "exr/cryptomatte/ae93ba3/name" --> "ae93ba3/name"
            metadata_id = numbered_key.split("/")[0]  # ex: "ae93ba3/name" --> ae93ba3
            partial_key = numbered_key.split("/")[1]  # ex: "ae93ba3/name" --> "name"
            if metadata_id not in self.cryptomattes:
                self.cryptomattes[metadata_id] = {}
            self.cryptomattes[metadata_id][partial_key] = value

            if default_selection is None:
                default_selection = metadata_id

        for metadata_id, value in self.cryptomattes.iteritems():
            name = value.get("name", "") 
            channels = self._identify_channels(name)
            self.cryptomattes[metadata_id]["channels"] = channels

        self.selection = default_selection

        if self.nuke_node.Class() == "Cryptomatte":
            selection_name = node_in.knob("cryptoLayer").getValue()
            if not selection_name:
                return

            valid_selection = self.set_selection(selection_name)
            if not valid_selection and not self.nuke_node.knob("cryptoLayerLock").getValue():
                self.selection = default_selection

    def is_valid(self):
        """Checks that the selection is valid."""
        if self.selection is None:
            return False
        if self.selection not in self.cryptomattes:
            return False
        if "channels" not in self.cryptomattes[self.selection]:
            return False
        if len(self.cryptomattes[self.selection]["channels"]) < 2:
            return False
        return True

    def set_selection(self, selection):
        """ sets the selection (eg. cryptoObject) based on the name. 
        Returns true if successful. 
        """
        for num in self.cryptomattes:
            if self.cryptomattes[num]["name"] == selection:
                self.selection = num
                return True
        self.selection = None
        return False

    def get_selection_metadata_key(self, key):
        return CRYPTOMATTE_METADATA_PREFIX + self.selection + "/" + key

    def get_cryptomatte_names(self):
        """ gets the names of the cryptomattes contained the file, which
        are the possible selections or cryptomatte channels.
        """
        return [self.cryptomattes[x]["name"] for x in self.cryptomattes]

    def get_channels(self):
        return self.cryptomattes[self.selection]["channels"]

    def _identify_channels(self, name):
        """from a name like "cryptoObject", 
        gets sorted channels, such as cryptoObject, cryptoObject00, cryptoObject01
        """

        channel_list = []
        if self.nuke_node.Class() in ["Cryptomatte", "Encryptomatte"]:
            # nuke_node is a keyer gizmo or encryptomatte gizmo
            channel_list = self.nuke_node.node('Input1').channels()
        else:
            # nuke_node might a read node
            channel_list = self.nuke_node.channels()

        relevant_channels = [x for x in channel_list if x.startswith(name)]
        pure_channels = []
        for channel in relevant_channels:
            suffix = ".red"
            if not channel.endswith(suffix):
                continue
            # to do: validate this somewhere else
            pure_channel = channel[:-len(suffix)]
            pure_channels.append(pure_channel)

        return sorted(pure_channels)

    def resolve_manifest_paths(self, exr_path, sidecar_path):
        import os
        if "\\" in sidecar_path:
            print "Cryptomatte: Invalid sidecar path (Back-slashes not allowed): ", sidecar_path
            return "" # to enforce the specification. 
        joined = os.path.join(os.path.dirname(exr_path), sidecar_path)
        return os.path.normpath(joined)

    def parse_manifest(self):
        """ Loads json manifest and unpacks hex strings into floats,
        and converts it to two dictionaries, which map IDs to names and vice versa.
        Also caches the last manifest in a global variable so that a session of selecting
        things does not constantly require reloading the manifest (' ~0.13 seconds for a 
        32,000 name manifest.')
        """
        import json
        import struct
        import os

        num = self.selection
        manifest = {}

        manif_file = self.cryptomattes[num].get("manif_file", "")
        if manif_file:
            manif_file = self.resolve_manifest_paths(self.filename, manif_file)

        if manif_file:
            if os.path.exists(manif_file):
                try:
                    with open(manif_file) as json_data:
                        manifest = json.load(json_data)
                except:
                    print "Cryptomatte: Unable to parse manifest, ", manif_file
            else:
                print "Cryptomatte: Unable to find manifest file: ", manif_file
        else:
            try:
                manifest = json.loads(self.cryptomattes[num].get("manifest", "{}"))
            except:
                pass

        from_names = {}
        from_ids = {}

        unpacker = struct.Struct('=f')
        packer = struct.Struct("=I")
        for name, value in manifest.iteritems():
            packed = packer.pack(int(value,16))
            packed = packed = '\0' * (4 - len(packed)) + packed
            id_float = unpacker.unpack( packed )[0]
            name_str = name.encode("utf8")
            from_names[name_str] = id_float
            from_ids[id_float] = name_str

        self.cryptomattes[num]["names_to_IDs"] = from_names
        self.cryptomattes[num]["ids_to_names"] = from_ids

        global g_cryptomatte_manf_from_names
        global g_cryptomatte_manf_from_IDs
        g_cryptomatte_manf_from_names = from_names
        g_cryptomatte_manf_from_IDs = from_ids

        return from_names

    def id_to_name(self, ID_value):
        """Checks the manifest for the ID value. 
        Checks the last used manifest first, before decoding
        the existing one. 
        """
        global g_cryptomatte_manf_from_IDs
        manf_cache = g_cryptomatte_manf_from_IDs
        if (type(manf_cache) is dict and ID_value in manf_cache):
            return g_cryptomatte_manf_from_IDs[ID_value]
        elif self.selection != None:
            self.parse_manifest()
            return self.cryptomattes[self.selection]["ids_to_names"].get(ID_value, None)
        else:
            return None

    def name_to_ID(self, name):
        return mm3hash_float(name)

    def test_manifest(self):        
        """Testing function to check for implementation errors and hash collisions.
        Checks all names and values in the manifest in the manifest by rehashing them,
        to ensure that the entire process is sound. Also finds collisions. Returns a tuple
        of errors and collisions. 
        """
        self.parse_manifest()

        ids = {}
        errors = []
        collisions = []
        manifest = self.cryptomattes[self.selection]["names_to_IDs"]
        for name, idvalue in manifest.iteritems():
            if mm3hash_float(name) != idvalue:
                errors.append("computed ID doesn't match manifest ID: (%s, %s)" % (idvalue, mm3hash_float(name)))
            else:
                if idvalue in ids:
                    collisions.append("colliding: %s %s" % (ids[idvalue], name))
                ids[idvalue] = name

        print "Tested %s, %s names" % (self.nuke_node.name(), len(manifest))
        print "    ", len(errors), "non-matching IDs between python and c++."
        print "    ", len(collisions), "hash collisions in manifest."

        return errors, collisions


def print_hash_info(name):
    hash_32 = mmh3.hash(name)
    print "Name:", name
    print "UTF-8 bytes:", " ".join( hex(ord(x))[2:] for x in name)
    print "Hash value (signed):", hash_32
    if hash_32 < 0:
        hash_32 = (-hash_32 - 1) ^ 0xFFFFFFFF
    print "Hash value (unsigned):", hash_32
    print "Float converted:", mm3hash_float(name)


def test_csv_round_trip():
    """Ensures the round trip is correct for CSV encoding and decoding. """
    csv_str = ("""str, "str with space", "single 'quotes'", """
        '"with_a,_comma", "with comma, and \\"quotes\\"", <123.45>, '
        '" space_in_front", "space_at_end ", "has_escape\\\\chars", '
        '"unicode \xd1\x80\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb8\xd0\xbd\xd0\xb0"')
    name_list = ["str", "str with space", "single 'quotes'",
        "with_a,_comma", 'with comma, and "quotes"', "<123.45>", 
        " space_in_front", "space_at_end ", "has_escape\\chars", 
        "unicode \xd1\x80\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb8\xd0\xbd\xd0\xb0"]

    def check_results(encoded, decoded):
        if encoded != csv_str:
            print "list:   ", decoded
            print "orig:   ", csv_str
            print "encoded:", encoded
            raise RuntimeError("Round trip to str failed: %s != %s" % (csv_str, encoded)); 
        for x, y in zip(name_list, decoded):
            if x != y:
                raise RuntimeError("Round trip to list failed: %s != %s" % (x, y));     

    # start from csv
    decoded = _decode_csv(csv_str)
    encoded = _encode_csv(decoded)
    check_results(encoded, decoded)

    # start from list
    encoded = _encode_csv(name_list)
    decoded = _decode_csv(encoded)
    check_results(encoded, decoded)
    print "Success."
    return True


#############################################
# Public - Create Crypto Gizmos
#############################################


def cryptomatte_create_gizmo():
    return nuke.createNode("Cryptomatte") 


def encryptomatte_create_gizmo():
    return nuke.createNode("Encryptomatte")


#############################################
# Public - cryptomatte Events
#############################################


def cryptomatte_knob_changed_event(node = None, knob = None):
    if knob.name() == "inputChange" or knob.name() == "cryptoLayer" or knob.name() == "cryptoLayerLock":
        cinfo = CryptomatteInfo(node)
        _update_cryptomatte_gizmo(node, cinfo)

    elif knob.name() == "pickerAdd":
        if _get_knob_channel_value(node.knob("pickerAdd"), 2) == 0.0:
            return
        cinfo = CryptomatteInfo(node)
        keyed_object = _update_gizmo_keyed_object(node, cinfo, True, "pickerAdd")
        node.knob("pickerRemove").setValue([0,0,0])
        if node.knob("singleSelection").getValue():
            node.knob("matteList").setValue("")
        _matteList_modify(node, keyed_object, False)
        _update_cryptomatte_gizmo(node, cinfo)

    elif knob.name() == "pickerRemove":
        cinfo = CryptomatteInfo(node)
        if _get_knob_channel_value(node.knob("pickerRemove"), 2) == 0.0:
            return
        keyed_object = _update_gizmo_keyed_object(node, cinfo, True, "pickerRemove")
        node.knob("pickerAdd").setValue([0,0,0])
        _matteList_modify(node, keyed_object, True)
        _update_cryptomatte_gizmo(node, cinfo)  

    elif knob.name() == "matteList":
        cinfo = CryptomatteInfo(node)
        _update_cryptomatte_gizmo(node, cinfo)
        node.knob("pickerRemove").setValue([0,0,0])
        node.knob("pickerAdd").setValue([0,0,0])

    elif knob.name() == "ColorKey":
        # probably superfluous, may remove later
        cinfo = CryptomatteInfo(node)
        _update_gizmo_keyed_object(node, cinfo)


def encryptomatte_knob_changed_event(node = None, knob = None):
    if knob.name() in ["matteName", "cryptoLayerLock"]:
        cinfo = CryptomatteInfo(node)
        _update_encryptomatte_gizmo(node, cinfo)

    if knob.name() in ["setupLayers", "cryptoLayer", "inputChange", "cryptoLayers"]:
        _update_encyptomatte_setup_layers(node)
        cinfo = CryptomatteInfo(node)
        _update_encryptomatte_gizmo(node, cinfo)


def encryptomatte_on_create_event(node = None, knob = None):
    node.knob('cryptoLayers').setEnabled(node.knob('setupLayers').value())


#############################################
# Public - cryptomatte functions
#############################################


def update_cryptomatte_gizmo(node, force=False):
    cinfo = CryptomatteInfo(node)
    _update_cryptomatte_gizmo(node, CryptomatteInfo(node), force)


def clear_cryptomatte_gizmo(node):
    node.knob("matteList").setValue("")
    _update_cryptomatte_gizmo(node, CryptomatteInfo(node), True)


def update_all_cryptomatte_gizmos():
    return _force_update_all()


def update_encryptomatte_gizmo(node, force=False):
    cinfo = CryptomatteInfo(node)
    _update_encryptomatte_gizmo(node, CryptomatteInfo(node), force)


def clear_encryptomatte_gizmo(node):
    node.knob("matteName").setValue("")
    _update_encryptomatte_gizmo(node, CryptomatteInfo(node), True)


#############################################
# Utils - Update Gizmi 
#       (gizmi is the plural of gizmo)
#############################################


def _cancel_update(gizmo, force):
    try:
        stopAutoUpdate = gizmo.knob("stopAutoUpdate").getValue()
    except:
        # This happens sometimes on creation. I don't really get it, but this seems to fix it.
        return True
    if (not force and stopAutoUpdate == 1.0): 
        return True
    else:
        return False


def _force_update_all():
    with nuke.root():
        node_count = 0
        for node in nuke.allNodes():
            if node.Class() == "Cryptomatte":
                node_count = node_count + 1
                cinfo = CryptomatteInfo(node)
                _update_cryptomatte_gizmo(node, cinfo, force=True)

        nuke.message("Updated %s cryptomatte gizmos." % node_count)



#############################################
# Utils - Update Gizmi 
#############################################

def _set_channels(gizmo, channels, default="none"):
    gizmo.knob("cryptoLayer").setValue(channels[0])
    for i, knob_name in enumerate(GIZMO_CHANNEL_KNOBS):
        channel = channels[i] if i < len(channels) else default
        gizmo.knob(knob_name).setValue(channel)


def _update_cryptomatte_gizmo(gizmo, cinfo, force=False):
    if _cancel_update(gizmo, force):
        return
    if not cinfo.is_valid():
        return
    cryptomatte_channels = cinfo.get_channels()
    if not cryptomatte_channels:
        return
    _set_channels(gizmo, cryptomatte_channels)
    _set_expression(gizmo, cryptomatte_channels)


def _update_encryptomatte_gizmo(gizmo, cinfo, force=False):
    if _cancel_update(gizmo, force):
        return
    
    matte_name = gizmo.knob('matteName').value()
    matte_input = gizmo.input(1)

    if matte_name == "" and not matte_input is None:
        matte_name = matte_input.name()
        gizmo.knob('matteName').setValue(matte_name)

    if matte_name == "":
        gizmo.knob('id').setValue(0.0)
        gizmo.knob('idHex').setValue('')
        gizmo.knob('previewColor').setValue([0.0, 0.0, 0.0])

    else:
        id_value = mm3hash_float(matte_name)
        gizmo.knob('id').setValue(id_value)
        gizmo.knob('idHex').setValue(id_to_hex(id_value))
        gizmo.knob('previewColor').setValue(id_to_rgb(id_value))

    if gizmo.knob('setupLayers').value():
        gizmo.knob('cryptoLayers').setEnabled(True)
        if cinfo.is_valid():
            cryptomatte_channels = cinfo.get_channels()
            if not cryptomatte_channels:
                cryptomatte_channels = []
        else:
            cryptomatte_channels = []

        crypto_layer = gizmo.knob('cryptoLayer').value()
        if crypto_layer in cryptomatte_channels:
            gizmo.knob('inputCryptoLayers').setValue(len(cryptomatte_channels) - 1)
            manifest_key = cinfo.get_selection_metadata_key("")
            gizmo.knob('manifestKey').setValue(manifest_key)
            gizmo.knob('newLayer').setValue(False)
        else:
            gizmo.knob('inputCryptoLayers').setValue(0)
            gizmo.knob('manifestKey').setValue(CRYPTOMATTE_METADATA_PREFIX + layer_hash(crypto_layer) + '/')
            gizmo.knob('newLayer').setValue(True)

        cryptomatte_channels = [crypto_layer] + [crypto_layer + "{0:02d}".format(i) for i in range(int(gizmo.knob('cryptoLayers').value()))]
        _set_channels(gizmo, cryptomatte_channels, default="none")

    else:
        gizmo.knob('cryptoLayers').setEnabled(False)
        if not cinfo.is_valid():
            return

        cryptomatte_channels = cinfo.get_channels()
        if not cryptomatte_channels:
            return

        gizmo.knob('newLayer').setValue(False)
        _set_channels(gizmo, cryptomatte_channels, default="none")
        gizmo.knob('inputCryptoLayers').setValue(len(cryptomatte_channels) - 1)
        gizmo.knob('cryptoLayers').setValue(len(cryptomatte_channels) - 1)
        manifest_key = cinfo.get_selection_metadata_key("")
        gizmo.knob('manifestKey').setValue(manifest_key)

    gizmo.knob("alphaExpression").setValue(_build_extraction_expression(cryptomatte_channels, [0.0]))    

def _update_encyptomatte_setup_layers(gizmo):
    setup_layers = gizmo.knob('setupLayers').value()
    num_layers = gizmo.knob('cryptoLayers').value()
    input_layers = gizmo.knob('inputCryptoLayers').value()
    crypto_layer = gizmo.knob('cryptoLayer').value()

    if not setup_layers:
        for i in range(len(GIZMO_ADD_CHANNEL_KNOBS)):
            gizmo.knob(GIZMO_ADD_CHANNEL_KNOBS[i]).setValue("none")
            gizmo.knob(GIZMO_REMOVE_CHANNEL_KNOBS[i]).setValue("none")
        #gizmo.knob('manifestKey').setValue("")
        return


    all_layers = nuke.layers()

    for i in range(len(GIZMO_ADD_CHANNEL_KNOBS)):
        
        if i > 0:
            this_layer = "{0}{1:02d}".format(crypto_layer, i - 1)
        else:
            this_layer = crypto_layer

        # Add
        if i <= num_layers:
            if not this_layer in all_layers:
                if i == 0:
                    nuke.Layer(this_layer, [this_layer + '.' + c for c in ['red', 'green', 'blue']])
                else:
                    nuke.Layer(this_layer, [this_layer + '.' + c for c in ['red', 'green', 'blue', 'alpha']])

            gizmo.knob(GIZMO_ADD_CHANNEL_KNOBS[i]).setValue(this_layer)
            gizmo.knob(GIZMO_REMOVE_CHANNEL_KNOBS[i]).setValue("none")
        else:
            gizmo.knob(GIZMO_ADD_CHANNEL_KNOBS[i]).setValue("none")
            if i <= input_layers:
                gizmo.knob(GIZMO_REMOVE_CHANNEL_KNOBS[i]).setValue(this_layer)
            else:
                gizmo.knob(GIZMO_REMOVE_CHANNEL_KNOBS[i]).setValue("none")

    #gizmo.knob('manifestKey').setValue(CRYPTOMATTE_METADATA_PREFIX + layer_hash(crypto_layer) + '/')


def encryptomatte_add_manifest_id(deserialize = False):
    
    node = nuke.thisNode()
    parent = nuke.thisParent()
    name = parent.knob('matteName').value()
    id_hex = parent.knob('idHex').value()
    manifest_key = parent.knob('manifestKey').value()
    metadata = node.metadata()
    manifest = metadata.get(manifest_key + 'manifest', "{}")
    
    if deserialize:
        import json
        d = json.loads(manifest)
        d[name] = hex_id
        new_manifest = json.dumps(d)
        return new_manifest
    else:
        last_item = '"{name}":"{id_hex}"'.format(name=name, id_hex=id_hex)
        last_item += '}'
        
        last_bracket_pos = manifest.rfind('}')
        existing_items = manifest[:last_bracket_pos].rstrip()
        if not existing_items.endswith(',') and not existing_items.endswith('{'):
            return existing_items + ',' + last_item
        else:
            return existing_items + last_item


#############################################
# Utils - Unload Manifest
#############################################


def unload_manifest(node):
    source_node = None
    if node.Class() == "Cryptomatte":
        source_node = node.input(0)
        if not source_node:
            nuke.message('Cryptomatte is not plugged into anything')
            return
    else:
        source_node = node

    cinfo = CryptomatteInfo(node)
    if not cinfo.is_valid():
        nuke.message("Gizmo's cryptomatte selection is not valid or no cryptomattes are available. ")
        return

    names_to_IDs = cinfo.parse_manifest();

    if not names_to_IDs:
        nuke.message('No Cryptomatte manifest was found in the input. ')
        return

    new_keyers = []
    if nuke.ask('There are %s named mattes in the manifest, are you sure you want to create keyer nodes for all of them?' % len(names_to_IDs)):
        with nuke.root():
            dot = nuke.nodes.Dot()
            dot.setInput(0, source_node)

            progress = 0
            task = nuke.ProgressTask("Unloading Manifest")
            for name, metadata_ID in names_to_IDs.iteritems():
                if task.isCancelled():
                    break
                task.setMessage("Creating Cryptomatte Keyer for %s" % name)
                task.setProgress( int(float(progress) / float(len(names_to_IDs)) * 100))
                keyer = nuke.nodes.Cryptomatte(name="ck_%s" % name, matteList=name, matteOnly=True)
                keyer.setInput(0, dot)
                _update_cryptomatte_gizmo(keyer, cinfo)
                new_keyers.append(keyer)
                progress = progress + 1

    return new_keyers


#############################################
# Utils - Build Expressions
#############################################


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def _set_expression(gizmo, cryptomatte_channels):

    matte_list_str = gizmo.knob("matteList").getValue()
    ID_list = []

    matte_list = get_mattelist_as_set(gizmo)

    for item in matte_list:
        if item.startswith("<") and item.endswith(">"):
            numstr = item[1:-1]
            if _is_number(numstr): 
                ID_list.append(single_precision(float(numstr)))
        else:
            ID_list.append(mm3hash_float(item))

    expression = _build_extraction_expression(cryptomatte_channels, ID_list)

    gizmo.knob("expression").setValue(expression)


def _build_condition(condition, IDs):
    conditions = []
    for ID in IDs:
        conditions.append( condition.replace("ID", str(ID)) )
    return " || ".join(conditions)


def _build_extraction_expression(channel_list, IDs):
    if not IDs:
        return ""
        
    iterated_expression = "({red_condition} ? sub_channel.green : 0.0) + ({blue_condition} ? sub_channel.alpha : 0.0) + more_work_needed"
    
    subcondition_red =  "sub_channel.red == ID"
    subcondition_blue = "sub_channel.blue == ID"

    start_channel = channel_list[0]
    sub_channels = list(channel_list)
    sub_channels.remove(start_channel)

    expression = ""
    for channel in sub_channels:
        condition_r = _build_condition(subcondition_red, IDs)
        condition_b = _build_condition(subcondition_blue, IDs)

        channel_expression = iterated_expression.replace("red_condition", condition_r).replace("blue_condition", condition_b)
        channel_expression = channel_expression.replace("sub_channel", channel)

        if not expression:
            expression = channel_expression
        else:
            expression = expression.replace("more_work_needed", channel_expression)
    expression = expression.replace("more_work_needed", "0")

    expression = expression.replace("{", "(")
    expression = expression.replace("}", ")")

    return expression


#def _set_encryptomatte_expression(gizmo, cryptomatte_channels):
#    expression = "1.0 - " + _build_extraction_expression(cryptomatte_channels, [0.0])
#    gizmo.knob("alphaExpression").setValue(expression)
    

#############################################
# Utils - Manifest Processing Helpers
#############################################


def set_text_knob(gizmo, text_knob_name, text):
    if not text_knob_name:
        return
    knob = gizmo.knob(text_knob_name)
    if knob:
        gizmo.knob(text_knob_name).setValue(text)


def _get_knob_channel_value(knob, c_index):
    try:
        return knob.getValue()[c_index]
    except:
        return 0.0

def _update_gizmo_keyed_object(gizmo, cinfo, force=False, color_knob_name="ColorKey", text_knob_name="keyedName"):
    if _cancel_update(gizmo, force):
        return None
    if not gizmo.knob(text_knob_name):
        return None

    ID_value = _get_knob_channel_value(gizmo.knob(color_knob_name), 2)

    if ID_value == 0.0:
        set_text_knob(gizmo, text_knob_name, "Background (Value is 0.0)")
        return None

    name = cinfo.id_to_name(ID_value)

    if name:
        set_text_knob(gizmo, text_knob_name, name)
        return name

    set_text_knob(gizmo, text_knob_name, "ID value not in manifest.")
    return "<%s>" % ID_value


#############################################
# Utils - Comma seperated list processing
#############################################


def _encode_csv(iterable_items):
    """
    Encodes CSVs with special characters escaped, and surrounded in quotes
    if it contains any of these or spaces, with a space after each comma. 
    """
    cleaned_items = []
    need_escape_chars = '"\\'
    need_space_chars = ' ,'
    for item in iterable_items:
        need_escape = any(x in item for x in need_escape_chars)
        need_quotes = need_escape or any(x in item for x in need_space_chars)

        cleaned = None
        if need_escape:
            cleaned = ""
            for char in item:
                if char in need_escape_chars:
                    cleaned +=( '\\%s' % char )
                else:
                    cleaned += char
        else:
            cleaned = item
        if need_quotes:
            cleaned_items.append('"%s"'%cleaned)
        else:
            cleaned_items.append(cleaned)
    result = ", ".join(cleaned_items)
    return result


def _decode_csv(input_str):
    """ Decodes CSVs into a list of strings. """
    import csv
    reader = csv.reader([input_str], quotechar='"', delimiter=',', escapechar="\\", 
        doublequote=False, quoting=csv.QUOTE_ALL, skipinitialspace=True);
    result = []
    for row in reader:
        result += row
    return result


def get_mattelist_as_set(gizmo):
    matte_list = gizmo.knob("matteList").getValue()
    raw_list = _decode_csv(matte_list)
    result = set()
    for item in raw_list:
        item = item.encode("utf-8") if type(item) is unicode else str(item)
        result.add(item) 
    return result


def set_mattelist_from_set(gizmo, matte_items):
    " Creates a CSV matte list. "
    matte_names_list = list(matte_items)
    matte_names_list.sort(key=lambda x: x.lower())
    matte_list_str = _encode_csv(matte_names_list)
    gizmo.knob("matteList").setValue(matte_list_str)

def _matteList_modify(gizmo, name, remove):
    def _matteList_set_add(name, matte_names):
        matte_names.add(name)

    def _matteList_set_remove(name, matte_names):
        if name in matte_names:
            matte_names.remove(name) # the simple case
        elif name.startswith('<') and name.endswith('>') and _is_number(name[1:-1]):
            # maybe it was selected by name, but is being removed by num
            num = single_precision(float(name[1:-1]))
            for existing_name in matte_names:
                if mm3hash_float(existing_name) == num:
                    matte_names.remove(existing_name)
                    break

    if not name or gizmo.knob("stopAutoUpdate").getValue() == 1.0:
        return
    
    matte_names = get_mattelist_as_set(gizmo)
    if remove:
        _matteList_set_remove(name, matte_names)
    else:
        _matteList_set_add(name, matte_names)
    set_mattelist_from_set(gizmo, matte_names)


#############################################
# Public - Decryption
#############################################


def decryptomatte_all(ask=True):
    decryptomatte_nodes(nuke.allNodes(), ask)


def decryptomatte_selected(ask=False):
    decryptomatte_nodes(nuke.selectedNodes(), ask)


def decryptomatte_nodes(nodes, ask):
    gizmos = []

    for node in nodes:
        if node.Class() == "Cryptomatte":
            gizmos.append(node)
    if not gizmos:
        return

    if not ask or nuke.ask(('Replace %s Cryptomatte gizmos with expression nodes? '
        'Replaced Gizmos will be disabled and selected.') % (len(gizmos))):

        for gizmo in gizmos:
            _decryptomatte(gizmo)

        for node in nuke.selectedNodes():
            node.knob("selected").setValue(False)

        for gizmo in gizmos:
            gizmo.knob("selected").setValue(True)


#############################################
# Decryptomatte helpers
#############################################


def _decryptomatte(gizmo):
    def _decryptomatte_get_name(gizmo):
        name_out = gizmo.knob("matteList").value()
        name_out.replace(", ", "_")
        if len(name_out) > 100:
            name_out = name_out[0:100]
        return name_out

    matte_name = _decryptomatte_get_name(gizmo)
    expression_str = gizmo.knob("expression").value()

    remove_channels = gizmo.knob("RemoveChannels").value()
    matte_only = gizmo.knob("matteOnly").value()

    connect_to = []
    dependents = gizmo.dependent()
    for node in dependents:
        num_inputs = node.inputs()
        for iid in range(0, num_inputs):
            inode =  node.input(iid)
            if inode:
                if inode.fullName() == gizmo.fullName():
                    connect_to.append((node, iid))

    disabled = gizmo.knob("disable").getValue()
    expr_node = nuke.nodes.Expression(inputs=[gizmo], channel0="alpha", 
        expr0=expression_str, name="CryptExpr_%s"%matte_name, disable=disabled)
    for knob_name in GIZMO_CHANNEL_KNOBS:
        expr_node.addKnob(nuke.nuke.Channel_Knob(knob_name, "none") )
        expr_node.knob(knob_name).setValue(gizmo.knob(knob_name).value())
        expr_node.knob(knob_name).setVisible(False)
    expr_node.knob("expr0").setValue(expression_str)

    last_node = expr_node
    if matte_only:
        shuffler = nuke.nodes.Shuffle(inputs=[last_node], red="alpha", 
            green="alpha", blue="alpha", name="CryptShuf_%s"%matte_name, disable=disabled)
        last_node = shuffler
    if remove_channels:
        remover = nuke.nodes.Remove(inputs=[last_node], operation="keep", 
            channels="rgba", name="CryptRemove_%s"%matte_name, disable=disabled)
        last_node = remover
    for node, inputID in connect_to:
        node.setInput(inputID, last_node)

    gizmo.knob("disable").setValue(True)
