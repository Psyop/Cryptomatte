#
#  Copyright (c) 2014, 2015, Psyop Media Company, LLC
#  Shared with the Cryptomatte Committee- please do not redistribute. 
#

import cryptomatte_utilities as cu

nuke.addKnobChanged(lambda: cu.cryptomatte_keyer_knob_changed_event(
    nuke.thisNode(), nuke.thisKnob()), nodeClass='CryptomatteKeyer')
nuke.addKnobChanged(lambda: cu.cryptomatte_multi_knob_changed_event(
    nuke.thisNode(), nuke.thisKnob()), nodeClass='CryptomatteMulti')

if nuke.GUI:
    toolbar = nuke.menu("Nodes")
    automatte_menu = toolbar.addMenu("Cryptomatte", "cryptomatte_logo.png")
    automatte_menu.addCommand("CryptomatteKeyer", "cu.cryptomatte_keyer_create();")
    automatte_menu.addCommand("CryptomatteMulti", "cu.cryptomatte_multi_create();")
    automatte_menu.addCommand("Decryptomatte All", "cu.decryptomatte_all();")
    automatte_menu.addCommand("Decryptomatte Selection", "cu.decryptomatte_selected();")
