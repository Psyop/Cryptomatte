#
#
#  Copyright (c) 2014, 2015, 2016 Psyop Media Company, LLC
#  See license.txt
#
#

__version__ = "1.1.0"

import nuke
import struct

def setup_cryptomatte_ui():
    if nuke.GUI:
        toolbar = nuke.menu("Nodes")
        automatte_menu = toolbar.addMenu("Cryptomatte", "cryptomatte_logo.png",index=-1)
        automatte_menu.addCommand("Cryptomatte", "import cryptomatte_utilities as cu; cu.cryptomatte_create_gizmo();")
        automatte_menu.addCommand("Decryptomatte All", "import cryptomatte_utilities as cu; cu.decryptomatte_all();")
        automatte_menu.addCommand("Decryptomatte Selection", "import cryptomatte_utilities as cu; cu.decryptomatte_selected();")

def setup_cryptomatte():
    nuke.addKnobChanged(lambda: cryptomatte_knob_changed_event(
        nuke.thisNode(), nuke.thisKnob()), nodeClass='Cryptomatte')


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

        if not node_in:
            return

        exr_metadata_dict = node_in.metadata() or {}

        prefix = "exr/cryptomatte/"
        default_selection = None
        for key, value in exr_metadata_dict.iteritems():
            if not key.startswith(prefix): 
                continue
            numbered_key = key[len(prefix):] # ex: "exr/cryptomatte/ae93ba3/name" --> "ae93ba3/name"
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
        if self.nuke_node.Class() == "Cryptomatte":
            # nuke_node is a keyer gizmo
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

    def parse_manifest(self):
        """ Loads json manifest and unpacks hex strings into floats,
        and converts it to two dictionaries, which map IDs to names and vice versa.
        Also caches the last manifest in a global variable so that a session of selecting
        things does not constantly require reloading the manifest (' ~0.13 seconds for a 
        32,000 name manifest.')
        """
        import json
        import struct

        num = self.selection
        try:
            manifest = json.loads(self.cryptomattes[num].get("manifest", "{}"))
        except:
            manifest = {}
        from_names = {}
        from_ids = {}

        unpacker = struct.Struct('=f')
        packer = struct.Struct("=I")
        for name, value in manifest.iteritems():
            packed = packer.pack(int(value,16))
            packed = packed = '\0' * (4 - len(packed)) + packed
            id_float = unpacker.unpack( packed )[0]
            name_str = str(name)
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


#############################################
# Public - Create Crypto Gizmos
#############################################


def cryptomatte_create_gizmo():
    return nuke.createNode("Cryptomatte") 


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


#############################################
# Public - cryptomatte functions
#############################################


def update_cryptomatte_gizmo(node, force=False):
    cinfo = CryptomatteInfo(node)
    _update_cryptomatte_gizmo(node, CryptomatteInfo(node), force)


def clear_cryptomatte_gizmo(node):
    node.knob("matteList").setValue("")
    cinfo = CryptomatteInfo(node)
    _update_cryptomatte_gizmo(node, cinfo, True)


def update_all_cryptomatte_gizmos():
    return _force_update_all()


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


def _update_gizmo(gizmo, force=False):
    if _cancel_update(gizmo, force):
        return
    cryptomatte_channels = _identify_cryptomattes_in_channels(gizmo)
    if not cryptomatte_channels:
        return
    _set_keyer_channels(gizmo, cryptomatte_channels)
    _set_keyer_expression(gizmo, cryptomatte_channels)


def _force_update_all():
    with nuke.root():
        node_count = 0
        for node in nuke.allNodes():
            if node.Class() == "Cryptomatte":
                node_count = node_count + 1
                cinfo = CryptomatteInfo(node)
                _update_cryptomatte_gizmo(node, cinfo, force=True)

        nuke.message("Updated %s cryptomatte gizmos." % node_count)


def _set_keyer_channels(gizmo, cryptomatte_channels):
    gizmo.knob("previewChannel").setValue(cryptomatte_channels[0])
    gizmo.knob("in00").setValue(cryptomatte_channels[1])


#############################################
# Utils - Update Gizmi 
#############################################


def _set_channels(gizmo, cryptomatte_channels):
    gizmo.knob("cryptoLayer").setValue(cryptomatte_channels[0])
    gizmo.knob("previewChannel").setValue(cryptomatte_channels[0])
    gizmo.knob("in00").setValue(cryptomatte_channels[1])


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


#############################################
# Utils - Build expressions
#############################################


def _set_keyer_expression(gizmo, cryptomatte_channels):
    expression = _build_keyer_expression(cryptomatte_channels)
    gizmo.knob("expression").setValue(expression)


def _build_keyer_expression(channel_list):
    # Build something like this. 
    #
    # the purpose of the first line is an early out 
    # if it's an ID miss and fully opaque (for another ID).
    # It's not stricly necessary but makes it a bit faster. 
    '''
    (uCryptoAsset00.green == 1.0 && uCryptoAsset00.red != ID) ? 0 : (
        uCryptoAsset00.red == ID ? uCryptoAsset00.green : (
            uCryptoAsset00.blue == ID ? uCryptoAsset00.alpha : (
                uCryptoAsset01.red == ID ? uCryptoAsset01.green : (
                    uCryptoAsset01.blue == ID ? uCryptoAsset01.alpha : (
                        uCryptoAsset02.red == ID ? uCryptoAsset02.green : (
                            uCryptoAsset02.blue == ID ? uCryptoAsset02.alpha : 0
                        )
                    )
                )
            )
        )
    )
    '''

    starting_expression = "(key_channel.green == 1.0 && key_channel.red != ID) ? 0 : more_work_needed"
    iterated_expression = "(sub_channel.red == ID ? sub_channel.green : (sub_channel.blue == ID ? sub_channel.alpha : more_work_needed))"
    
    start_channel = channel_list[0]
    sub_channels = list(channel_list)
    sub_channels.remove(start_channel)

    expression = ""
    for channel in sub_channels:
        channel_expression = iterated_expression.replace("sub_channel", channel)
        if not expression:
            expression = channel_expression
        else:
            expression = expression.replace("more_work_needed", channel_expression)
    expression = expression.replace("more_work_needed", "0")
    
    formatted_expression = _format_expression(expression)
    
    starting_expression = starting_expression.replace("key_channel", sub_channels[0])
    full_expression = starting_expression.replace("more_work_needed", formatted_expression)
    return full_expression


def _convert_keyer_expression(expression, value):
    ''' Converts a keyer style expression to a generic expression for use elsewhere '''
    expression = expression.replace("== ID", "== %s" % value)
    expression = expression.replace("!= ID", "!= %s" % value)
    return expression


def _format_expression(expression_in):
    expression = expression_in
    expression = expression.replace("(", "(\n")
    expression = expression.replace(")", ")\n")
    return expression



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


def _set_expression(gizmo, cryptomatte_channels):
    matte_names_text = gizmo.knob("matteList").getValue()
    ID_list = []

    matte_names = _matteList_text_to_set(matte_names_text)

    for name in matte_names:
        if name.startswith("<") and name.endswith(">"):
            ID_value = single_precision( float(name[1:-1]) )
            ID_list.append(ID_value)
        else:
            ID_list.append( mm3hash_float(name) )

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


def _matteList_text_to_set(matte_names_text):
    if matte_names_text:
        matte_names_text = matte_names_text.replace(" ", "")
        return set(matte_names_text.split(","))
    else:
        return set()


def _matteList_modify(gizmo, name, remove):
    def _matteList_set_add(name, matte_names):
        matte_names.add(name)

    def _matteList_set_remove(name, matte_names):
        if name in matte_names:
            matte_names.remove(name)

    def _matteList_set_to_text(gizmo, matte_names):
        matte_names_list = list(matte_names)
        matte_names_list.sort(key=lambda x: x.lower())
        gizmo.knob("matteList").setValue(", ".join(matte_names_list))

    if not name or gizmo.knob("stopAutoUpdate").getValue() == 1.0 :
        return
    matte_names_text = gizmo.knob("matteList").getValue()
    matte_names = _matteList_text_to_set(matte_names_text)
    if remove:
        _matteList_set_remove(name, matte_names)
    else:
        _matteList_set_add(name, matte_names)
    _matteList_set_to_text(gizmo, matte_names)


#############################################
# Public - Decryption
#############################################


def decryptomatte_all():
    decryptomatte_nodes(nuke.allNodes())


def decryptomatte_selected():
    decryptomatte_nodes(nuke.selectedNodes())


def decryptomatte_nodes(nodes):
    gizmos = []

    for node in nodes:
        if node.Class() == "Cryptomatte":
            gizmos.append(node)
    if not gizmos:
        return

    if nuke.ask(('Replace %s Cryptomatte gizmos with expression nodes? '
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
    expr = nuke.nodes.Expression(inputs=[gizmo], channel0="alpha", 
        expr0=expression_str, name="CryptExpr_%s"%matte_name, disable=disabled)
    last_node = expr
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
