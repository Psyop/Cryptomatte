#
#
#  Copyright (c) 2014, 2015, 2016 Psyop Media Company, LLC
#  See license.txt
#
#

__version__ = "1.1.3"

CHANNEL_KNOBS = ["previewChannel", "in00", "in01", "in02", "in03", "in04", "in05", "in06", "in07"]
CRYPTOMATTE_CLASS = "com.Cryptomatte.pyplug.Cryptomatte"

import NatronEngine

from NatronEngine import natron as NE

if not NatronEngine.natron.isBackground():
    from NatronGui import natron as NG
    natron = NG
else:
    natron = NE

import struct
import ctypes

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
        """Take a nuke node, such as a read node or a Cryptomatte node,
        and Reformat metadata into a dictionary, and collect channel
        information."""
        self.cryptomattes = {}
        self.node = node_in
        self.selection = None

        if not node_in:
            return

        if self.node.getPluginID() == CRYPTOMATTE_CLASS:
            manifest_override = node_in.getParam('manifestOverride').get()
            selected_channel = node_in.getParam('cryptoLayer').get()
            channels = self._identify_channels(selected_channel)
            self.cryptomattes[selected_channel] = {'name' : selected_channel, 
                'manifest' : manifest_override, 
                'hash' : 'MurmurHash3_32', 
                'conversion' : 'uint32_to_float32',
                'channels' : channels}
            self.selection = selected_channel
            return
        
        exr_metadata_dict = {}
        
        # TODO: Implement real metadata support once it's available
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

        if self.node.getPluginID() == CRYPTOMATTE_CLASS:
            selection_name = node_in.getParam("cryptoLayer").get()
            if not selection_name:
                return

            valid_selection = self.set_selection(selection_name)
            if not valid_selection and not self.node.getParam("cryptoLayerLock").get():
                self.selection = default_selection

    def is_valid(self):
        """Checks that the selection is valid."""
        if self.selection is None:
            print "Selection was None"
            return False
        if self.selection not in self.cryptomattes:
            print "Selection was not in list of mattes"
            return False
        if "channels" not in self.cryptomattes[self.selection]:
            print "No channels list"
            return False
        if len(self.cryptomattes[self.selection]["channels"]) < 2:
            print "Not enough channels"
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
        if self.node.getPluginID() == CRYPTOMATTE_CLASS:
            # nuke_node is a keyer gizmo
            channel_list = self.node.getAvailableLayers()
        else:
            # nuke_node might a read node
            channel_list = self.node.getAvailableLayers()

        channel_names = [x.getLayerName() for x in channel_list]

        relevant_channels = [x for x in channel_names if x.startswith(name) and x != "Color"]
        
        return sorted(relevant_channels)

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
# Public - cryptomatte Events
#############################################


def paramChangedCallback(thisParam, thisNode, thisGroup, app, userEdited):
    
    param_name = thisParam.getScriptName()

    if param_name in ['cryptoLayer', 'cryptoLayerLock']:
        cinfo = CryptomatteInfo(thisNode)
        _update_cryptomatte_gizmo(thisNode, cinfo)

    elif param_name == 'pickerAdd':
        if _get_knob_channel_value(thisNode.getParam("pickerAdd"), 2) == 0.0:
            return
        cinfo = CryptomatteInfo(thisNode)
        keyed_object = _update_gizmo_keyed_object(thisNode, cinfo, True, "pickerAdd")
        thisNode.getParam("pickerAdd").set(0,0,0,0)
        thisNode.getParam("pickerRemove").set(0,0,0,0)
        if thisNode.singleSelection.get():
            thisNode.matteList.set("")
        _matteList_modify(thisNode, keyed_object, False)
        _update_cryptomatte_gizmo(thisNode, cinfo)

    elif param_name == 'pickerRemove':
        cinfo = CryptomatteInfo(thisNode)
        if _get_knob_channel_value(thisNode.getParam("pickerRemove"), 2) == 0.0:
            return
        keyed_object = _update_gizmo_keyed_object(thisNode, cinfo, True, "pickerRemove")
        thisNode.getParam("pickerAdd").set(0,0,0,0)
        thisNode.getParam("pickerRemove").set(0,0,0,0)
        _matteList_modify(thisNode, keyed_object, True)
        _update_cryptomatte_gizmo(thisNode, cinfo)  

    elif param_name == 'matteList':
        cinfo = CryptomatteInfo(thisNode)
        _update_cryptomatte_gizmo(thisNode, cinfo)
        thisNode.pickerRemove.set(0,0,0,0)
        thisNode.pickerAdd.set(0,0,0,0)

    elif param_name == 'ColorKey':
        # probably superfluous, may remove later
        cinfo = CryptomatteInfo(thisNode)
        _update_gizmo_keyed_object(thisNode, cinfo)

    elif param_name == 'clear':
        clear_cryptomatte_gizmo(thisNode)

    elif param_name == 'forceUpdate':
        update_cryptomatte_gizmo(thisNode, force=True)

    elif param_name == 'forceUpdateAll':
        _force_update_all(app)

    elif param_name == 'unloadManifest':
        unload_manifest(app, thisNode)

    
def inputChangedCallback(inputIndex, thisNode, thisGroup, app):
    cinfo = CryptomatteInfo(thisNode)
    _update_cryptomatte_gizmo(thisNode, cinfo)



#############################################
# Public - cryptomatte functions
#############################################


def update_cryptomatte_gizmo(node, force=False):
    cinfo = CryptomatteInfo(node)
    _update_cryptomatte_gizmo(node, CryptomatteInfo(node), force)


def clear_cryptomatte_gizmo(node):
    node.getParam("matteList").set("")
    cinfo = CryptomatteInfo(node)
    _update_cryptomatte_gizmo(node, cinfo, True)


def update_all_cryptomatte_gizmos(app):
    return _force_update_all(app)



#############################################
# Utils - Update Gizmi 
#       (gizmi is the plural of gizmo)
#############################################


def _cancel_update(gizmo, force):
    try:
        stopAutoUpdate = gizmo.getParam("stopAutoUpdate").get()
    except:
        # This happens sometimes on creation. I don't really get it, but this seems to fix it.
        return True
    if (not force and stopAutoUpdate == 1.0): 
        return True
    else:
        return False


def _force_update_all(app):
    node_count = 0
    for node in app.getChildren():
        if node.getPluginID() == CRYPTOMATTE_CLASS:
            node_count = node_count + 1
            cinfo = CryptomatteInfo(node)
            _update_cryptomatte_gizmo(node, cinfo, force=True)

    natron.informationDialog("Info", "Updated {0} cryptomatte nodes.".format(node_count))



#############################################
# Utils - Update Gizmi 
#############################################

def _set_channels(gizmo, channels):
    
    gizmo.getParam("cryptoLayer").set(channels[0])

    for i, knob_name in enumerate(CHANNEL_KNOBS):
        channel = channels[i] if i < len(channels) else "none"
        param = gizmo.getParam(knob_name)
        if param.getTypeName() == "Choice":
            options = param.getOptions()
            if channel in options:
                param.set(options.index(channel))
            elif "None" in options:
                param.set(options.index("None"))
            else:
                param.set(0)
        elif param.getTypeName() == "String":
            param.set(channel)


def _update_cryptomatte_gizmo(gizmo, cinfo, force=False):
    
    if _cancel_update(gizmo, force):
        print "Update cancelled"
        return
    if not cinfo.is_valid():
        print "Invalid info"
        return
    cryptomatte_channels = cinfo.get_channels()
    if not cryptomatte_channels:
        print "No channels"
        return
    _set_channels(gizmo, cryptomatte_channels)
    _set_expression(gizmo, cryptomatte_channels)


#############################################
# Utils - Build expressions
#############################################


def _set_keyer_expression(gizmo, cryptomatte_channels):
    expression = _build_keyer_expression(cryptomatte_channels)
    gizmo.getParam("expression").set(expression)


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

    starting_expression = "(Cs_key_channel[1] == 1.0 && Cs_key_channel[0] != ID) ? 0 : more_work_needed"
    iterated_expression = "(Cs_sub_channel[0] == ID ? Cs_sub_channel[1] : (Cs_sub_channel[2] == ID ? As_sub_channel : more_work_needed))"
    
    start_channel = channel_list[0]
    sub_channels = list(channel_list)
    sub_channels.remove(start_channel)

    expression = ""
    for channel in sub_channels:
        channel_expression = iterated_expression.replace("_sub_channel", channel)
        if not expression:
            expression = channel_expression
        else:
            expression = expression.replace("more_work_needed", channel_expression)
    expression = expression.replace("more_work_needed", "0")
    
    formatted_expression = _format_expression(expression)
    
    starting_expression = starting_expression.replace("_key_channel", sub_channels[0])
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


def unload_manifest(app, node):
    source_node = None
    if node.getPluginID() == CRYPTOMATTE_CLASS:
        source_node = node.getInput(0)
        if not source_node:
            natron.warningDialog('Warning', 'Cryptomatte is not plugged into anything')
            return
    else:
        source_node = node

    cinfo = CryptomatteInfo(node)
    if not cinfo.is_valid():
        natron.warningDialog('Warning', "Gizmo's cryptomatte selection is not valid or no cryptomattes are available. ")
        return

    names_to_IDs = cinfo.parse_manifest();

    if not names_to_IDs:
        natron.warningDialog('Warning', 'No Cryptomatte manifest was found in the input. ')
        return

    new_keyers = []
    response = natron.questionDialog('Question', 'There are {0} named mattes in the manifest, are you sure you want to create keyer nodes for all of them?'.format(len(names_to_IDs)))
    if response == NatronEngine.Natron.StandardButtonEnum.eStandardButtonYes:

        with nuke.root():
            dot = app.createNode("fr.inria.built-in.Dot")
            dot.setInput(0, source_node)

            progress = 0
            for name, metadata_ID in names_to_IDs.iteritems():
                keyer = nuke.nodes.Cryptomatte(name="ck_%s" % name, matteList=name, matteOnly=True)
                keyer = app.createNode("com.Cryptomatte.pyplug.Cryptomatte")
                keyer.setLabel("ck_%s" % name)
                keyer.setInput(0, dot)
                keyer.getParam('matteList').set(name)
                keyer.getParam('matteOnly').set(True)
                _update_cryptomatte_gizmo(keyer, cinfo)
                new_keyers.append(keyer)
                progress = progress + 1

    return new_keyers


#############################################
# Utils - Build Expressions
#############################################


def _set_expression(node, cryptomatte_channels):
    matte_names_text = node.matteList.get()
    matte_names_text = matte_names_text.encode('ascii', 'ignore')
    ID_list = []

    matte_names = _matteList_text_to_set(matte_names_text)


    for name in matte_names:
        if name.startswith("<") and name.endswith(">"):
            ID_value = single_precision( float(name[1:-1]) )
            ID_list.append(ID_value)
        else:
            ID_list.append( mm3hash_float(name) )


    ID_list_double = [repr(ctypes.c_double(ctypes.c_float(v).value).value) for v in ID_list]

    seexpr_input_channels = []
    for c in range(len(cryptomatte_channels)):
        if c == 0:
            this_channel = "Cs"
        else:
            this_channel = "Cs" + str(c + 1)
        seexpr_input_channels.append(this_channel)

    gmicxpr_input_channels = ["previewChanndl", "i"]
    expression = _build_extraction_expression(gmicxpr_input_channels, ID_list_double)

    node.expression.set(expression)


def _build_condition(condition, IDs):
    conditions = []
    for ID in IDs:
        conditions.append( condition.replace("ID", str(ID)) )
    return " || ".join(conditions)


def _build_extraction_expression(channel_list, IDs):
    if not IDs:
        return "0"
        
    iterated_expression = "({red_condition} ? sub_channel[1] : 0.0) + ({blue_condition} ? sub_channel[3] : 0.0) + more_work_needed"
    
    subcondition_red =  "sub_channel[0] == ID"
    subcondition_blue = "sub_channel[2] == ID"

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

    # 
    expression = expression.replace("[", "")
    expression = expression.replace("]", "")
    expression = expression.replace("{", "(")
    expression = expression.replace("}", ")")

    return expression



#############################################
# Utils - Manifest Processing Helpers
#############################################


def set_text_knob(node, text_knob_name, text):
    if not text_knob_name:
        return
    knob = node.getParam(text_knob_name)
    if knob:
        node.getParam(text_knob_name).set(text)


def _get_knob_channel_value(knob, c_index):
    try:
        return knob.get()[c_index]
    except:
        return 0.0

def _update_gizmo_keyed_object(node, cinfo, force=False, color_knob_name="ColorKey", text_knob_name="keyedName"):
    if _cancel_update(node, force):
        return None
    if not node.getParam(text_knob_name):
        return None

    ID_value = _get_knob_channel_value(node.getParam(color_knob_name), 2)

    if ID_value == 0.0:
        set_text_knob(node, text_knob_name, "Background (Value is 0.0)")
        return None

    name = cinfo.id_to_name(ID_value)

    if name:
        set_text_knob(node, text_knob_name, name)
        return name

    set_text_knob(node, text_knob_name, "ID value not in manifest.")
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


def _matteList_modify(node, name, remove):
    def _matteList_set_add(name, matte_names):
        matte_names.add(name)

    def _matteList_set_remove(name, matte_names):
        if name in matte_names:
            matte_names.remove(name)

    def _matteList_set_to_text(node, matte_names):
        matte_names_list = list(matte_names)
        matte_names_list.sort(key=lambda x: x.lower())
        node.getParam("matteList").set(", ".join(matte_names_list))

    if not name or node.getParam("stopAutoUpdate").get() == 1.0 :
        return
    matte_names_text = node.getParam("matteList").get()
    matte_names = _matteList_text_to_set(matte_names_text)
    if remove:
        _matteList_set_remove(name, matte_names)
    else:
        _matteList_set_add(name, matte_names)
    _matteList_set_to_text(node, matte_names)


#############################################
# Public - Decryption
#############################################

def decryptomatte_all(app, ask=True):
    decryptomatte_nodes(app, app.getChildren(), ask)

def decryptomatte_selected(app, ask=False):
    decryptomatte_nodes(app, app.getSelectedNodes(), ask)

def decryptomatte_nodes(app, nodes, ask):
    gizmos = []

    for node in nodes:
        if node.getPluginID() == CRYPTOMATTE_CLASS:
            gizmos.append(node)
    if not gizmos:
        return

    if ask:
        reply = natron.questionDialog("Question", 'Replace {0} Cryptomatte nodes with expression nodes? Replaced nodes will be disabled and selected.'.format(len(gizmos)))
        if not reply == NatronEngine.Natron.StandardButtonEnum.eStandardButtonYes:
            return

    for gizmo in gizmos:
        _decryptomatte(app, gizmo)

    app.setSelection(gizmos)


#############################################
# Decryptomatte helpers
#############################################


def _decryptomatte(app, gizmo):
    def _decryptomatte_get_name(gizmo):
        name_out = gizmo.getParam("matteList").get()
        name_out.replace(", ", "_")
        if len(name_out) > 100:
            name_out = name_out[0:100]
        return name_out

    matte_name = _decryptomatte_get_name(gizmo)
    expression_str = gizmo.getParam("expression").get()

    remove_channels = gizmo.getParam("removeChannels").get()
    matte_only = gizmo.getParam("matteOnly").get()

    connect_to = []

    gizmo_script_name = gizmo.getScriptName()

    all_nodes = app.getChildren()

    for node in all_nodes:
        num_inputs = node.getMaxInputCount()
        for iid in range(0, num_inputs):
            inode = node.getInput(iid)
            if inode:
                if inode.getScriptName() == gizmo_script_name:
                    connect_to.append((node, iid))

    disabled = gizmo.getParam("disableNode").get()

    expression_channels = []
    for c in CHANNEL_KNOBS[1:]:
        param = gizmo.getParam(c)
        options = param.getOptions()
        channel = options[param.get()]
        if channel not in ["", 'None']:
            expression_channels.append(channel)

    preview_channel = gizmo.getParam(CHANNEL_KNOBS[0]).get()
    
    gizmo.getParam("disableNode").set(True)

    group_node = app.createNode("fr.inria.built-in.Group")
    group_node.channels = group_node.createPageParam("channels", "Channels")

    crypto_layer_param = group_node.createStringParam("cryptoLayer", "cryptoLayer")
    crypto_layer_param.setType(NatronEngine.StringParam.TypeEnum.eStringTypeDefault)

    # Add the param to the page
    group_node.channels.addParam(crypto_layer_param)

    # Set param properties
    crypto_layer_param.setHelp("The name of the main Cryptomatte channel")
    crypto_layer_param.setAddNewLine(True)
    crypto_layer_param.setAnimationEnabled(True)
    crypto_layer_param.set(preview_channel)
    group_node.cryptoLayer = crypto_layer_param
    del crypto_layer_param
    
    input_node = app.createNode("fr.inria.built-in.Input", -1, group_node)
    input_node.setPosition(0.0, 0.0)
    output_node = app.createNode("fr.inria.built-in.Output", -1, group_node)
    output_node.setPosition(0.0, 600.0)

    group_node.connectInput(0, gizmo)
    
    expression_nodes = []
    i = 0
    for c in expression_channels:
        h_pos = i * 200.0 - len(expression_channels) * 100.0 + 50.0
        shuffle_node = app.createNode("net.sf.openfx.ShufflePlugin", -1, group_node)
        shuffle_node.setPosition(h_pos, 100.0)

        shuffle_node.connectInput(0, input_node)
        shuffle_node.connectInput(1, input_node)

        channel_param_name = "in" + str(i).rjust(2, "0")

        
        for chan in ['R', 'G', 'B', 'A']:
            shuffle_node.getParam('output' + chan).setExpression("try:\n\treturn thisParam.getOptions().index(\"B.\" + thisGroup.getParam(\"" + channel_param_name + "\").get() + \"." + chan + "\")\nexcept:\n\treturn thisParam.getOptions().index(\"0\")", True, 0)

        expression_node = app.createNode("net.sf.cimg.CImgExpression", -1, group_node)
        expression_node.setPosition(h_pos, 200.0)
                
        expression_node.getParam("expression").set(expression_str)
        expression_node.getParam("NatronOfxParamProcessA").set(True)
        expression_node.connectInput(0, shuffle_node)

        channel_param = group_node.createStringParam(channel_param_name, channel_param_name)
        channel_param.setDefaultValue("")
        channel_param.restoreDefaultValue()
        channel_param.set(c)

        # Add the param to the channels page
        group_node.channels.addParam(channel_param)

        # Set param properties
        channel_param.setAddNewLine(True)
        channel_param.setAnimationEnabled(False)
        setattr(group_node, channel_param_name, channel_param)
        del channel_param

        expression_node.setLabel("CryptExpr_%s"%matte_name + channel_param_name)
        expression_node.getParam("disableNode").set(disabled)
        expression_nodes.append(expression_node)
        i += 1

    merge_node = app.createNode("net.sf.openfx.MergePlus", -1, group_node)
    merge_node.setPosition(0.0, 300.0)
    i = 0
    for e in expression_nodes:
        merge_node.connectInput(i, e)
        i += 1

        # Skip mask
        if i == 2:
            i += 1

    last_node = merge_node
    if matte_only:
        shuffle_node = app.createNode("net.sf.openfx.ShufflePlugin")
        shuffle_node.setPosition(0.0, 400.0)
        shuffle_node.connectInput(0, last_node)
        options = shuffle_node.getParam("outputR").getOptions()
        alpha_index = options.index('B.a')
        for param_name in ["outputR", "outputG", "outputB", "outputA"]:
            shuffle_node.getParam(param_name).set(alpha_index)

        last_node = shuffle_node

    output_node.connectInput(0, merge_node)

    group_node.getParam("disableNode").set(disabled)

    for node, inputID in connect_to:
        node.connectInput(inputID, last_node)


def createInstanceExt(app, group):
    group.onParamChanged.set('Cryptomatte.paramChangedCallback')
    group.onInputChanged.set('Cryptomatte.inputChangedCallback')