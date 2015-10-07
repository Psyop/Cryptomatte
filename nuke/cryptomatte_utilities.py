#
#  Copyright (c) 2014, 2015, Psyop Media Company, LLC
#  Shared with the Cryptomatte Committee- please do not redistribute. 
#


import nuke

MANIFEST_PREFIX = r"exr/manifest/"


#############################################
# Public - Create Crypto Gizmos
#############################################


def test_manifest(node_to_check=None):
    # quick and dirty manifest testing tool
    node = node_to_check;
    if not node:
        node = nuke.selectedNode()
    if not node:
        print "no node specified or selected"
        return

    id_name_pairs = parse_metadata(node)

    ids = {}
    errors = [];
    collisions = []
    for id, name in id_name_pairs:
        if djb2_hash(name) != id:
            errors.append("computed ID doesn't match manifest ID: ", id, djb2_hash(name))
        else:
            if id in ids:
                collisions.append("colliding: %s %s" % ids[id], name)
            ids[id] = name

    print "Tested %s" % node.name()
    print len(errors), "non-matching IDs between python and c++."
    for error in errors:
        print error
    print len(collisions), "hash collisions in manifest."
    for error in errors:
        print error

    return errors, collisions


#############################################
# Public - Create Crypto Gizmos
#############################################

def cryptomatte_keyer_create():
    nuke.createNode("CryptomatteKeyer"); 

def cryptomatte_multi_create():
    nuke.createNode("CryptomatteMulti"); 

#############################################
# Public - cryptomatte_keyer Events
#############################################

def cryptomatte_keyer_knob_changed_event(node = None, knob = None):
    if knob.name() == "inputChange":
        _update_gizmo(node)
        _update_gizmo_keyed_object(node)
    if knob.name() == "ColorKey":
        _update_gizmo_keyed_object(node)

#############################################
# Public - cryptomatte_multi Events
#############################################

def cryptomatte_multi_knob_changed_event(node = None, knob = None):
    if knob.name() == "inputChange":
        update_cryptomatte_multi_gizmo(node)

    elif knob.name() == "pickerAdd":
        if node.knob("pickerAdd").getValue()[2] == 0.0:
            return
        keyed_object = _update_gizmo_keyed_object(node, True, "pickerAdd")
        node.knob("pickerRemove").setValue([0,0,0])
        _matteList_modify(node, keyed_object, False)
        update_cryptomatte_multi_gizmo(node)

    elif knob.name() == "pickerRemove":
        if node.knob("pickerRemove").getValue()[2] == 0.0:
            return
        keyed_object = _update_gizmo_keyed_object(node, True, "pickerRemove")
        node.knob("pickerAdd").setValue([0,0,0])
        _matteList_modify(node, keyed_object, True)
        update_cryptomatte_multi_gizmo(node)    

    elif knob.name() == "matteList":
        update_cryptomatte_multi_gizmo(node)
        node.knob("pickerRemove").setValue([0,0,0])
        node.knob("pickerAdd").setValue([0,0,0])

    elif knob.name() == "ColorKey":
        # probably superfluous, may remove later
        _update_gizmo_keyed_object(node)

#############################################
# Public - cryptomatte_keyer functions
#############################################


def update_cryptomatte_gizmo(node, force=False):
    _update_gizmo(node, force)
    _update_gizmo_keyed_object(node, force)


def update_all_cryptomatte_gizmos():
    return _force_update_all()


def unload_manifest(node):
    source_node = None
    if node.Class() == "CryptomatteKeyer":
        source_node = node.input(0)
        if not source_node:
            nuke.message('Cryptomatte Keyer is not plugged into anything')
            return
    else:
        source_node = node

    ID_name_pairs = parse_metadata(node)
    if not ID_name_pairs:
        nuke.message('No Cryptomatte manifest was found in the input. ')
        return

    new_keyers = []
    if nuke.ask('There are %s named mattes in the manifest, are you sure you want to create keyer nodes for all of them?' % len(ID_name_pairs)):
        with nuke.root():
            dot = nuke.nodes.Dot()
            dot.setInput(0, source_node)

            progress = 0
            task = nuke.ProgressTask("Unloading Manifest")
            for metadata_ID, name in ID_name_pairs:
                if task.isCancelled():
                    break
                task.setMessage("Creating Cryptomatte Keyer for %s" % name)
                task.setProgress(int(float(progress) / float(len(ID_name_pairs)) * 100))
                keyer = nuke.nodes.cryptomatte_keyer(name="ck_%s" % name, 
                                                     ColorKey=metadata_ID, 
                                                     matteOnly=True, 
                                                     keyedName=name)
                keyer.setInput(0, dot)
                new_keyers.append(keyer)
                progress = progress + 1

    return new_keyers

def clear_cryptomatte_gizmo(node):
    # _cryptomatte_send_statistics(['button', 'keyer', 'clear'])
    node.knob("ColorKey").setValue([0.0,0.0,0.0,0.0])
    _update_gizmo(node, True)

#############################################
# Public - cryptomatte_multi functions
#############################################

def update_cryptomatte_multi_gizmo(node, force=False):
    _update_gizmo_multi(node, force)

def clear_cryptomatte_multi_gizmo(node):
    # _cryptomatte_send_statistics(['button', 'multi', 'clear'])
    node.knob("matteList").setValue("")
    _update_gizmo_multi(node, True)


#############################################
# Public - Manifest Processing
#############################################

'''
Hashes are computed as single precision floats in c++. 
They are then written out as single precision (32 bit) floats in the images.
Python has no single precision float type, floats in python are doubles (64 bit).
The metadata stores the hash values as decimals strings. Therein lies the rub.
    There is no good way to maintain exact precision with decimal numbers.
    Instead, we just make sure there is *enough* precision by having extra decimal places.
    To allow a direct == comparison back to the values in the image, or the color picked values,
    We simple decrease the precision back to single precision. 
    Python's array module has a 32 bit float type that performs this reduction in precision. 
'''

def single_precision(float_in):
    import array
    return array.array("f", [float_in])[0]

def parse_metadata(gizmo, sort_by_name=True, searchForNumber=None):
    doing_search = searchForNumber != None
    exr_metadata_dict = gizmo.metadata()

    ID_name_pairs = []

    if exr_metadata_dict.has_key("exr/cryptoManifest"):
        # has new style (all in one string) metadata. For old metadata, see below.
        manifest_as_string = exr_metadata_dict["exr/cryptoManifest"]
        for manifest_entry in manifest_as_string.split("<hash>"):
            hash_name_pair = manifest_entry.split("<name>")
            if len(hash_name_pair) == 2:
                ID = single_precision( float(hash_name_pair[0]) )
                name = hash_name_pair[1]
                if doing_search and ID == searchForNumber:
                    return name
                else:
                    ID_name_pairs.append((ID, name))
    else:
        # old metadata, left here for backwards compatibility with existing images. 
        for key in exr_metadata_dict:
            ID = _metadata_key_to_number(key)
            if ID:            
                name = exr_metadata_dict[key]
                if doing_search and ID == searchForNumber:
                    return name
                ID_name_pairs.append((ID, name))

    if sort_by_name:
        ID_name_pairs.sort(key=lambda tup: tup[1].lower())

    if doing_search:
        return None
    else:
        return ID_name_pairs


#############################################
# New DJB2 & friends
#############################################

def djb2_hash(name):
    import struct
    max_64_int = 18446744073709551616 # 2^64    
    hash_64 = 5381    
    for k in name:
        hash_64 = ((hash_64 << 5) + hash_64 + ord(k)) % max_64_int
    for i in range(16):
        hash_64 = ((hash_64 << 5) + hash_64) % max_64_int

    mantissa = hash_64 & pow(2, 23)-1
    exponent = ((hash_64 >> 24) % pow(2, 8))
    exponent = max(exponent, 1)
    exponent = min(exponent, 254)
    exponent = exponent << 23
    sign = (hash_64 >> 32) % 2
    float_bits = exponent | mantissa

    packed = struct.pack('@l', float_bits)
    if sign == 1:
        return -struct.unpack('@f', packed)[0]
    elif sign == 0:
        return struct.unpack('@f', packed)[0]

#############################################
# Utils - Update Gizmi 
#       (gizmi is the plural of gizmo)
#############################################

def _cancel_update(gizmo, force):
    try:
        stopAutoUpdate = gizmo.knob("stopAutoUpdate").getValue()
    except:
        # # This happens sometimes on creation. I don't really get it, but this seems to fix it.
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
            if node.Class() == "CryptomatteKeyer":
                node_count = node_count + 1
                _update_gizmo(node, force=True)
            if node.Class() == "CryptomatteMulti":
                node_count = node_count + 1
                _update_gizmo_multi(node, force=True)

        nuke.message("Updated %s cryptomatte gizmos." % node_count)


def _set_keyer_channels(gizmo, cryptomatte_channels):
    gizmo.knob("previewChannel").setValue(cryptomatte_channels[0])
    gizmo.knob("in00").setValue(cryptomatte_channels[1])




#############################################
# Utils - Update Multi Gizmi 
#############################################

def _set_multi_channels(gizmo, cryptomatte_channels):
    gizmo.knob("previewChannel").setValue(cryptomatte_channels[0])
    gizmo.knob("in00").setValue(cryptomatte_channels[1])


def _update_gizmo_multi(gizmo, force=False):
    if _cancel_update(gizmo, force):
        return
    cryptomatte_channels = _identify_cryptomattes_in_channels(gizmo)
    if not cryptomatte_channels:
        return
    _set_multi_channels(gizmo, cryptomatte_channels)
    _set_multi_expression(gizmo, cryptomatte_channels)



#############################################
# Utils - Identify channels
#############################################

def _identify_cryptomattes_in_channels(node_in):
    # This could be construed as paranoid code. 
    channel_list = []
    if "crypto" in node_in.Class().lower():
        channel_list = node_in.node('Input1').channels()
    else:
        # Allows read nodes to use this function
        channel_list = node_in.channels()

    suffix = ".red"
    channel_list_stripped = [x[:-len(suffix)] for x in channel_list if (x.endswith(suffix) and x[:-len(suffix)] + ".green" in channel_list)]

    candidates = []
    candidate_subchannels = {}

    for channel in channel_list_stripped:
        if (channel + "00") not in  channel_list_stripped:
            continue
        check_channel = channel + "00"
        crypto_depth = 0
        sub_channels = [channel]
        while check_channel in channel_list_stripped:
            sub_channels.append(check_channel)
            crypto_depth = crypto_depth + 1
            check_channel = "%s%02d" % (channel, crypto_depth)
        candidates.append((channel, crypto_depth))
        candidate_subchannels[channel] = sub_channels
    
    best_score = 0
    winning_channel = ""
    for candidate in candidates:
        if candidate[1] > best_score:
            best_score = candidate[1] 
            winning_channel = candidate[0]

    if winning_channel:
        return candidate_subchannels[winning_channel]
    else:
        return []



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
    expression = expression.replace("== ID", "== %s" % single_precision(value))
    expression = expression.replace("!= ID", "!= %s" % single_precision(value))
    return expression


def _format_expression(expression_in):
    expression = expression_in
    expression = expression.replace("(", "(\n")
    expression = expression.replace(")", ")\n")
    return expression



#############################################
# Utils - Build Expressions for multi
#############################################


def _set_multi_expression(gizmo, cryptomatte_channels):
    matte_names_text = gizmo.knob("matteList").getValue()
    ID_list = []

    matte_names = _matteList_text_to_set(matte_names_text)

    for name in matte_names:
        if name.startswith("<") and name.endswith(">"):
            ID_value = single_precision( float(name[1:-1]) )
            ID_list.append(ID_value)
        else:
            ID_list.append( djb2_hash(name) )

    expression = _build_multi_expression(cryptomatte_channels, ID_list)

    gizmo.knob("expression").setValue(expression)


def _build_multi_condition(condition, IDs):
    conditions = []
    for ID in IDs:
        conditions.append( condition.replace("ID", str(ID)) )
    return " || ".join(conditions)


def _build_multi_expression(channel_list, IDs):
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
        condition_r = _build_multi_condition(subcondition_red, IDs)
        condition_b = _build_multi_condition(subcondition_blue, IDs)

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
# Utils - Manifest Processing - Private
#############################################

def _metadata_key_to_number(key_in):
    if key_in.startswith(MANIFEST_PREFIX):
        number_string = key_in[len(MANIFEST_PREFIX):]
        numeric_value = float(number_string)
        return single_precision(numeric_value)
    else:
        return None


def _get_color_key_value(gizmo, color_knob_name):
    color = gizmo.knob(color_knob_name).getValue()
    if type(color) is list:
        return single_precision(color[2])
    if type(color) is float:
        return single_precision(color)
    else:
        return 0.0


def set_text_knob(gizmo, text_knob_name, text):
    if not text_knob_name:
        return
    knob = gizmo.knob(text_knob_name)
    if knob:
        gizmo.knob(text_knob_name).setValue(text)


def _update_gizmo_keyed_object(gizmo, force=False, color_knob_name="ColorKey", text_knob_name="keyedName"):
    if _cancel_update(gizmo, force):
        return None
    if not gizmo.knob(text_knob_name):
        return None

    ID_value = _get_color_key_value(gizmo, color_knob_name)

    if ID_value == 0.0:
        set_text_knob(gizmo, text_knob_name, "Background (Value is 0.0)")
        return None

    name = parse_metadata(gizmo, False, ID_value)
    if name:
        set_text_knob(gizmo, text_knob_name, name)
        return name

    set_text_knob(gizmo, text_knob_name, "ID value not in manifest.")
    return "<%s>" % single_precision(ID_value)



#############################################
# Utils - Comma seperated list processing
#############################################

def _matteList_text_to_set(matte_names_text):
    if matte_names_text:
        matte_names_text = matte_names_text.replace(" ", "")
        return set(matte_names_text.split(","))
    else:
        return set()


def _matteList_set_add(name, matte_names):
    matte_names.add(name)


def _matteList_set_remove(name, matte_names):
    if name in matte_names:
        matte_names.remove(name)


def _matteList_set_to_text(gizmo, matte_names):
    matte_names_list = list(matte_names)
    matte_names_list.sort(key=lambda x: x.lower())
    gizmo.knob("matteList").setValue(", ".join(matte_names_list))


def _matteList_modify(gizmo, name, remove=False):
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
    decryptomatte_nodes(nuke.allNodes(), "all")

def decryptomatte_selected():
    decryptomatte_nodes(nuke.selectedNodes(), "selected")

def decryptomatte_nodes(nodes, stat_name="all"):
    keyer_gizmos = []
    multi_gizmos = []

    for node in nodes:
        if node.Class() == "CryptomatteKeyer":
            keyer_gizmos.append(node)
        if node.Class() == "CryptomatteMulti":
            multi_gizmos.append(node)
    if not keyer_gizmos and not multi_gizmos:
        return

    if nuke.ask('Replace %s Cryptomatte gizmos with expression nodes? \
Replaced Gizmos will be disabled and selected.' % (
        len(keyer_gizmos) + len(multi_gizmos))):

        for gizmo in keyer_gizmos:
            _decrypt_keyer(gizmo)
        for gizmo in multi_gizmos:
            _decrypt_multi(gizmo)

        for node in nuke.selectedNodes():
            node.knob("selected").setValue(False)

        for gizmo in keyer_gizmos:
            gizmo.knob("selected").setValue(True)
        for gizmo in multi_gizmos:
            gizmo.knob("selected").setValue(True)


#############################################
# Private - Decryption helpers
#############################################

def _keyer_decrypto_name(gizmo):
    keyed_name = gizmo.knob("keyedName").value()
    return keyed_name

def _multi_decrypto_name(gizmo):
    name_out = gizmo.knob("matteList").value()
    name_out.replace(", ", "_")
    if len(name_out) > 100:
        name_out = name_out[0:100]
    return name_out

def _decrypt_keyer(gizmo):
    value = -1.0
    keyerValue = gizmo.knob("ColorKey").value()
    if len(keyerValue) >= 3:
        value = keyerValue[2]
    else:
        value = keyerValue[0]
    expression = _convert_keyer_expression(gizmo.knob("expression").value(), value)
    _decryptomatte_gizmo(gizmo, _keyer_decrypto_name(gizmo), expression)

def _decrypt_multi(gizmo):
    expression = gizmo.knob("expression").value()
    _decryptomatte_gizmo(gizmo, _multi_decrypto_name(gizmo), expression)


def _decryptomatte_gizmo(gizmo, matteName, expression_str):
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
        expr0=expression_str, name="CryptExpr_%s"%matteName, disable=disabled)
    last_node = expr
    if matte_only:
        shuffler = nuke.nodes.Shuffle(inputs=[last_node], red="alpha", 
            green="alpha", blue="alpha", name="CryptShuf_%s"%matteName, disable=disabled)
        last_node = shuffler
    if remove_channels:
        remover = nuke.nodes.Remove(inputs=[last_node], operation="keep", 
            channels="rgba", name="CryptRemove_%s"%matteName, disable=disabled)
        last_node = remover
    for node, inputID in connect_to:
        node.setInput(inputID, last_node)

    gizmo.knob("disable").setValue(True)


#############################################
# Private - Usage Statistics
#############################################

# def _cryptomatte_send_statistics(names_list, sample_rate = 1):
#     if type(names_list) is not list:
#         return

#     try:
#         if not nuke.GUI:
#             return
#         import psyop.env as env
#         stats_key_list = []
#         stats_key_list.append( "cryptomatte" )
#         for name in names_list:
#             stats_key_list.append(name)
#         stats_key_list.append(env.OFFICE)
#         stats_key = ".".join(stats_key_list)

#         graphite = env.statsd_client
#         graphite.increment(stats_key, sample_rate)
#     except:
#         pass
