#
#
#  Copyright (c) 2014, 2015, 2016, 2017 Psyop Media Company, LLC
#  See license.txt
#
#

import re
import csv
import nuke
import struct
import fnmatch

__version__ = "1.4.0"

GIZMO_CHANNEL_KNOBS = [
    "in00", "in01", "in02", "in03", 
    "in04", "in05", "in06", "in07",
    "in08", "in09", "in10", "in11"
]
GIZMO_REMOVE_CHANNEL_KNOBS = [
    "remove00", "remove01", "remove02", "remove03", 
    "remove04", "remove05", "remove06", "remove07"
]
GIZMO_ADD_CHANNEL_KNOBS = [
    "add00", "add01", "add02", "add03", 
    "add04", "add05", "add06", "add07" 
]

CRYPTO_METADATA_LEGAL_PREFIX = ["exr/cryptomatte/", "cryptomatte/"]
CRYPTO_METADATA_DEFAULT_PREFIX = CRYPTO_METADATA_LEGAL_PREFIX[1]

HAS_WILDCARDS_RE = re.compile(r"(?<!\\)([*?\[\]])")


def setup_cryptomatte_ui():
    if nuke.GUI:
        toolbar = nuke.menu("Nodes")
        menu = toolbar.addMenu("Cryptomatte", "cryptomatte_logo.png",index=-1)
        menu.addCommand("Cryptomatte", "import cryptomatte_utilities as cu; cu.cryptomatte_create_gizmo();")
        menu.addCommand("Decryptomatte All", "import cryptomatte_utilities as cu; cu.decryptomatte_all();")
        menu.addCommand("Decryptomatte Selection", "import cryptomatte_utilities as cu; cu.decryptomatte_selected();")
        menu.addCommand("Encryptomatte", "import cryptomatte_utilities as cu; cu.encryptomatte_create_gizmo();")


def setup_cryptomatte():
    nuke.addOnCreate(lambda: cryptomatte_on_create_event(
        nuke.thisNode(), nuke.thisKnob()), nodeClass='Cryptomatte')
    nuke.addKnobChanged(lambda: cryptomatte_knob_changed_event(
        nuke.thisNode(), nuke.thisKnob()), nodeClass='Cryptomatte')
    nuke.addKnobChanged(lambda: encryptomatte_knob_changed_event(
        nuke.thisNode(), nuke.thisKnob()), nodeClass='Encryptomatte')
    nuke.addOnCreate(lambda: encryptomatte_on_create_event(
        nuke.thisNode(), nuke.thisKnob()), nodeClass='Encryptomatte')


#############################################
# Testing
#############################################

class CryptomatteTesting(object):
    """ Utility functions for manually running tests. 
    Returns results if there are failures, otherwise None 

    Arguments of these functions:
        test_filter -- (string) will be matched fnmatch style (* wildcards) to either the name of the TestCase 
        class or test method. 

        failfast -- (bool) will stop after a failure, and skip cleanup of the nodes that were created. 
    """

    def get_all_unit_tests(self):
        import cryptomatte_utilities_tests as cu_tests
        return cu_tests.get_all_unit_tests()

    def get_all_nuke_tests(self):
        import cryptomatte_utilities_tests as cu_tests
        return cu_tests.get_all_nuke_tests()

    def run_unit_tests(self, test_filter="", failfast=False):
        import cryptomatte_utilities_tests as cu_tests
        return cu_tests.run_unit_tests(test_filter, failfast)

    def run_nuke_tests(self, test_filter="", failfast=False):
        import cryptomatte_utilities_tests as cu_tests
        return cu_tests.run_nuke_tests(test_filter, failfast)

tests = CryptomatteTesting()

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
    exp = hash_32 >> 23 & 255 
    if (exp == 0) or (exp == 255):
        hash_32 ^= 1 << 23 

    packed = struct.pack('<L', hash_32 & 0xffffffff)
    return struct.unpack('<f', packed)[0]


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

def reset_manifest_cache():
    global g_cryptomatte_manf_from_names
    global g_cryptomatte_manf_from_IDs

    g_cryptomatte_manf_from_names = {}
    g_cryptomatte_manf_from_IDs = {}

reset_manifest_cache()


class CryptomatteInfo(object):

    def __init__(self, node_in, reload_metadata=False):
        """Take a nuke node, such as a read node or a Cryptomatte gizmo,
        and Reformat metadata into a dictionary, and collect channel
        information."""
        self.cryptomattes = {}
        self.nuke_node = node_in
        self.selection = None
        self.filename = None

        if not self.nuke_node:
            return

        exr_metadata_dict = {}
        if not reload_metadata:
            exr_metadata_dict = self._load_minimal_metadata()

        if not exr_metadata_dict:
            exr_metadata_dict = self.nuke_node.metadata(view=nuke.thisView()) or {}

        default_selection = None
        
        self.cachable_metadata = {}
        for key, value in exr_metadata_dict.items():
            if key == "input/filename":
                self.filename = value
                self.cachable_metadata[key] = value
            for prefix in CRYPTO_METADATA_LEGAL_PREFIX:
                if not key.startswith(prefix):
                    continue
                numbered_key = key[len(prefix):] # ex: "exr/cryptomatte/ae93ba3/name" --> "ae93ba3/name"
                metadata_id, partial_key = numbered_key.split("/")  # ex: "ae93ba3/name" --> ae93ba3, "name"
                if metadata_id not in self.cryptomattes:
                    self.cryptomattes[metadata_id] = {}
                if partial_key == "name":
                    value = _legal_nuke_layer_name(value)
                self.cryptomattes[metadata_id][partial_key] = value
                self.cryptomattes[metadata_id]['md_prefix'] = prefix
                if partial_key != "manifest":
                    self.cachable_metadata[key] = value
                break

        for metadata_id, value in self.cryptomattes.items():
            if not "name" in value:
                value["name"] = ""

        if self.cryptomattes:
            default_selection = sorted(
                list(self.cryptomattes.keys()), 
                key=lambda x: self.cryptomattes[x]["name"])[0]

        for metadata_id, value in self.cryptomattes.items():
            name = value["name"]
            channels = self._identify_channels(name)
            self.cryptomattes[metadata_id]["channels"] = channels

        self.selection = default_selection
        if self.nuke_node.Class() in ["Cryptomatte", "Encryptomatte"]:
            selection_name = self.nuke_node.knob("cryptoLayer").getValue()
            if selection_name:
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
        if not self.cryptomattes[self.selection]["channels"]:
            return False
        return True

    def set_selection(self, selection):
        """ sets the selection (eg. cryptoObject) based on the name. 
        Returns true if successful. 
        """
        selection = _legal_nuke_layer_name(selection)
        for num in self.cryptomattes:
            if self.cryptomattes[num]["name"] == selection:
                self.selection = num
                return True
        self.selection = None
        return False

    def get_selection_metadata_key(self, key):
        return self.cryptomattes[self.selection]["md_prefix"] + self.selection + "/" + key

    def get_cryptomatte_names(self):
        """ gets the names of the cryptomattes contained the file, which
        are the possible selections or cryptomatte channels.
        """
        return [self.cryptomattes[x]["name"] for x in self.cryptomattes]

    def get_channels(self):
        return self.cryptomattes[self.selection]["channels"] if self.selection else None

    def get_selection_name(self):
        return self.cryptomattes[self.selection]["name"] if self.selection else None

    def get_metadata_cache(self):
        import json
        return json.dumps(self.cachable_metadata)

    def _load_minimal_metadata(self):
        """ Returns {} if no quicklky accessible metadata is found, 
        otherwise returns only metadata accessible without loading everything, 
        and no manifest (which may be large). 
        """
        import json
        if not "metadataCache" in self.nuke_node.knobs():
            return {}
        metadata_cache = self.nuke_node.knob("metadataCache").getValue()
        if metadata_cache:
            return json.loads(metadata_cache)
        else:
            return {}

    def _identify_channels(self, name):
        """from a name like "cryptoObject", 
        gets sorted channels, such as cryptoObject00, cryptoObject01, cryptoObject02
        """

        channel_list = []
        if self.nuke_node.Class() in ["Cryptomatte", "Encryptomatte"]:
            # nuke_node is a keyer gizmo or encryptomatte gizmo
            channel_list = self.nuke_node.node('Input1').channels()
        else:
            # nuke_node might a read node
            channel_list = self.nuke_node.channels()

        # regex for "cryptoObject" + digits + ending with .red or .r
        channel_regex = re.compile(r'({name}\d+)\.(?:red|r)$'.format(name=name))
        pure_channels = []
        for channel in channel_list:
            match = channel_regex.match(channel)
            if match:
                pure_channels.append(match.group(1))

        return sorted(pure_channels)[:len(GIZMO_CHANNEL_KNOBS)]

    def resolve_manifest_paths(self, exr_path, sidecar_path):
        import os
        if "\\" in sidecar_path:
            print("Cryptomatte: Invalid sidecar path (Back-slashes not allowed): ", sidecar_path)
            return "" # to enforce the specification. 
        joined = os.path.join(os.path.dirname(exr_path), sidecar_path)
        return os.path.normpath(joined)

    def lazy_load_manifest(self):
        import json
        if 'manifest' not in self.cryptomattes[self.selection]:
            manif_key = self.get_selection_metadata_key('manifest')
            manif_str = self.nuke_node.metadata(manif_key, view=nuke.thisView())
            if manif_str is None:
                return {}
            else:
                self.cryptomattes[self.selection]['manifest'] = manif_str
        try:
            return json.loads(self.cryptomattes[self.selection]['manifest'])
        except ValueError as e:
            print("Cryptomatte: Unable to parse manifest. (%s)." % e)
            return {}

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
                    print("Cryptomatte: Unable to parse manifest, ", manif_file)
            else:
                print("Cryptomatte: Unable to find manifest file: ", manif_file)
        else:
            manifest = self.lazy_load_manifest()

        from_names = {}
        from_ids = {}

        unpacker = struct.Struct('=f')
        packer = struct.Struct("=I")
        for name, value in manifest.items():
            packed = packer.pack(int(value,16))
            packed = packed = b'\0' * (4 - len(packed)) + packed
            id_float = unpacker.unpack( packed )[0]
            name_str = name if type(name) is str else name.encode("utf-8")
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

    def test_manifest(self, quiet=False):
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
        for name, idvalue in manifest.items():
            if mm3hash_float(name) != idvalue:
                errors.append("computed ID doesn't match manifest ID: (%s, %s)" % (idvalue, mm3hash_float(name)))
            else:
                if idvalue in ids:
                    collisions.append("colliding: %s %s" % (ids[idvalue], name))
                ids[idvalue] = name

        if not quiet:
            print("Tested %s, %s names" % (self.nuke_node.name(), len(manifest)))
            print("    ", len(errors), "non-matching IDs between python and c++.")
            print("    ", len(collisions), "hash collisions in manifest.")

        return errors, collisions


def print_hash_info(name):
    hash_32 = mmh3.hash(name)
    print("Name:", name)
    print("UTF-8 bytes:", " ".join( hex(ord(x))[2:] for x in name))
    print("Hash value (signed):", hash_32)
    if hash_32 < 0:
        hash_32 = (-hash_32 - 1) ^ 0xFFFFFFFF
    print("Hash value (unsigned):", hash_32)
    print("Float converted:", mm3hash_float(name))


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


def cryptomatte_on_create_event(node = None, knob = None):
    # make sure choices are available on load
    prev_stop_state = node.knob("stopAutoUpdate").getValue()
    node.knob("stopAutoUpdate").setValue(True)

    _set_crypto_layer_choice_options(node, CryptomatteInfo(node))

    node.knob("stopAutoUpdate").setValue(prev_stop_state)


def cryptomatte_knob_changed_event(node = None, knob = None):
    if _limbo_state(node):
        return

    if knob.name() == "inputChange":
        if unsafe_to_do_inputChange(node):
            return # see comment in #unsafe_to_do_inputChange.
        cinfo = CryptomatteInfo(node, reload_metadata=True)
        _update_cryptomatte_gizmo(node, cinfo)
    elif knob.name() in ["cryptoLayer", "cryptoLayerLock"]:
        cinfo = CryptomatteInfo(node)
        _update_cryptomatte_gizmo(node, cinfo)
    elif knob.name() in ["cryptoLayerChoice"]:
        if not node.knob('cryptoLayerLock').value():
            knob_value = int(knob.getValue())
            choice_options = list(knob.values())
            if knob_value >= len(choice_options):
                return
            prev_crypto_layer = node.knob('cryptoLayer').value()
            new_crypto_layer = list(knob.values())[knob_value]
            if prev_crypto_layer != new_crypto_layer:
                node.knob('cryptoLayer').setValue(new_crypto_layer)
                cinfo = CryptomatteInfo(node)
                _update_cryptomatte_gizmo(node, cinfo)
            
                # Undo user action on menu
                knob.setValue(list(knob.values()).index(node.knob('cryptoLayer').value()))
    elif knob.name() == "pickerAdd":
        if node.knob("singleSelection").getValue():
            node.knob("matteList").setValue("")
        ID_value = _get_keyed_ID(node, node.knob("pickerAdd"), remove=False)
        if ID_value == 0.0:
            return
        cinfo = CryptomatteInfo(node)
        keyed_object = cinfo.id_to_name(ID_value) or "<{0:.12g}>".format(ID_value)
        node.knob("pickerRemove").setValue([0] * 8)
        _modify_mattelist_with_keyer(node, keyed_object, False)
        _update_cryptomatte_gizmo(node, cinfo)

    elif knob.name() == "pickerRemove":
        ID_value = _get_keyed_ID(node, node.knob("pickerRemove"), remove=True)
        if ID_value == 0.0:
            return
        cinfo = CryptomatteInfo(node)
        keyed_object = cinfo.id_to_name(ID_value) or "<{0:.12g}>".format(ID_value)
        node.knob("pickerAdd").setValue([0] * 8)
        _modify_mattelist_with_keyer(node, keyed_object, True)
        _update_cryptomatte_gizmo(node, cinfo)  

    elif knob.name() == "matteList":
        cinfo = CryptomatteInfo(node)
        _update_cryptomatte_gizmo(node, cinfo)
        node.knob("pickerRemove").setValue([0] * 8)
        node.knob("pickerAdd").setValue([0] * 8)

    elif knob.name() in ["previewMode", "previewEnabled"]:
        cinfo = CryptomatteInfo(node)
        _update_cryptomatte_gizmo(node, cinfo)

    elif knob.name() == "forceUpdate":
        cinfo = CryptomatteInfo(node, reload_metadata=True)
        _update_cryptomatte_gizmo(node, cinfo, True)

    elif knob.name() == "useWildcards":
        cinfo = CryptomatteInfo(node)
        _update_cryptomatte_gizmo(node, cinfo, True)


def encryptomatte_knob_changed_event(node=None, knob=None):
    if _limbo_state(node):
        return

    if knob.name() in ["matteName", "cryptoLayerLock"]:
        cinfo = CryptomatteInfo(node, reload_metadata=True)
        _update_encryptomatte_gizmo(node, cinfo)
        return
    if knob.name() in ["setupLayers", "cryptoLayer", "inputChange", "cryptoLayers"]:
        if knob.name() == "inputChange":
            if unsafe_to_do_inputChange(node):
                return # see comment in #unsafe_to_do_inputChange.
        _update_encyptomatte_setup_layers(node)
        cinfo = CryptomatteInfo(node, reload_metadata=True)
        _update_encryptomatte_gizmo(node, cinfo)


def encryptomatte_on_create_event(node = None, knob = None):
    node.knob('cryptoLayers').setEnabled(node.knob('setupLayers').value())

#############################################
# Public - cryptomatte functions
#############################################


def update_cryptomatte_gizmo(node, force=False):
    """
    Not invoked by gizmo button.

    The gizmo button relies on knob changed callbacks, to avoid
    recursive evaluation of callbacks.
    """
    cinfo = CryptomatteInfo(node, reload_metadata=True)
    _update_cryptomatte_gizmo(node, cinfo, force=force)


def clear_cryptomatte_gizmo(node):
    """Relies on knob changed callbacks to update gizmo after values change."""
    node.knob("matteList").setValue("")
    node.knob("expression").setValue("")


def update_all_cryptomatte_gizmos():
    return _force_update_all()


def update_encryptomatte_gizmo(node, force=False):
    cinfo = CryptomatteInfo(node, reload_metadata=True)
    _update_encryptomatte_gizmo(node, cinfo, force)


def clear_encryptomatte_gizmo(node):
    node.knob("matteName").setValue("")
    _update_encryptomatte_gizmo(node, cinfo, True)


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
                cinfo = CryptomatteInfo(node, reload_metadata=True)
                _update_cryptomatte_gizmo(node, cinfo, force=True)

        nuke.message("Updated %s cryptomatte gizmos." % node_count)


def unsafe_to_do_inputChange(node):
    """
    In Nuke 8, 9, 10, 11, 12 it's been discovered that when copy and pasting certain nodes,
    or when opening certain scripts the inputchanged knob change callback breaks the script.

    What actually happens is the call to metadata() breaks it.

    The only reliable way to notice that it's unsafe we've found is calling node.screenHeight(),
    and if zero, stopping.

    see: https://github.com/Psyop/Cryptomatte/issues/18
    """
    return nuke.NUKE_VERSION_MAJOR > 7 and node.screenHeight() == 0


def _limbo_state(gizmo):
    """
    Checks if the node is in a limbo state. This happens when creating
    and connected a node at the same time. It manifests as the error,
        ValueError: A PythonObject is not attached to a node
    """
    try:
        gizmo.Class()
    except ValueError:
        return True
    return False


#############################################
# Utils - Update Gizmi
#############################################

def _set_channels(gizmo, channels, layer_name):
    gizmo.knob("cryptoLayer").setValue(layer_name)
    for i, knob_name in enumerate(GIZMO_CHANNEL_KNOBS):
        channel = channels[i] if i < len(channels) else "none"
        gizmo.knob(knob_name).setValue(channel)

def _set_metadata_cache(gizmo, cinfo):
    gizmo.knob('metadataCache').setValue(cinfo.get_metadata_cache())

def _set_crypto_layer_choice_options(gizmo, cinfo):
    layer_locked = gizmo.knob('cryptoLayerLock').value()
    values = sorted([v.get('name', '') for v in list(cinfo.cryptomattes.values())])
    gizmo.knob('cryptoLayerChoice').setEnabled(not layer_locked)
    gizmo.knob("cryptoLayerChoice").setValues(values)
    return values

def _set_crypto_layer_choice(gizmo, cinfo):
    values = _set_crypto_layer_choice_options(gizmo, cinfo)
    current_selection = cinfo.get_selection_name()

    if current_selection:
        gizmo.knob("cryptoLayerChoice").setValue(values.index(current_selection))

def _update_cryptomatte_gizmo(gizmo, cinfo, force=False):
    if _cancel_update(gizmo, force):
        return
    _set_metadata_cache(gizmo, cinfo)
    if not cinfo.is_valid():
        return
    cryptomatte_channels = cinfo.get_channels()
    if not cryptomatte_channels:
        return
    _set_channels(gizmo, cryptomatte_channels, cinfo.get_selection_name())
    _explode_wildcards(gizmo, cinfo)
    _set_expression(gizmo, cryptomatte_channels)
    _set_preview_expression(gizmo, cryptomatte_channels)
    _set_crypto_layer_choice(gizmo, cinfo)


def _explode_wildcards(gizmo, cinfo):
    """ Explodes the wildcards in the matte list."""
    if not gizmo.knob("useWildcards").value():
        return 

    ml = MatteList(gizmo)
    if ml.has_wildcards:
        ml.expand_wildcards(cinfo)
        ml.set_gizmo_mattelist(gizmo)

def _set_ui(gizmo):
    layer_locked = gizmo.knob('cryptoLayerLock').value()
    gizmo.knob('cryptoLayerChoice').setEnabled(not layer_locked)


def _legal_nuke_layer_name(name):
    """ Blender produces channels with certain characters in the name, which Nuke
    changes to "_". We have to make sure we handle Cryptomattes
    that are built this way. Doing this by only allowing alphanumeric
    output plus dash and underscores
    """
    prefix = ""
    if name and name[0] in "0123456789":
        prefix = "_"
    return prefix + "".join([x if x.lower() in 'abcdefghijklmnopqrstuvwxyz1234567890_-' else '_' for x in name])


def _update_encryptomatte_gizmo(gizmo, cinfo, force=False):
    if _cancel_update(gizmo, force):
        return

    def reset_gizmo(gizmo):
        _set_channels(gizmo, [], "")
        gizmo.knob("alphaExpression").setValue("")

    matte_name = gizmo.knob('matteName').value()
    matte_input = gizmo.input(1)
    _set_metadata_cache(gizmo, cinfo)

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
        crypto_layer = _legal_nuke_layer_name(crypto_layer)
        if not crypto_layer:
            return reset_gizmo(gizmo)
        if crypto_layer in cryptomatte_channels:
            gizmo.knob('inputCryptoLayers').setValue(len(cryptomatte_channels) - 1)
            manifest_key = cinfo.get_selection_metadata_key("")
            gizmo.knob('manifestKey').setValue(manifest_key)
            gizmo.knob('newLayer').setValue(False)
        else:
            gizmo.knob('inputCryptoLayers').setValue(0)
            gizmo.knob('manifestKey').setValue(
                CRYPTO_METADATA_DEFAULT_PREFIX + layer_hash(crypto_layer) + '/')
            gizmo.knob('newLayer').setValue(True)

        cryptomatte_channels = [
            crypto_layer + "{0:02d}".format(i)
            for i in range(int(gizmo.knob('cryptoLayers').value()))
        ]
        _set_channels(gizmo, cryptomatte_channels, crypto_layer)

    else:
        gizmo.knob('cryptoLayers').setEnabled(False)
        if not cinfo.is_valid():
            return

        cryptomatte_channels = cinfo.get_channels()
        if not cryptomatte_channels:
            return

        gizmo.knob('newLayer').setValue(False)
        _set_channels(gizmo, cryptomatte_channels, cinfo.get_selection_name())
        gizmo.knob('inputCryptoLayers').setValue(len(cryptomatte_channels) - 1)
        gizmo.knob('cryptoLayers').setValue(len(cryptomatte_channels) - 1)
        manifest_key = cinfo.get_selection_metadata_key("")
        gizmo.knob('manifestKey').setValue(manifest_key)

    gizmo.knob("alphaExpression").setValue(_build_extraction_expression(cryptomatte_channels, [0.0]))

def _update_encyptomatte_setup_layers(gizmo):
    setup_layers = gizmo.knob('setupLayers').value()
    num_layers = gizmo.knob('cryptoLayers').value()
    input_layers = gizmo.knob('inputCryptoLayers').value()
    crypto_layer = _legal_nuke_layer_name(gizmo.knob('cryptoLayer').value())

    if not setup_layers:
        gizmo.knob('manifestKey').setValue("")
        for ch_add, ch_remove in zip(GIZMO_ADD_CHANNEL_KNOBS, GIZMO_REMOVE_CHANNEL_KNOBS):
            gizmo.knob(ch_add).setValue("none")
            gizmo.knob(ch_remove).setValue("none")
        return

    all_layers = nuke.layers()

    num_ch = len(GIZMO_ADD_CHANNEL_KNOBS)
    for i, ch_add, ch_remove in zip(
            list(range(num_ch)), GIZMO_ADD_CHANNEL_KNOBS, GIZMO_REMOVE_CHANNEL_KNOBS):
        this_layer = "{0}{1:02d}".format(crypto_layer, i)
        # Add
        if i < num_layers:
            if not this_layer in all_layers:
                channels = ["%s.%s" % (this_layer, c) for c in ['red', 'green', 'blue', 'alpha']]
                nuke.Layer(this_layer, channels)

            gizmo.knob(ch_add).setValue(this_layer)
            gizmo.knob(ch_remove).setValue("none")
        else:
            gizmo.knob(ch_add).setValue("none")
            if i <= input_layers:
                gizmo.knob(ch_remove).setValue(this_layer)
            else:
                gizmo.knob(ch_remove).setValue("none")

def encryptomatte_add_manifest_id():
    node = nuke.thisNode()
    parent = nuke.thisParent()
    name = parent.knob('matteName').value()
    id_hex = parent.knob('idHex').value()
    manifest_key = parent.knob('manifestKey').value()
    metadata = node.metadata()
    manifest = metadata.get(manifest_key + 'manifest', "{}")

    # Add another item, with closing bracket
    last_item = '"%s":"%s"}' % (name, id_hex)
    last_bracket_pos = manifest.rfind('}')
    existing_items = manifest[:last_bracket_pos].rstrip()
    if not existing_items.endswith(',') and not existing_items.endswith('{'):
        existing_items += ','
    existing_items += last_item
    return existing_items


#############################################
# Utils - Troubleshooting
#############################################

def _troubleshoot_gizmo(gizmo):
    MSG_WRONGTYPE = 'Troubleshooting: Cannot troubleshoot non-Cryptomatte nodes'
    MSG_UNCONNECTED = 'Cryptomatte gizmo is not plugged into anything'
    MSG_NONE_FOUND = 'No Cryptomattes found in input. '
    MSG_LYR_UNSET = ('Gizmo needs updating, layer is not set. '
                     'Press "force update" or reconnect.')
    MSG_LYR_UNPOP = ('Gizmo needs updating, layer menu is not populated. '
                     'Press "force update" or reconnect.')
    MSG_ODD_STATE = ('Gizmo is in an odd state and needs updating. '
                     'Press "force update" or reconnect.')
    MSG_INVALID_SEL = ('Layer is set to "%s", which is unavailable. '
                       'Select another layer.')
    if gizmo.Class() != "Cryptomatte":
        return [MSG_WRONGTYPE]

    issues = []
    if not gizmo.input(0):
        issues.append(MSG_UNCONNECTED)
    else:
        cinfo = CryptomatteInfo(gizmo, reload_metadata=True)
        available = cinfo.get_cryptomatte_names()
        selection = gizmo.knob('cryptoLayer').value()
        menu_selection = gizmo.knob('cryptoLayerChoice').value()
        if not cinfo.cryptomattes:
            issues.append(MSG_NONE_FOUND)
        else:
            if not selection or not menu_selection:
                issues.append(MSG_LYR_UNSET)
            if menu_selection not in available:
                issues.append(MSG_LYR_UNPOP)
            elif selection not in gizmo.knob(GIZMO_CHANNEL_KNOBS[0]).value():
                issues.append(MSG_ODD_STATE)
            elif selection not in available:
                issues.append(MSG_INVALID_SEL % selection)
    return issues

def _troubleshoot_setup():
    MSG_BAD_INSTALL = ("Installation is wrong, callbacks were not found. "
                       "setup_cryptomatte() did not run, init.py may "
                       "not be set up properly. ")
    PROXY_MODE = "Proxy mode is on, this can cause artifacts. "
    issues = []
    expected_knob_changeds = ["Cryptomatte", "Encryptomatte"]
    if any(x not in nuke.callbacks.knobChangeds for x in expected_knob_changeds):
        issues.append(MSG_BAD_INSTALL)
    if nuke.root().knob('proxy').value():
        issues.append(PROXY_MODE)
    return issues

def troubleshoot_gizmo(node):
    issues = _troubleshoot_gizmo(node) + _troubleshoot_setup()
    if issues:
        nuke.message("Troubleshooting: Found the following issues: %s" %
                     "\n    - ".join([""] + issues))
    else:
        nuke.message("Troubleshooting: All good!")

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

    cinfo = CryptomatteInfo(node, reload_metadata=True)
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
            for name, metadata_ID in names_to_IDs.items():
                if task.isCancelled():
                    break
                task.setMessage("Creating Cryptomatte Keyer for %s" % name)
                task.setProgress( int(float(progress) / float(len(names_to_IDs)) * 100))
                ml = MatteList("")
                ml.add(name)
                keyer = nuke.nodes.Cryptomatte(name="ck_%s" % name, matteList=ml.to_nukestr, matteOnly=True)
                keyer.setInput(0, dot)
                _update_cryptomatte_gizmo(keyer, cinfo)
                new_keyers.append(keyer)
                progress = progress + 1

    return new_keyers


#############################################
# Utils - Build Expressions
#############################################


def _set_expression(gizmo, cryptomatte_channels):
    ml = MatteList(gizmo)
    expression = _build_extraction_expression(cryptomatte_channels, ml.IDs)
    gizmo.knob("expression").setValue(expression)


def _build_condition(condition, IDs):
    conditions = []
    for ID in IDs:
        conditions.append( condition.replace("ID", "{0:.12g}".format(ID)) )
    return " || ".join(conditions)


def _build_extraction_expression(channel_list, IDs):
    if not IDs:
        return ""
    sorted_ids = sorted(IDs)
    iterated_expression = "({red_condition} ? sub_channel.green : 0.0) + ({blue_condition} ? sub_channel.alpha : 0.0) + more_work_needed"

    subcondition_red =  "sub_channel.red == ID"
    subcondition_blue = "sub_channel.blue == ID"

    expression = ""
    for channel in channel_list:
        condition_r = _build_condition(subcondition_red, sorted_ids)
        condition_b = _build_condition(subcondition_blue, sorted_ids)

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

def _set_preview_expression(gizmo, cryptomatte_channels):
    enabled = gizmo.knob('previewEnabled').getValue()
    preview_mode = gizmo.knob('previewMode').value() if enabled else 'None'

    channel_pairs = []
    for c in cryptomatte_channels:
        channel_pairs.append(('%s.red' % c, '%s.green' % c))
        channel_pairs.append(('%s.blue' % c, '%s.alpha' % c))

    expressions = []
    if preview_mode == 'Edges':
        expressions = [
            "",
            "",
            "",
            "2.0 * %s" % channel_pairs[1][1],
        ]
    elif preview_mode == 'Colors':
        """
        Generates an expression like this: 
        red = (
          (mantissa(abs(c00.red)) * 1 % 0.25) * c00.green + 
          (mantissa(abs(c00.blue)) * 1 % 0.25) * c00.alpha + 
          (mantissa(abs(c01.red)) * 1 % 0.25) * c01.green + 
          (mantissa(abs(c01.blue)) * 1 % 0.25) * c01.alpha
        )
        green = (
          (mantissa(abs(c00.red)) * 4 % 0.25) * c00.green + 
          (mantissa(abs(c00.blue)) * 4 % 0.25) * c00.alpha + 
          (mantissa(abs(c01.red)) * 4 % 0.25) * c01.green + 
          (mantissa(abs(c01.blue)) * 4 % 0.25) * c01.alpha
        )
        blue = (
          (mantissa(abs(c00.red)) * 16 % 0.25) * c00.green + 
          (mantissa(abs(c00.blue)) * 16 % 0.25) * c00.alpha + 
          (mantissa(abs(c01.red)) * 16 % 0.25) * c01.green + 
          (mantissa(abs(c01.blue)) * 16 % 0.25) * c01.alpha
        )
        """

        puzzle_layers = 4
        factors = [1, 16, 64]
        puzzle_bits = "(mantissa(abs({id_chan})) * {factor} % 0.25) * {cov_chan}"

        for factor in factors:
            puzzle = " + ".join(
                puzzle_bits.format(factor=factor, id_chan=id_chan, cov_chan=cov_chan)
                for (id_chan, cov_chan) in channel_pairs[:puzzle_layers])
            expr = "(%s)" % puzzle
            expressions.append(expr)
        expressions.append("")
    else:  # mode is none
        expressions = ["", "", "", ""]
    for i in range(4):
        gizmo.knob('previewExpression' + str(i)).setValue(expressions[i])



#############################################
# Utils - Manifest Processing Helpers
#############################################


def _get_keyed_ID(node, keying_knob, remove=False):
    bbox = keying_knob.getValue()[4:]
    upstream_node = node.input(0)
    if not upstream_node:
        return 0.0

    ml = MatteList(node)
    id_set = set(ml.IDs)

    saw_bg = False
    add_mode = not remove
    rm_mode = remove

    for layer_knob in GIZMO_CHANNEL_KNOBS:
        layer = node.knob(layer_knob).value()

        if layer == "none":
            return 0.0

        for id_suffix, cov_suffix in [('.red', '.green'), ('.blue', '.alpha')]:
            id_chan = layer + id_suffix
            cov_chan = layer + cov_suffix
            selected_id = upstream_node.sample(id_chan, bbox[0], bbox[1])
            selected_coverage = upstream_node.sample(cov_chan, bbox[0], bbox[1])

            if selected_id == 0.0 or selected_coverage == 0.0:
                # Seen bg twice?  Select bg.
                if saw_bg:
                    break
                saw_bg = True
                continue

            in_list = selected_id in id_set
            if (add_mode and not in_list) or (rm_mode and in_list):
                return selected_id


#############################################
# Utils - Comma seperated list processing
#############################################

class StringEncoder(object):
    r""" 
    Helper class for all the steps of encoding that need
    to happen in order to get strings through all the levels
    of parsing. 

    raw str: literal names, no escapes, ready for hashing. 
    matte str:  strings are users see them. Backslashes and literal f
                nmatch tokens have escapes
    csv str: comma separated values, with another level of escaping
    nuke str:   brackets have special meaning, so have one more
                level of escaping. 

    Example:
    
    First, we have a name coming in, the raw one. 
        raw str:            \brack*[et]
    We need to process it to the matte string users see
        matte str:          \\brack\*\[et\]
    Then double escapes for CSV. 
        csv string:         \\\\brack\\*\\[et\\]
    Then process brackets for nuke to ignore them. 
        nuke string (out):  \\\\brack\\*\\\[et\\\]

    Get nuke str back from nuke, which will remove a level of escapes. 
        nuke string (in):   \\brack\*\[et\]
    This is not ready for CSV to process:
        csv string:         \\\\brack\\*\\[et\\]
    CSV gives us mattelist name:
        matte str:          \\brack\*\[et\]
    From that we get the raw:
        raw str:            \brack*[et]

    """

    def encode_rawstr_to_mattestr(self, rawstr):
        """ Converts a raw string to a mattelist form """
        escaped_tokens = "\\*?[]"
        mattestr = rawstr
        for token in escaped_tokens:
            mattestr = mattestr.replace(token, "\\%s" % token)
        return mattestr

    def encode_mattestr_to_csv(self, mattestrs):
        """ Converts a mattestr strings to csv. """
        return self._encode_csv(mattestrs)

    def encode_csvstr_to_nukestr(self, csvstr):
        """ Converts a csv-friendly string to one that can be consumed by Nuke """
        return csvstr.replace("[", "\\[").replace("]", "\\]").replace('\\"', '\\\\"')

    def decode_nukestr_to_csv(self, nukestr):
        """ Converts a nuke string to one that can be consumed by CSV 
        getvalue will have stripped escape characters, so we need to restore them. 
        Also need to avoid double-escaping "
        """
        return nukestr.replace("\\", "\\\\").replace('\\\\"', '\\"')

    def decode_csvstr_to_mattestrs(self, csvstr):
        """ Converts a CSV to mattelist form """
        # This is done by CSV's behavior with escapes. 
        return self._decode_csv(csvstr)

    def decode_mattestr_to_raw(self, mattestr):
        """ Converts a mattestr to raw """
        escaped_tokens = "\\*?[]"
        rawstr = mattestr
        for token in escaped_tokens:
            rawstr = rawstr.replace("\\%s" % token, token)
        return rawstr

    def encode_mattestr_to_fnmatch(self, mattestr):
        """ Converts the matte string to an fnmatch pattern.
        Escaped tokens are isntead wrapped in [], as fnmatch
        would like. 
        """
        fn_token = "[]*?"
        pattern = ""

        escaped = False
        for char in mattestr:
            if char == "\\" and not escaped:
                escaped = True
            elif escaped:
                if char in fn_token:
                    pattern += "[%s]" % char
                if char == "\\":
                    pattern += "\\\\"
                escaped = False
            else:
                pattern += char
        return pattern

    def _decode_csv(self, csvstr):
        """ Decodes CSVs into a list of strings. """
        reader = csv.reader([csvstr], quotechar='"', delimiter=',', escapechar="\\", 
            doublequote=False, quoting=csv.QUOTE_ALL, skipinitialspace=True);
        result = []
        for row in reader:
            result += row
        return result

    def _encode_csv(self, rawstrs):
        cleaned_items = []
        need_escape_chars = '"\\'
        need_quotes_characters = ' ,'

        for item in rawstrs:
            need_escape = any(x in item for x in need_escape_chars)
            need_quotes = need_escape or any(x in item for x in need_quotes_characters)

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
        return ", ".join(cleaned_items)


class MatteList(StringEncoder):
    """
        Mattelist is a class for dealing with matte lists, from
        the state stored in the gizmo, through fnmatching, and 
        to the raw state. 

        For the steps of string parsing, see StringEncoder, a 
        separate calss for convenience reasons. 

        To use, instantiate it with either a gizmo, or a string 
        as recieved from a gizmo matte list (nukestr) as the 
        argument. 

    """

    def __init__(self, initializer):
        import nuke
        self.mattes = None

        if type(initializer) is nuke.Gizmo:
            gizmo = initializer
            nukestr = gizmo.knob("matteList").getValue()
        else: #str or in Python 2.7, str or unicode
            nukestr = initializer

        csv = self.decode_nukestr_to_csv(nukestr)
        mattestrs = self.decode_csvstr_to_mattestrs(csv)
        self.mattes = set(mattestrs)
        self._update_raw_mattes()

    def _ensure_utf8(self, string):
        return string if type(string) is str else string.encode("utf-8")

    def add(self, rawstr):
        mattestr = self.encode_rawstr_to_mattestr(rawstr)
        self.mattes.add(mattestr)
        self._update_raw_mattes()

    def remove(self, rawstr):
        mattestr = self.encode_rawstr_to_mattestr(rawstr)
        if mattestr in self.mattes:
            self.mattes.remove(mattestr) # the simple case
        elif mattestr.startswith('<') and mattestr.endswith('>') and self._is_number(mattestr[1:-1]):
            # in matte list by name, but is being removed by number
            num = single_precision(float(mattestr[1:-1]))
            for existing_name in self.raw_mattes:
                if mm3hash_float(existing_name) == num:
                    self.mattes.remove(existing_name)
                    break
        else:
            # in mattelist by number, but is being removed by name
            num_str = "<{:.12g}>".format(mm3hash_float(rawstr))
            if num_str in self.mattes:
                self.mattes.remove(num_str)
        self._update_raw_mattes()

    @property
    def has_wildcards(self):
        """ Checks for wildcards in string that aren't escaped.
        Returns True if a wildcard is found, else False.
        """
        return any(self._name_has_wildcards(x) for x in self.raw_mattes)

    @property
    def IDs(self):
        def _id_from_matte_name(name):
            if name.startswith('<') and name.endswith('>') and self._is_number(name[1:-1]):
                return single_precision(float(name[1:-1]))
            else:
                return mm3hash_float(name)
        return list(map(_id_from_matte_name, self.raw_mattes))

    def expand_wildcards(self, cinfo):
        if not self.has_wildcards:
            return

        manifest = cinfo.parse_manifest()
        old_mattes = self.mattes
        self.mattes = set()
        for mattestr in old_mattes:
            if self._name_has_wildcards(mattestr):

                globbed_wildcard_mattes = self._glob_wildcard_names(mattestr, manifest)
                for globbed_matte in globbed_wildcard_mattes:
                    self.mattes.add( globbed_matte)
            else:
                self.mattes.add(mattestr)
        self._update_raw_mattes()

    @property    
    def to_nukestr(self):
        matte_names_list = list(self.mattes)
        matte_names_list.sort(key=lambda x: x.lower())
        csv = self.encode_mattestr_to_csv(matte_names_list)
        return self.encode_csvstr_to_nukestr(csv)

    def set_gizmo_mattelist(self, gizmo):
        gizmo.knob("matteList").setValue(self.to_nukestr)

    def _update_raw_mattes(self):
        self.raw_mattes = set(
            self.decode_mattestr_to_raw(x)
            for x in self.mattes
        )

    def _is_number(self, string):
        try:
            float(string)
            return True
        except ValueError:
            return False
    
    def _name_has_wildcards(self, name):
        return HAS_WILDCARDS_RE.search(name)

    def _glob_wildcard_names(self, mattestr, manifest):
        """ Returns a set of matches from the wildcard string."""
        match_set = []
        fn_pattern = self.encode_mattestr_to_fnmatch(mattestr)
        for manf in manifest:
            if fnmatch.fnmatchcase(manf, fn_pattern):
                manf = manf if type(manf) is str else manf.encode("utf-8")
                match_set.append(self.encode_rawstr_to_mattestr(manf))
        return match_set


def _modify_mattelist_with_keyer(gizmo, keyed_name, remove):
    ml = MatteList(gizmo)
    if remove:
        ml.remove(keyed_name)
    else:
        ml.add(keyed_name)
    ml.set_gizmo_mattelist(gizmo)


#############################################
# Public - Decryption
#############################################


def decryptomatte_all(ask=True):
    decryptomatte_nodes(nuke.allNodes(), ask)


def decryptomatte_selected(ask=False):
    decryptomatte_nodes(nuke.selectedNodes(), ask)


def decryptomatte_button(node):
    if "." in nuke.thisNode().fullName():
        parent_name = ".".join(nuke.thisNode().fullName().split(".")[:-1])
        with nuke.toNode(parent_name):
            decryptomatte_nodes([node], False)
            return
    with nuke.root():
        decryptomatte_nodes([node], False)


def decryptomatte_nodes(nodes, ask):
    """ Replaces Cryptomatte gizmos with equivelant nodes. """
    gizmos = [n for n in nodes if n.Class() == "Cryptomatte"]
    if not gizmos:
        return

    if not ask or nuke.ask(('Replace %s Cryptomatte gizmos with expression nodes? '
        'Replaced Gizmos will be disabled and selected.') % len(gizmos)):

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
    """ Returns list of new nodes, in order of connections. """
    orig_name = gizmo.name()
    disabled = gizmo.knob("disable").getValue()
    matte_list = gizmo.knob("matteList").value()
    matte_only = gizmo.knob("matteOnly").value()
    expression = gizmo.knob("expression").value()
    matte_output = gizmo.knob("matteOutput").value()
    unpremultiply = gizmo.knob("unpremultiply").value()
    remove_channels = gizmo.knob("RemoveChannels").value()

    # compile list immediate outputs to connect to
    connect_to = []
    for node in gizmo.dependent():
        for i in range(node.inputs()):
            input_node = node.input(i)
            if input_node and input_node.fullName() == gizmo.fullName():
                connect_to.append((i, input_node))

    # Modifiy expression to perform premult.
    if unpremultiply and expression:
        expression = "(%s) / (alpha ? alpha : 1)" % expression

    # Setup expression node.
    expr_node = nuke.nodes.Expression(
        inputs=[gizmo], channel0=matte_output, expr0=expression,
        name="%sExtract" % orig_name, disable=disabled)
    expr_node.addKnob(nuke.nuke.String_Knob(
        'origMatteList', 'Original Matte List', matte_list))
    for knob_name in GIZMO_CHANNEL_KNOBS:
        expr_node.addKnob(nuke.nuke.Channel_Knob(knob_name, "none") )
        expr_node.knob(knob_name).setValue(gizmo.knob(knob_name).value())
        expr_node.knob(knob_name).setVisible(False)
    new_nodes = [expr_node]

    # Add remove channels node, if needed.
    if remove_channels:
        channels2 = matte_output if matte_output != "alpha" else ""
        remove = nuke.nodes.Remove(
            inputs=[expr_node], operation="keep", channels="rgba",
            channels2=channels2, name="%sRemove" % orig_name,
            disable=disabled)
        new_nodes.append(remove)

    # If "matte only" is used, add shuffle node.
    if matte_only:
        shuffle = nuke.nodes.Shuffle(
            name="%sMatteOnly" % orig_name, inputs=[new_nodes[-1]],
            disable=disabled)
        shuffle.knob("in").setValue(matte_output)
        new_nodes.append(shuffle)        

    # Disable original
    gizmo.knob("disable").setValue(True)

    # Reconnect outputs
    for inputID, node in connect_to:
        node.setInput(inputID, new_nodes[-1])
    return new_nodes
