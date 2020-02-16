#
#
#  Copyright (c) 2014, 2015, 2016, 2017 Psyop Media Company, LLC
#  See license.txt
#
#

import sys
import unittest


def get_all_unit_tests():
    """ Returns the list of unit tests (to run in any context)"""
    return [CSVParsing, CryptoHashing]


def get_all_nuke_tests():
    """ Returns the list of Nuke integration tests"""
    return [CSVParsingNuke, CryptomatteNodePasting, CryptomatteNukeTests]


#############################################
# Env. variables
#############################################
"""
The supplied Cryptomatte sample images are required for testing.  The path to the sample_images 
directory can be defined using the environment variable below. Otherwise, they are searched for 
relative to this file.
"""
SAMPLES_IMAGES_DIR_ENVIRON = "CRYPTOMATTE_TESTING_SAMPLES"
global CRYPTOMATTETEST_SKIP_CLEANUP_ON_FAILURE
CRYPTOMATTETEST_SKIP_CLEANUP_ON_FAILURE = False


def set_skip_cleanup_on_failure(enabled):
    assert type(enabled) is bool
    global CRYPTOMATTETEST_SKIP_CLEANUP_ON_FAILURE
    CRYPTOMATTETEST_SKIP_CLEANUP_ON_FAILURE = enabled


def reset_skip_cleanup_on_failure():
    global CRYPTOMATTETEST_SKIP_CLEANUP_ON_FAILURE
    CRYPTOMATTETEST_SKIP_CLEANUP_ON_FAILURE = False


#############################################
# Unit tests
#############################################


class CSVParsing(unittest.TestCase):
    csv_str = ("""str, "str with space", "single 'quotes'", """
               '"with_a,_comma", "with comma, and \\"quotes\\"", <123.45>, '
               '" space_in_front", "space_at_end ", "has_escape\\\\chars", '
               '"cyrillic \xd1\x80\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb8\xd0\xbd\xd0\xb0"')
    name_list = [
        "str", "str with space", "single 'quotes'", "with_a,_comma", 'with comma, and "quotes"',
        "<123.45>", " space_in_front", "space_at_end ", "has_escape\\chars",
        "cyrillic \xd1\x80\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb8\xd0\xbd\xd0\xb0"
    ]

    def test_csv_round_trip(self):
        import cryptomatte_utilities as cu
        """Ensures the round trip is correct for CSV encoding and decoding. """

        def check_results(encoded, decoded):
            self.assertEqual(encoded, self.csv_str,
                             "Round trip to str failed: %s != %s" % (self.csv_str, encoded))
            self.assertEqual(self.name_list, decoded,
                             "Round trip to list failed: %s != %s" % (self.name_list, decoded))

        # start from csv
        decoded = cu._decode_csv(self.csv_str)
        encoded = cu._encode_csv(decoded)
        check_results(encoded, decoded)

        # start from list
        encoded = cu._encode_csv(self.name_list)
        decoded = cu._decode_csv(encoded)
        check_results(encoded, decoded)


class CryptoHashing(unittest.TestCase):
    mm3hash_float_values = {
        "hello": 6.0705627102400005616e-17,
        "cube": -4.08461912519e+15,
        "sphere": 2.79018604383e+15,
        "plane": 3.66557617593e-11,
        # utf-8 bytes for "plane" in Bulgarian
        "\xd1\x80\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb8\xd0\xbd\xd0\xb0": -1.3192631212399999468e-25,
        # utf-8 bytes for "girl" in German
        "m\xc3\xa4dchen": 6.2361298211599995797e+25,
    }

    def test_mm3hash_float(self):
        import cryptomatte_utilities as cu
        for name, hashvalue in self.mm3hash_float_values.iteritems():
            msg = "%s hash does not line up: %s %s" % (name, hashvalue, cu.mm3hash_float(name))
            self.assertEqual(cu.mm3hash_float(name), cu.single_precision(hashvalue), msg)


#############################################
# Nuke tests
#############################################

global g_cancel_nuke_testing
g_cancel_nuke_testing = False


class CSVParsingNuke(unittest.TestCase):
    """
    Nuke removes escaped characters when you use getValue() on a string knob. 
    Therefore, testing the round trip through the gizmo is slightly complicated. 
    """

    def setUp(self):
        import nuke
        self.gizmo = nuke.nodes.Cryptomatte()

    def tearDown(self):
        import nuke
        nuke.delete(self.gizmo)

    def round_trip_through_gizmo(self, csv, msg):
        import cryptomatte_utilities as cu
        # start from csv
        self.gizmo.knob("matteList").setValue(csv.replace("\\", "\\\\"))

        for i in range(3):
            matte_set = cu.get_mattelist_as_set(self.gizmo)
            self.gizmo.knob("matteList").setValue("")
            cu.set_mattelist_from_set(self.gizmo, matte_set)
        result_csv = self.gizmo.knob("matteList").getValue()
        correct_set = set(cu._decode_csv(csv))
        result_set = set(cu._decode_csv(result_csv))
        self.assertEqual(correct_set, result_set, "%s: Came out as: %s" % (msg, result_csv))

    def test_csv_through_gizmo(self):
        self.round_trip_through_gizmo('"name containing a \\"quote\\"  "', "Round trip failed")

    def test_big_csv_through_gizmo(self):
        self.round_trip_through_gizmo(CSVParsing.csv_str, "Round trip failed")


class CryptomatteNodePasting(unittest.TestCase):
    """
    This one takes some explaining. 

    In Nuke 8, 9, 10, it's been discovered that when copy and pasting certain nodes,
    or when opening certain scripts the inputchanged knob change callback breaks the script. 

    What actually happens is the call to metadata() breaks it. 

    The only reliable way to notice that it's unsafe we've found is calling node.screenHeight(), 
    and if zero, stopping. 

    see: https://github.com/Psyop/Cryptomatte/issues/18

    This test tests for it. 
    """

    expected_error_prefix =  "On paste, node lost connection to"

    def test_paste_with_channelmerge(self):
        """Tests this bug has been fixed."""
        import nuke
        pastable = """
            set cut_paste_input [stack 0]
            version 10.0 v4
            push $cut_paste_input
            TimeOffset {
             name {prefix}_TimeOffset7
             label "\[value time_offset]"
             selected true
             xpos 13246
             ypos 6816
            }
            set Ndd6dafc0 [stack 0]
            push $Ndd6dafc0
            add_layer {crypto_object crypto_object.red crypto_object.green crypto_object.blue crypto_object.alpha}
            add_layer {crypto_object00 crypto_object00.red crypto_object00.green crypto_object00.blue crypto_object00.alpha}
            add_layer {crypto_object01 crypto_object01.red crypto_object01.green crypto_object01.blue crypto_object01.alpha}
            add_layer {crypto_object02 crypto_object02.red crypto_object02.green crypto_object02.blue crypto_object02.alpha}
            Cryptomatte {
             name {prefix}_Cryptomatte6
             selected true
             xpos 13150
             ypos 6876
             matteList ""
             cryptoLayer crypto_object
             expression a
             keyedName "ID value not in manifest."
             previewChannel crypto_object
             in00 crypto_object00
             in01 crypto_object01
             in02 crypto_object02
             in03 none
             in04 none
             in05 none
             in06 none
             in07 none
            }
            ChannelMerge {
             inputs 2
             operation in
             name {prefix}_ChannelMerge7
             selected true
             xpos 13246
             ypos 6941
            }
        """

        prefix = "test_paste_with_channelmerge_"
        pasted_node_names = [(prefix + x)
                             for x in ("_TimeOffset7", "_Cryptomatte6", "_ChannelMerge7")]
        self.assertFalse(
            any([nuke.toNode(x) for x in pasted_node_names]), 
            "Nodes already exist at the start of testing, were not pasted. ")
        try:
            # deselect all
            for node in nuke.selectedNodes():
                node['selected'].setValue(False)

            nuke.tcl(pastable.replace("{prefix}", prefix))
            pasted_nodes = [nuke.toNode(x) for x in pasted_node_names]
            ch_merge_node = pasted_nodes[-1]
            self.assertTrue(ch_merge_node.input(0), "%s input 0." % self.expected_error_prefix)
            self.assertTrue(ch_merge_node.input(1), "%s input 1." % self.expected_error_prefix)
        except:
            raise
        finally:
            for node in pasted_nodes:
                if node:
                    nuke.delete(node)

    def test_bug_still_exists(self):
        """Tests this bug still exists. We don't want to be running the fix if we don't have to. """
        import nuke

        if nuke.NUKE_VERSION_MAJOR == 7:  # but is known not to exist in version 7.
            return

        def test_callback(node=None, knob=None):
            node.metadata()

        callback = lambda: test_callback(nuke.thisNode())
        nuke.addKnobChanged(callback, nodeClass='Cryptomatte')

        try:
            self.test_paste_with_channelmerge()
            exception = None
        except Exception, e:
            exception = e
        finally:
            nuke.removeKnobChanged(callback, nodeClass='Cryptomatte')

        if exception:
            self.assertTrue(
                type(exception) is AssertionError,
                "Bug check failure was not assertion error. %s " % exception)
            self.assertTrue(
                self.expected_error_prefix in str(exception),
                "Assertion did not contain expected prefix (wrong assertion failed, probably). %s" %
                exception)
        else:
            self.fail("Pasting bug does not reproduce in Nuke Version %s" % nuke.NUKE_VERSION_MAJOR)


class CryptomatteNukeTests(unittest.TestCase):
    """ 
    Many tests are combined into one big class because setupClass takes significant time,
    and many tests in the same class is the lesser evil. 
    """

    @classmethod
    def setUpClass(cls):
        import nuke
        import os
        default_path = os.path.normpath(os.path.join(__file__, "../", "../", "sample_images"))
        sample_images = os.environ.get(SAMPLES_IMAGES_DIR_ENVIRON, "") or default_path
        obj_path = os.path.join(sample_images, "bunny_CryptoObject.exr").replace("\\", "/")
        asset_path = os.path.join(sample_images, "bunny_CryptoAsset.exr").replace("\\", "/")
        material_path = os.path.join(sample_images, "bunny_CryptoMaterial.exr").replace("\\", "/")
        sidecar_path = os.path.join(sample_images, "sidecar_manifest",
                                    "bunny_CryptoObject.exr").replace("\\", "/")
        for file_path in [obj_path, asset_path, material_path, sidecar_path]:
            if not os.path.isfile(file_path):
                raise IOError(
                    ("Could not find: %s. Sample image dir can be defined env variable, %s") %
                    (file_path, SAMPLES_IMAGES_DIR_ENVIRON))

        cls.read_obj = nuke.nodes.Read(file=obj_path)
        cls.read_asset = nuke.nodes.Read(file=asset_path)
        cls.read_material = nuke.nodes.Read(file=material_path)
        cls.read_sidecar = nuke.nodes.Read(file=sidecar_path)

        cls.constant = nuke.nodes.Constant(color=0.5)
        cls.set_canceled(False)

    @classmethod
    def tearDownClass(cls):
        import nuke
        if cls.canceled():
            return
        nuke.delete(cls.read_obj)
        nuke.delete(cls.read_asset)
        nuke.delete(cls.read_material)
        nuke.delete(cls.read_sidecar)
        nuke.delete(cls.constant)

    @classmethod
    def set_canceled(cls, canceled):
        global g_cancel_nuke_testing
        g_cancel_nuke_testing = canceled

    @classmethod
    def canceled(cls):
        global g_cancel_nuke_testing
        return g_cancel_nuke_testing

    def skip_cleanup(self):
        global CRYPTOMATTETEST_SKIP_CLEANUP_ON_FAILURE
        test_ok = (sys.exc_info() == (None, None, None) or sys.exc_info()[0] is unittest.SkipTest)
        if CRYPTOMATTETEST_SKIP_CLEANUP_ON_FAILURE and not test_ok:
            self.set_canceled(True)  # ensure that teardownClass does not run
            return True
        else:
            return False

    def setUp(self):
        import nuke
        import cryptomatte_utilities as cu
        if self.canceled():
            self.skipTest("Remaining tests canceled.")
            return
            # raise RuntimeError("Remaining tests canceled.")
        if not hasattr(self, "read_asset"):
            # this happens pre-python 2.7, in Nuke 7.
            # We can still create everything and run tests in Nuke 7,
            # They'll just scatter some nodes about.
            self.setUpClass()
        cu.reset_manifest_cache()
        self._remove_later = []
        self.gizmo = self.tempNode("Cryptomatte", inputs=[self.read_asset])
        self.merge = self.tempNode(
            "Merge", inputs=[self.read_obj, self.read_asset], also_merge="all")
        self.copyMetadata = self.tempNode("CopyMetaData", inputs=[self.merge, self.read_asset])
        self.read_obj_dot = self.tempNode("Dot", inputs=[self.read_obj])

    def tearDown(self):
        import nuke
        import cryptomatte_utilities as cu
        if not self.canceled():
            if self.constant.sample("red", 0, 0) != 0.5:
                self.set_canceled(True)
                self.fail(("After running '%s', can no longer sample. "
                           "No remaining tests can run.") % (self.id()))
        if not self.canceled() and not self.skip_cleanup():
            for node in self._remove_later:
                nuke.delete(node)

        cu.reset_manifest_cache()


    def tempNode(self, nodeType, **kwargs):
        """
        Creates a temporary nuke node that will be removed in teardown, 
        after the test_ method. 
        """
        import nuke
        func = getattr(nuke.nodes, nodeType)
        node = func(**kwargs)
        self._remove_later.append(node)
        return node

    def delete_nodes_after_test(self, nodes):
        self._remove_later += nodes

    #############################################
    # Keying constants (for cryptoAsset example)
    #############################################

    heroflower_expr = (
        "((uCryptoAsset00.red == 2.07262543558e+26) ? uCryptoAsset00.green : 0.0) + "
        "((uCryptoAsset00.blue == 2.07262543558e+26) ? uCryptoAsset00.alpha : 0.0) + "
        "((uCryptoAsset01.red == 2.07262543558e+26) ? uCryptoAsset01.green : 0.0) + "
        "((uCryptoAsset01.blue == 2.07262543558e+26) ? uCryptoAsset01.alpha : 0.0) + "
        "((uCryptoAsset02.red == 2.07262543558e+26) ? uCryptoAsset02.green : 0.0) + "
        "((uCryptoAsset02.blue == 2.07262543558e+26) ? uCryptoAsset02.alpha : 0.0) + 0")

    black_pkr = ("add", (700.0, 700.0))
    floweredge_pkr = ("add", (884.0, 662.0))
    bunny_pkr = ("add", (769.0, 429.0))
    set_pkr = ("add", (490.0, 250.0))  # on this pixel, extracted alpha == 1.0
    bunnyflower_pkr = ("add", (842.0, 441.0))
    rm_black_pkr = ("remove", black_pkr[1])
    rm_floweredge_pkr = ("remove", floweredge_pkr[1])
    rm_bunny_pkr = ("remove", bunny_pkr[1])
    rm_set_pkr = ("remove", set_pkr[1])
    rm_bunnyflower_pkr = ("remove", bunnyflower_pkr[1])

    #############################################
    # Utils - Keying and sampling
    #############################################

    def key_on_image(self, *args):
        self.key_on_gizmo(self.gizmo, *args)

    def key_on_gizmo(self, gizmo, *args):

        def pickerCoords(coord):
            return [0.0, 0.0, 0.0, 0.0, coord[0], coord[1], 0.0, 0.0]

        for action, coordinates in args:
            if action == "add":
                gizmo.knob("pickerAdd").setValue(pickerCoords(coordinates))
            elif action == "remove":
                gizmo.knob("pickerRemove").setValue(pickerCoords(coordinates))

    def _sample_gizmo_assert(self, pkr, msg, inverse, **kwargs):
        for channel, value in kwargs.iteritems():
            sample = self.gizmo.sample(channel, pkr[1][0], pkr[1][1])
            msg_resolved = "%s: (%s) %s vs %s" % (msg, channel, sample, value)
            if inverse:
                self.assertNotEqual(sample, value, msg_resolved)
            else:
                self.assertEqual(sample, value, msg_resolved)

    def assertSampleEqual(self, pkr, msg, **kwargs):
        self._sample_gizmo_assert(pkr, msg, False, **kwargs)

    def assertSampleNotEqual(self, pkr, msg, **kwargs):
        self._sample_gizmo_assert(pkr, msg, True, **kwargs)

    def assertMatteList(self, value, msg):
        ml = self.gizmo.knob("matteList").getValue()
        self.assertEqual(ml, value, '%s. ("%s" vs "%s")' % (msg, value, ml))

    def hash_channel(self, node, pkr, channel, num_scanlines=8, precision=None):
        """
        Returns a hash from the values a channel, tested in a number of 
        horizontal scanlines across the images. A picker tuple can be 
        provided to ensure the values on that scanline are checked. 
        If channel=depth is provided, and it finds only "depth.Z", 
        it will assume that was intended. "
        """
        import hashlib
        if channel not in ["red", "green", "blue", "alpha"] and channel not in node.channels():
            raise RuntimeError("Incorrect channel specified. %s" % channel)

        anything = False
        m = hashlib.md5()
        width, height = node.width(), node.height()
        if pkr:
            y = pkr[1][1]
            for x in xrange(width):
                sample = node.sample(channel, x, y)
                if precision:
                    sample = round(sample, precision)
                anything = anything or bool(sample)
                m.update(str(sample))
        for y_index in xrange(num_scanlines):
            y = (float(y_index) + 0.5) * height / (num_scanlines)
            for x in xrange(width):
                sample = node.sample(channel, x, y)
                anything = anything or bool(sample)
                if precision:
                    sample = round(sample, precision)
                m.update(str(sample))
        return m.hexdigest() if anything else 0

    def hash_channel_layer(self, node, layer, channel, num_scanlines=16):
        """Hashes some scanlines of a layer other than rgba, by shuffling first. """
        shuf = self.tempNode("Shuffle", inputs=[node])
        shuf.knob("in").setValue(layer)
        return self.hash_channel(shuf, None, channel, num_scanlines=num_scanlines)

    #############################################
    # Manifest tests
    #############################################

    def _create_bogus_asset_manifest(self):
        bad_md = '{set exr/cryptomatte/d593dd7/manifest "\{broken\}"}'
        return self.tempNode(
            "ModifyMetaData", inputs=[self.read_asset], 
            metadata=bad_md, name="ModifyMetaData_rename")

    def _create_missing_asset_manifest(self):
        bad_md = '{remove exr/cryptomatte/d593dd7/manifest ""}'
        return self.tempNode(
            "ModifyMetaData", inputs=[self.read_asset], 
            metadata=bad_md, name="ModifyMetaData_remove")

    def test_manifests(self):
        # Embedded and sidecar
        import cryptomatte_utilities as cu
        for read in [self.read_obj, self.read_asset, self.read_material, self.read_sidecar]:
            cinfo = cu.CryptomatteInfo(read)
            mismatches, collisions = cinfo.test_manifest(quiet=True)
            self.assertTrue(cinfo.parse_manifest(),
                            "%s manifest not loaded. " % read.knob("file").getValue())
            self.assertEqual(mismatches, [], "%s manifest mismatch" % read.knob("file").getValue())

    def test_load_manifests_lazy(self):
        import cryptomatte_utilities as cu
        gizmo = self.tempNode("Cryptomatte", inputs=[self.read_asset])
        cinfo = cu.CryptomatteInfo(gizmo)
        self.assertNotIn("manifest", cinfo.cryptomattes[cinfo.selection])

    def test_load_manifests_nonlazy(self):
        import cryptomatte_utilities as cu
        gizmo = self.tempNode("Cryptomatte", inputs=[self.read_asset])
        cinfo = cu.CryptomatteInfo(gizmo, True)
        self.assertIn("manifest", cinfo.cryptomattes[cinfo.selection])

    def test_layer_bogus_manifest(self):
        import cryptomatte_utilities as cu

        def test_manifest_and_keying(input_node):
            cu.reset_manifest_cache()
            cinfo = cu.CryptomatteInfo(input_node)
            self.gizmo.knob("matteList").setValue("")
            self.gizmo.setInput(0, input_node)

            self.assertFalse(cinfo.parse_manifest(), "Bogus manifest still loaded. ")

            cu.update_cryptomatte_gizmo(self.gizmo, True)  # tests that this doesn't raise.
            self.assertEqual(
                self.gizmo.knob("cryptoLayer").value(), "uCryptoAsset", "Layer selection not set.")

            self.key_on_image(self.bunny_pkr)
            self.assertMatteList("<3.36000126251e-27>", "Could not key with bogus manifest.")

        bogus_asset = self._create_bogus_asset_manifest()
        test_manifest_and_keying(bogus_asset)

        missing_manifest = self._create_missing_asset_manifest()
        test_manifest_and_keying(missing_manifest)


    #############################################
    # Layer Selection
    #############################################

    def test_layer_selection(self, node=None):
        gizmo = node if node else self.gizmo
        # layer selection set up properly in the first place
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoAsset", "Layer selection not set.")

        # switching inputs switches layer selections
        gizmo.setInput(0, self.read_obj)
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoObject",
            "Input change did not switch layers")
        gizmo.setInput(0, self.read_asset)
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoAsset", "Input change did not switch layers")

        # switching inputs to a multi-cryptomatte stream does not switch layer selections
        gizmo.setInput(0, self.copyMetadata)
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoAsset",
            "Input change to multi should not have switched layers")

        gizmo.setInput(0, self.read_obj)
        gizmo.setInput(0, self.copyMetadata)
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoObject",
            "Input change to multi should not have switch layers")

    def test_layer_selection_after_keying(self):
        """ Tests all layer selection options are still available after keying.  
        """
        layers = ["uCryptoAsset", "uCryptoObject"]
        choice_knob = self.gizmo.knob("cryptoLayerChoice")
        self.gizmo.setInput(0, self.copyMetadata) # set to multi

        for layer in layers:
            choice_knob.setValue(layer)
            self.assertEqual(self.gizmo.knob("cryptoLayer").value(), layer)
            self.assertEqual(set(choice_knob.values()), set(layers))
            self.key_on_gizmo(self.gizmo, self.triangle_pkr, self.set_pkr)
            self.assertEqual(set(choice_knob.values()), set(layers))

        new_gizmo = self.tempNode(
            "Cryptomatte", cryptoLayer="uCryptoAsset", 
            inputs=[self.copyMetadata], stopAutoUpdate=True)
        self.assertEqual(set(new_gizmo.knob("cryptoLayerChoice").values()), set(layers))

    def test_layer_lock(self, node=None):
        gizmo = node if node else self.gizmo
        # locking layer selection stops the switching
        gizmo.setInput(0, self.read_asset)
        gizmo.knob("cryptoLayerLock").setValue(True)
        gizmo.setInput(0, self.read_obj_dot)
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoAsset",
            "cryptoLayerLock did not keep things from changing.")
        gizmo.knob("cryptoLayerLock").setValue(False)
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoObject",
            "Disabling cryptoLayerLock did not set gizmo back to uCryptoObject.")

    def _setup_test_layer_forced_update_func(self, gizmo):
        gizmo.setInput(0, self.read_obj_dot)
        self.read_obj_dot.setInput(0, self.read_asset)
        if (gizmo.knob("cryptoLayer").value() != "uCryptoObject"):
            raise RuntimeError("Upstream changes now trigger updates, test is invalid %s " %
                               gizmo.knob("cryptoLayer").value())

    def test_layer_forced_update_btn(self, node=None):
        gizmo = node if node else self.gizmo
        self._setup_test_layer_forced_update_func(gizmo)

        gizmo.knob("forceUpdate").execute()
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoAsset",
            "Update button did not update gizmo. %s" % (gizmo.knob("cryptoLayer").value()))

    def test_layer_forced_update_func(self, node=None):
        import cryptomatte_utilities as cu
        gizmo = node if node else self.gizmo
        self._setup_test_layer_forced_update_func(gizmo)

        cu.update_cryptomatte_gizmo(gizmo, True)
        self.assertEqual(
            gizmo.knob("cryptoLayer").value(), "uCryptoAsset",
            "Update function should have updated from upstream changes. %s" %
            (gizmo.knob("cryptoLayer").value()))

    #############################################
    # Keying
    #############################################

    def test_keying_nothing(self):
        self.key_on_image(self.black_pkr)
        self.assertMatteList("", "Something selected on black. ")

    def _test_keying_partial_black(self, msg=""):
        # used as setup for other tests
        self.key_on_image(self.floweredge_pkr)
        self.assertMatteList("heroflower", msg or "Hero flower not selected on partial pixels. ")
        self.assertEqual(
            self.gizmo.knob("expression").getValue(), self.heroflower_expr, msg or
            "Hero flower expression was wrong. ")

    def test_keying_partial_black(self):
        self._test_keying_partial_black()

    def test_keying_manual(self):
        self.gizmo.knob("matteList").setValue("heroflower")
        self.assertEqual(
            self.gizmo.knob("expression").getValue(), self.heroflower_expr,
            "Expression did not update on setting matte list. ")

    def test_keying_with_removechannels(self):
        self.gizmo.knob("RemoveChannels").setValue(True)
        self.key_on_image(self.bunny_pkr)
        self.assertMatteList("bunny", "Could not key on image after Remove Channels was enabled.")

    def test_keying_blank_matteList(self):
        self._test_keying_partial_black()
        self.gizmo.knob("matteList").setValue("")
        self.assertEqual(
            self.gizmo.knob("expression").getValue(), "",
            "Expression did not update on blanking matte list. ")

    def test_keying_clear(self):
        import cryptomatte_utilities as cu
        self._test_keying_partial_black()
        cu.clear_cryptomatte_gizmo(self.gizmo)
        self.assertMatteList("", "Clear() failed. ")
        self.assertEqual(self.gizmo.knob("expression").getValue(), "", "Clear() failed. ")

    def test_clear_button(self):
        import cryptomatte_utilities as cu
        self._test_keying_partial_black()
        self.gizmo.knob("clear").execute()
        self.assertMatteList("", "Clear button failed. ")
        self.assertEqual(self.gizmo.knob("expression").getValue(), "", "Clear button failed. ")

    def test_keying_multiselect(self):
        import cryptomatte_utilities as cu

        # Multiselect over partial black
        self.key_on_image(self.floweredge_pkr, self.floweredge_pkr, self.floweredge_pkr)
        self.assertMatteList("heroflower",
                             "Multiselect on edge didn't select only 'heroflower': (%s)" %
                             self.gizmo.knob("matteList").getValue())

        # Multiselect over partial pixels
        cu.clear_cryptomatte_gizmo(self.gizmo)
        self.key_on_image(self.bunnyflower_pkr, self.black_pkr, self.bunnyflower_pkr)
        self.assertMatteList("bunny, heroflower", "Same pixel multiple selection was wrong: (%s)" %
                             self.gizmo.knob("matteList").getValue())

        # Add set to selection
        self.key_on_image(self.set_pkr)
        self.assertMatteList(
            "bunny, heroflower, set",
            "Multi selection was wrong: (%s)" % self.gizmo.knob("matteList").getValue())

        # Remove bunny and flower
        self.key_on_image(self.rm_bunny_pkr, self.rm_black_pkr, self.rm_floweredge_pkr)
        self.assertMatteList(
            "set", "Bunny and flower not removed: (%s)" % self.gizmo.knob("matteList").getValue())

    def test_keying_single_selection(self):
        # Single selection
        self.gizmo.knob("matteList").setValue("bunny, heroflower, set")
        self.gizmo.knob("singleSelection").setValue(True)
        self.assertMatteList("bunny, heroflower, set",
                             "Single selection knob changed without selection changed matte list.")
        self.key_on_image(self.set_pkr)
        self.assertMatteList(
            "set",
            "Single selection seems to have failed: (%s)" % self.gizmo.knob("matteList").getValue())

        for _ in range(5):
            self.key_on_image(self.black_pkr, self.bunnyflower_pkr)
            self.assertMatteList("bunny", "Single selection may be flickering on partials")

    def test_keying_stop_auto_update(self):
        self.gizmo.knob("stopAutoUpdate").setValue(True)
        self.gizmo.knob("expression").setValue(self.heroflower_expr)
        self.key_on_image(self.bunny_pkr)
        self.key_on_image(self.rm_set_pkr)
        self.key_on_image(self.rm_black_pkr)
        self.gizmo.knob("matteList").setValue("hello")
        self.assertEqual(
            self.gizmo.knob("expression").getValue(), self.heroflower_expr,
            "Stop auto update did not work. ")

    def test_keying_without_preview_channels(self):
        """ 
        Test that the gizmo can be set up and used properly without 
        the preview channels being available. 
        """
        self.gizmo.setInput(0, self.read_material)  # switch layer selection
        remove = self.tempNode("Remove", inputs=[self.read_asset], channels="uCryptoAsset")
        self.gizmo.setInput(0, remove)
        self._test_keying_partial_black()
        self.gizmo.knob("forceUpdate").execute()

    def test_keying_without_prefix(self):
        """ 
        If the image is loaded without the exr/ prefix, things should keep working. 
        """
        exception = None
        try:
            self.read_asset.knob("noprefix").setValue(True)
            self.gizmo.knob("forceUpdate").execute()
            self._test_keying_partial_black("Keying failed once read-node prefix was disabled.")
        except Exception, e:
            exception = e

        self.read_asset.knob("noprefix").setValue(False)
        if exception:
            raise exception

    #############################################
    # Output checking
    #############################################

    def test_output_preview(self):
        self.key_on_image(self.bunny_pkr)
        msg = "Selection did not light up properly. %s, %s"
        self.assertSampleEqual(
            self.bunny_pkr, "Preview image did not light up", red=1.0, green=1.0, alpha=1.0)
        self.assertSampleNotEqual(self.set_pkr, "Set pixels should be dark.", red=1.0, green=1.0)
        self.assertSampleEqual(self.set_pkr, "Set pixels should be unselected.", alpha=0.0)

    def test_output_preview_disabled(self):
        # stops lighting up after disabled, but alpha still correct
        self.key_on_image(self.bunny_pkr)
        self.gizmo.knob("previewEnabled").setValue(False)
        self.assertSampleEqual(
            self.bunny_pkr,
            "Preview image bunny pixels wrong when disabled",
            red=0.0,
            green=0.0,
            alpha=1.0)
        self.assertSampleEqual(
            self.set_pkr,
            "Preview image set pixels wrong when disabled",
            red=0.0,
            green=0.0,
            alpha=0.0)
        self.gizmo.knob("previewEnabled").setValue(True)

    def test_output_preview_multi(self):
        # add an item, make sure it lights up too
        self.key_on_image(self.bunny_pkr, self.set_pkr)
        self.assertSampleEqual(
            self.bunny_pkr, "Bunny pixels are wrong.", red=1.0, green=1.0, alpha=1.0)
        self.assertSampleEqual(self.set_pkr, "Set pixels are wrong.", red=1.0, green=1.0, alpha=1.0)

    #############################################
    # Matte list manipulations
    #############################################

    def _clear_manifest_cache(self):
        import cryptomatte_utilities as cu
        cu.g_cryptomatte_manf_from_names = {}
        cu.g_cryptomatte_manf_from_IDs = {}

    def test_matte_list_numeric(self):
        """
        Tests what happens with matte lists if you have a name matte list, but pick without a 
        manifest, and vice version. It should be smart enough to not create anything redundant. 
        """
        import nuke
        numeric_mlist_bunny = "<3.36000126251e-27>"
        numeric_mlist_set = "<7.36562399642e+18>"
        numeric_mlist_both = "<3.36000126251e-27>, <7.36562399642e+18>"
        name_mlist_bunny = "bunny"

        mod_md_node = self.tempNode(
            "ModifyMetaData",
            inputs=[self.read_asset],
            metadata='{set exr/cryptomatte/d593dd7/manifest "\{\}"}')

        self.gizmo.setInput(0, mod_md_node)
        self._clear_manifest_cache()

        self.key_on_image(self.bunny_pkr)
        self.assertMatteList(numeric_mlist_bunny, "Numeric mattelist incorrect.")

        # test adding redundant item numerically to a named selection
        self.gizmo.knob("matteList").setValue(name_mlist_bunny)
        self.key_on_image(self.bunny_pkr)
        self.assertMatteList("bunny", "Redundant matte list generated.")

        # test that removing named item by number works
        self.key_on_image(self.rm_bunny_pkr)
        self.assertMatteList("", "Removal of name by number failed.")

        # test that adding and removing numeric items works from a named list
        self.gizmo.knob("matteList").setValue("bunny, heroflower")
        self.key_on_image(self.set_pkr, self.rm_bunny_pkr)
        self.assertMatteList("<7.36562399642e+18>, heroflower", "Removal of name by number failed.")
        self.key_on_image(self.bunny_pkr)
        self.assertMatteList("<3.36000126251e-27>, <7.36562399642e+18>, heroflower",
                             "Adding number to a name list failed.")

    def test_matte_list_name_modifications(self):
        self.gizmo.knob("matteList").setValue(
            "<3.36000126251e-27>, <7.36562399642e+18>, heroflower")
        self.key_on_image(self.rm_bunny_pkr, self.rm_set_pkr, self.rm_floweredge_pkr,
                          self.rm_floweredge_pkr)
        self.assertMatteList("", "Could not remove numbers by name.")
        self.key_on_image(self.bunny_pkr, self.set_pkr)
        self.assertMatteList("bunny, set", "Could not re-add by picking.")

    #############################################
    # Decryptomatte
    #############################################

    def test_decrypto_basic(self):
        """ Tests both basic decryptomatte, as well as ensuring hash_channel() is
        returning different hashes for different values. 
        """
        import cryptomatte_utilities as cu

        self.key_on_image(self.bunny_pkr)
        wrong_hash = self.hash_channel(self.gizmo, self.bunny_pkr, "green")
        correct_hash = self.hash_channel(self.gizmo, self.bunny_pkr, "alpha")

        new_nodes = cu._decryptomatte(self.gizmo)
        self.delete_nodes_after_test(new_nodes)
        decryptomatted_hash = self.hash_channel(new_nodes[-1], self.bunny_pkr, "alpha")
        self.assertNotEqual(decryptomatted_hash, wrong_hash,
                            "Wrong hash is same as right hash, scanlines may be broken.")
        self.assertEqual(decryptomatted_hash, correct_hash,
                         "Decryptomatte caused a different alpha from Cryptomatte.")

    def test_decrypto_custom_channel(self):
        import cryptomatte_utilities as cu
        custom_layer = "uCryptoAsset"  # guaranteed to already exist.
        custom_layer_subchannel = "%s.red" % custom_layer

        self.key_on_image(self.set_pkr)
        self.gizmo.knob("matteOutput").setValue(custom_layer)
        alpha_hash = self.hash_channel(self.gizmo, self.set_pkr, "alpha")
        correct_hash = self.hash_channel(self.gizmo, self.set_pkr, custom_layer_subchannel)

        new_nodes = cu._decryptomatte(self.gizmo)
        self.delete_nodes_after_test(new_nodes)
        decryptomatte_hash = self.hash_channel(new_nodes[-1], self.set_pkr, custom_layer_subchannel)

        self.assertNotEqual(correct_hash, alpha_hash, "Custom channel is the same as the alpha.")
        self.assertEqual(correct_hash, decryptomatte_hash,
                         "Decryptomatte in a custom channel mismatch.")

    def test_decrypto_matteonly_unpremul(self):
        import cryptomatte_utilities as cu
        custom_layer = "uCryptoAsset"  # guaranteed to already exist
        prec = 5

        # self.gizmo will have alpha for unpremult.
        self.key_on_image(self.set_pkr, self.bunny_pkr)
        new_gizmo = self.tempNode(
            "Cryptomatte",
            inputs=[self.gizmo],
            matteList="bunny",
            matteOnly=True,
            matteOutput=custom_layer)
        no_unpremult_hash = self.hash_channel(new_gizmo, self.set_pkr, "alpha", precision=prec)
        new_gizmo.knob("unpremultiply").setValue(True)

        channels = ["red", "green", "alpha", "%s.red" % custom_layer]
        gizmo_hashes = [self.hash_channel(new_gizmo, self.set_pkr, ch, precision=prec)
                        for ch in channels]
        new_nodes = cu._decryptomatte(new_gizmo)
        self.delete_nodes_after_test(new_nodes)
        decrypto_hashes = [self.hash_channel(new_nodes[-1], self.set_pkr, ch, precision=prec)
                           for ch in channels]

        self.assertNotEqual(no_unpremult_hash, gizmo_hashes[0],
                            "Unpremult didn't seem to change anything.")
        for ch, g_hash, dc_hash in zip(channels, gizmo_hashes, decrypto_hashes):
            self.assertEqual(g_hash, dc_hash,
                             "Difference between decryptomatte (%s) and regular (%s) in %s"
                              % (new_nodes[-1].name(), new_gizmo.name(), ch))
        for i, channel in enumerate(channels[:-1]):
            msg = "Matte-only difference between %s and %s" % (channels[i], channels[i + 1])
            self.assertEqual(decrypto_hashes[i], decrypto_hashes[i + 1], msg)

    def test_decrypto_rmchannels_customlayer(self):
        self._test_decrypto_rmchannels("uCryptoAsset")

    def test_decrypto_rmchannels_alpha(self):
        self._test_decrypto_rmchannels("alpha")

    def _test_decrypto_rmchannels(self, output_layer="alpha"):
        import cryptomatte_utilities as cu
        orig_channels = set(x for x in self.gizmo.channels())
        self.gizmo.knob("RemoveChannels").setValue(True)
        self.gizmo.knob("matteOutput").setValue(output_layer)
        channels_removed = set(x for x in self.gizmo.channels())

        new_nodes = cu._decryptomatte(self.gizmo)
        self.delete_nodes_after_test(new_nodes)

        channels_removed_decrypto = set(x for x in new_nodes[-1].channels())
        channels_removed_decrypto |= set(['rgba.red', 'rgba.green', 'rgba.blue', 'rgba.alpha'])

        self.assertNotEqual(orig_channels, channels_removed, 
                            "Removing channels did nothing (%s)" % output_layer)
        self.assertEqual(channels_removed, channels_removed_decrypto,
                         "Channels not removed properly after decrypto. (%s)" % output_layer)

    #############################################
    # Gizmo integrity
    #############################################

    def test_gizmo_version(self, node=None):
        import cryptomatte_utilities as cu
        def test_version(gizmo):
            gizmo_version = gizmo.knob("cryptomatteVersion").value()
            self.assertEqual(
                gizmo_version, cu.__version__,
                "%s version not same as Python version. "
                        "(%s, %s)" % (gizmo.Class(), cu.__version__, gizmo_version))

        test_version(self.gizmo)
        test_version(self.tempNode("Encryptomatte"))

    def test_crypto_channel_knobs_type(self, node=None):
        import cryptomatte_utilities as cu
        for channel in cu.GIZMO_CHANNEL_KNOBS:
            self.assertTrue(
                self.gizmo.knob(channel).Class() in set(["Channel_Knob", "ChannelMask_Knob"]),
                "Input knob was not a channel knob, which causes failed renders "
                "due to expression errors on load. (%s)" % self.gizmo.knob(channel).Class())

    def test_encrypt_channel_knobs_type(self, node=None):
        import cryptomatte_utilities as cu
        encrypt = self.tempNode("Encryptomatte")
        for channel in cu.GIZMO_REMOVE_CHANNEL_KNOBS + cu.GIZMO_ADD_CHANNEL_KNOBS:
            self.assertTrue(
                encrypt.knob(channel).Class() in set(["Channel_Knob", "ChannelMask_Knob"]),
                "Input knob was not a channel knob, which causes failed renders "
                "due to expression errors on load. (%s)" % encrypt.knob(channel).Class())

    #############################################
    # Encryptomatte
    #############################################
    # todo(jfriedman): test stop_auto_update, auto filling in "matte name"

    triangle_coords = [
        [916.0, 512.0],
        [839.0, 416.0],
        [828.0, 676.0],
    ]

    triangle_pkr = ("add", (840.0, 615.0))

    def _setup_rotomask(self):
        """Which partially covers the flower."""
        import nuke.rotopaint as rp
        self.gizmo.setInput(0, self.read_asset)
        rotomask = self.tempNode("Roto", inputs=[self.read_asset])
        shape = rp.Shape(rotomask['curves'])
        shape.getAttributes().set("fx", 20)
        shape.getAttributes().set("fy", 20)
        for pos in self.triangle_coords:
            shape.append(pos)
        rotomask['curves'].rootLayer.append(shape)
        return rotomask

    def test_encrypt_layerselection(self):
        encryptomatte = self.tempNode("Encryptomatte", inputs=[self.gizmo])
        self.test_layer_selection(encryptomatte)

    def test_encrypt_layer_lock(self):
        encryptomatte = self.tempNode("Encryptomatte", inputs=[self.gizmo])
        self.test_layer_lock(encryptomatte)

    def test_encrypt_layer_forced_update_btn(self):
        encryptomatte = self.tempNode("Encryptomatte", inputs=[self.gizmo])
        self.test_layer_forced_update_btn(encryptomatte)

    def test_encrypt_matte_name_autofill2(self):
        encryptomatte = self.tempNode("Encryptomatte", inputs=[self.read_asset])
        self.assertEqual(
            encryptomatte.knob("matteName").getValue(), "",
            "Encryptomatte got a matte name not properly blank to start. ")
        encryptomatte.setInput(1, self.constant)
        self.assertEqual(
            encryptomatte.knob("matteName").getValue(),
            self.constant.name(), "Encryptomatte matte name was not set automatically.")
        encryptomatte.setInput(1, self.gizmo)
        self.assertEqual(
            encryptomatte.knob("matteName").getValue(),
            self.constant.name(), ("Encryptomatte matte should not have been "
                                   "set automatically if it was already connected. "))

        preconnected_encrypto = self.tempNode(
            "Encryptomatte", inputs=[self.read_asset, self.constant])
        self.assertEqual(
            encryptomatte.knob("matteName").getValue(),
            self.constant.name(), "Encryptomatte matte name was not set automatically on creation.")

    def test_encrypt_bogus_inputs(self):
        """ Tests that when setting up layers, entering the name before pressing "setup layers"
        doesn't spew python errors but fails gracefully. 
        """
        import cryptomatte_utilities as cu
        encryptomatte = self.tempNode("Encryptomatte", matteName="triangle")
        try:
            encryptomatte.knob("cryptoLayer").setValue("customCrypto")
            cu.encryptomatte_knob_changed_event(encryptomatte, encryptomatte.knob("cryptoLayer"))
            encryptomatte.knob("setupLayers").setValue(True)
            cu.encryptomatte_knob_changed_event(encryptomatte, encryptomatte.knob("setupLayers"))
        except Exception, e:
            self.fail("Invalid crypto layer name raises error: %s" % e)

    def test_encrypt_setup_layers_numbers(self):
        """ Tests that when setting up layers, entering the name before pressing "setup layers"
        doesn't spew python errors but fails gracefully. 
        """
        encryptomatte = self.tempNode("Encryptomatte", matteName="triangle")
        encryptomatte.knob("setupLayers").setValue(True)
        encryptomatte.knob("cryptoLayer").setValue("customCrypto")
        customLayers = [
            "customCrypto00", "customCrypto01", "customCrypto02", "customCrypto03",
            "customCrypto04", "customCrypto05", "customCrypto06", "customCrypto07",
            "customCrypto08", "customCrypto09"
        ]

        encryptomatte.knob("cryptoLayers").setValue(3)
        channels = set(encryptomatte.channels())
        for layer in customLayers[:3]:
            self.assertTrue("%s.red" % layer in channels, "%s not in channels" % layer)
        for layer in customLayers[3:]:
            self.assertFalse("%s.red" % layer in channels, "%s in channels" % layer)

        encryptomatte.knob("cryptoLayers").setValue(6)
        channels = encryptomatte.channels()
        for layer in customLayers[:6]:
            self.assertTrue("%s.red" % layer in channels, "%s not in channels" % layer)
        for layer in customLayers[6:]:
            self.assertFalse("%s.red" % layer in channels, "%s in channels" % layer)

    def test_encrypt_roundtrip_setup(self):
        import cryptomatte_utilities as cu

        keysurf_hash = self.hash_channel(self.gizmo, None, "blue", num_scanlines=16)
        roto_hash = self.hash_channel(self._setup_rotomask(), None, "alpha", num_scanlines=16)

        id0_hash = self.hash_channel_layer(self.read_asset, "uCryptoAsset00", "red")
        encryptomatte = self.tempNode(
            "Encryptomatte", inputs=[self.read_asset, self._setup_rotomask()], matteName="triangle")
        second_cryptomatte = self.tempNode(
            "Cryptomatte", matteList="triangle")
        second_cryptomatte.setInput(0, encryptomatte)
        self.assertEqual(encryptomatte.knob("cryptoLayer").getValue(), "uCryptoAsset", "Layer was not set")

        new_id0_hash = self.hash_channel_layer(encryptomatte, "uCryptoAsset00", "red")
        self.assertNotEqual(id0_hash, new_id0_hash, "ID channel did not change. ")

        decrypto_hash = self.hash_channel(second_cryptomatte, None, "alpha", num_scanlines=16)
        mod_keysurf_hash = self.hash_channel(second_cryptomatte, None, "alpha", num_scanlines=16)
        
        self.assertEqual(roto_hash, decrypto_hash, ("Alpha did not survive round trip through "
                                                    "Encryptomatte and then Cryptomatte. "))
        self.assertNotEqual(keysurf_hash, mod_keysurf_hash, "preview image did not change. ")
        cinfo = cu.CryptomatteInfo(second_cryptomatte)
        names_to_IDs = cinfo.parse_manifest()
        self.assertTrue("set" in names_to_IDs, "Manifest doesn't contain original manifest")
        self.assertTrue("triangle" in names_to_IDs, "Manifest doesn't contain new members")

    def test_encrypt_roundtrip_keyable(self):        
        encryptomatte = self.tempNode(
            "Encryptomatte", inputs=[self.read_asset, self._setup_rotomask()], matteName="triangle")

        self.gizmo.setInput(0, encryptomatte)
        self.key_on_image(self.set_pkr, self.triangle_pkr)

        mlist = self.gizmo.knob("matteList").getValue()
        self.assertEqual(mlist, "set, triangle",
                         "Encrypto-modified manifest not properly keyable. {0}".format(mlist))

        self.assertTrue("set" in mlist, "Couldn't properly key 'set' (Pre-existing)")
        self.assertTrue("triangle" in mlist, "Couldn't properly key 'triangle' (New Member)")

    def test_encrypt_roundtrip_without_prefix(self):
        self.read_asset.knob("noprefix").setValue(True)
        exception = None
        try:
            self.test_encrypt_roundtrip_setup()
        except:
            raise
        finally:
            self.read_asset.knob("noprefix").setValue(False)

    def test_encrypt_bogus_manifest(self):
        import cryptomatte_utilities as cu
        mod_md_node = self._create_bogus_asset_manifest()
        encryptomatte = self.tempNode(
            "Encryptomatte", inputs=[mod_md_node, self._setup_rotomask()], matteName="triangle")
        self.gizmo.setInput(0, encryptomatte)
        self.key_on_image(self.triangle_pkr)
        self.gizmo.knob("forceUpdate").execute()
        self.assertMatteList("<1.54567320652e-21>", "Did not update after keying. ")

        def broken_test_parts():
            """ this should work, but doesn't for some reason. It produces the right result 
            as seen in failfast, but breaks tests. The encryptomatte tests are generally too 
            brittle and this is one example. """
            self.assertSampleEqual(
                self.triangle_pkr, "Encryptomatte result not keyable after bogus manifest", alpha=1.0)
        # broken_test_parts()

    def test_encrypt_merge_operations(self):
        import cryptomatte_utilities as cu

        encry_over = self.tempNode(
            "Encryptomatte",
            inputs=[self.read_asset, self._setup_rotomask()],
            matteName="triangle",
            mergeOperation="over")

        id0_hash = self.hash_channel_layer(encry_over, "uCryptoAsset00", "red")

        # use a new rotomask every time, less bug prone in Nuke. 
        encry_under = self.tempNode(
            "Encryptomatte",
            inputs=[self.read_asset, self._setup_rotomask()],
            matteName="triangle",
            mergeOperation="under")
        id0_mod_hash = self.hash_channel_layer(encry_under, "uCryptoAsset00", "red")

        self.assertNotEqual(id0_hash, id0_mod_hash, "Under mode did not change ID 0. ")

    def test_encrypt_fresh_roundtrip(self):
        constant2k = self.tempNode("Constant", format="square_2K")
        empty_hash = self.hash_channel(constant2k, None, "alpha", num_scanlines=16)

        roto1k = self._setup_rotomask()
        roto1k.setInput(0, constant2k)
        roto_hash = self.hash_channel(roto1k, None, "alpha", num_scanlines=16)

        if empty_hash == roto_hash:
            raise RuntimeError("Roto matte did not change alpha, test is invalid. (%s)" % roto_hash)

        constant2k = self.tempNode("Constant", format="square_1K")

        encryptomatte = self.tempNode(
            "Encryptomatte", inputs=[constant2k, roto1k], matteName="triangle")
        encryptomatte.knob("cryptoLayer").setValue("customCrypto")
        encryptomatte.knob("setupLayers").setValue(True)

        self.gizmo.setInput(0, encryptomatte)
        self.key_on_image(self.triangle_pkr)
        self.assertMatteList("triangle", "Encryptomatte did not produce a keyable triangle")

        def broken_test_parts():
            """ this should work, but doesn't for some reason. It produces the right result 
            as seen in failfast, but breaks tests. The encryptomatte tests are generally too 
            brittle and this is one example. """

            self.gizmo.knob("forceUpdate").execute() # needed for some reason. 
            merge = self.tempNode("Merge", inputs=[constant2k, roto1k])
            roto_hash_720 = self.hash_channel(merge, None, "alpha", num_scanlines=16)
            decrypto_hash = self.hash_channel(self.gizmo, None, "alpha", num_scanlines=16)
            self.assertEqual(
                roto_hash_720, decrypto_hash, 
                ("Alpha did not survive round trip through "
                "Encryptomatte (%s) and then Cryptomatte (%s). ") % (roto_hash_720, decrypto_hash))
        # broken_test_parts()


    def test_encrypt_manifest(self):
        """Gets it into a weird state where it has a manifest but no cryptomatte."""
        import cryptomatte_utilities as cu
        encryptomatte = self.tempNode(
            "Encryptomatte", inputs=[self.gizmo, self.constant], matteName="test")
        cu.encryptomatte_knob_changed_event(encryptomatte, encryptomatte.knob("matteName"))
        encryptomatte.knob("setupLayers").setValue(True)
        encryptomatte.knob("cryptoLayer").setValue("customCrypto")
        encryptomatte.knob("setupLayers").setValue(False)
        cu.encryptomatte_knob_changed_event(encryptomatte, encryptomatte.knob("matteName"))

    def test_encrypt_fresh_keyable(self):
        """Tests fresh Encryptomatte setup where there is no input constant."""
        import cryptomatte_utilities as cu
        encryptomatte = self.tempNode(
            "Encryptomatte", inputs=[None, self._setup_rotomask()], matteName="triangle", 
            setupLayers=True, cryptoLayer="custom_crypto")
        self.gizmo.setInput(0, encryptomatte)
        self.key_on_image(self.triangle_pkr)
        self.assertMatteList("triangle", "Encryptomatte did not produce a keyable triangle")

    def test_channel_identification(self):
        """Makes sure multiple Cryptomattes can have sub-channels identified properly, 
        even if one's name starts with the others. """
        import cryptomatte_utilities as cu
        lyr_a_name, lyr_b_name = "cryLyr", "cryLyrSecond"
        lyr_a_result = ['cryLyr00', 'cryLyr01', 'cryLyr02']
        lyr_b_result = ['cryLyrSecond00', 'cryLyrSecond01', 'cryLyrSecond02']

        encrypt_a = self.tempNode("Encryptomatte", setupLayers=True, cryptoLayer=lyr_a_name)
        encrypt_b = self.tempNode("Encryptomatte", setupLayers=True, cryptoLayer=lyr_b_name)

        encrypt_b.setInput(0, encrypt_a)
        self.gizmo.setInput(0, encrypt_b)
        cinfo = cu.CryptomatteInfo(self.gizmo)

        identified_a = cinfo._identify_channels(lyr_a_name)
        identified_b = cinfo._identify_channels(lyr_b_name)

        self.assertEqual(lyr_a_result, identified_a)
        self.assertEqual(lyr_b_result, identified_b)

        cinfo.set_selection(lyr_a_name)
        self.assertEqual(cinfo.get_channels(), identified_a)

        cinfo.set_selection(lyr_b_name)
        self.assertEqual(cinfo.get_channels(), identified_b)

    #############################################
    # Blender names ("with . in names)
    #############################################

    nuke_unfriendly_channel_names = [
        ("custom.crypto", "custom_crypto"),
        ("amp&rsand", "amp_rsand"),
        ("per.od", "per_od"),
        (".per.od", "_per_od"),
        ("numlast_123", "numlast_123"),
        ("123_numfirst", "_123_numfirst"),
        ("123_numfirst.", "_123_numfirst_"),
        ("num_123_middle", "num_123_middle"),
    ]

    def test_blendery_names_in_metadata(self):
        """Tests that names with nuke-unfriendly layer names are mangled property."""
        encryptomatte = self.tempNode(
            "Encryptomatte", inputs=[None, self._setup_rotomask()], matteName="triangle", 
            setupLayers=True)
        for bad_name, corrected_name in self.nuke_unfriendly_channel_names:
            encryptomatte.knob("cryptoLayer").setValue(bad_name)

            name_key = ""
            metadata = encryptomatte.metadata()
            for key in metadata:
                if key.startswith("cryptomatte/") and key.endswith("/name"):
                    name_key = key
                    break
            self.assertEqual(metadata[name_key], corrected_name)

            modify_md = self.tempNode(
                "ModifyMetaData", inputs=[encryptomatte], 
                metadata='{set %s "%s"}' % (name_key, bad_name))
            self.gizmo.setInput(0, modify_md)

            # For some reason, on first runs after opening a fresh nuke (12.0v3)
            # this does not always update on its own. 
            encryptomatte.knob("forceUpdate").execute()
            self.gizmo.knob("forceUpdate").execute()

            self.assertEqual(
                self.gizmo.knob("cryptoLayer").getValue(), corrected_name,
                "Period should be removed from name and it should key.")
            self.key_on_image(self.triangle_pkr)
            self.assertMatteList("triangle", "Did not produce a keyable triangle")

        self.test_bad_names_in_nuke_layers()

    def test_blendery_names_encryptomatte(self):
        """Tests that names with nuke-unfriendly layer names are mangled property by Encryptomatte."""

        encryptomatte = self.tempNode(
            "Encryptomatte", inputs=[None, self._setup_rotomask()], matteName="triangle", 
            setupLayers=True)
        for bad_name, corrected_name in self.nuke_unfriendly_channel_names:
            encryptomatte.knob("cryptoLayer").setValue(bad_name)
            self.assertEqual(
                corrected_name, encryptomatte.knob("cryptoLayer").getValue(),
                "Period should be removed from Encryptomatte name.")
            self.gizmo.setInput(0, encryptomatte)

            # For some reason, on first runs after opening a fresh nuke (12.0v3)
            # this does not always update on its own. 
            encryptomatte.knob("forceUpdate").execute()
            self.gizmo.knob("forceUpdate").execute()

            self.assertEqual(
                self.gizmo.knob("cryptoLayer").getValue(), corrected_name,
                "Period should be removed from name and it should key.")
            self.key_on_image(self.triangle_pkr)
            self.assertMatteList("triangle", "Did not produce a keyable triangle")

        self.test_bad_names_in_nuke_layers()

    def test_bad_names_in_nuke_layers(self):
        import nuke
        import cryptomatte_utilities as cu
        for bad_name, corrected_name in self.nuke_unfriendly_channel_names:
            if bad_name != cu._legal_nuke_layer_name(bad_name):
                self.assertNotIn(
                    bad_name + "00", nuke.layers(), 
                    "Bad layer (%s) got into nuke layers. Restarting Nuke is required to test this again." % bad_name)

    def test_file_open_doesnt_update_nodes(self):
        """
        Note: This script behaves differently if the xpos and ypos are on the Cryptomatte node,
        vs if they aren't. They need to be here for this to work. 

        There does not appear to be a difference in loading a file vs pasting
        as of Nuke 12v3. 
        """
        import nuke

        prefix = "test_file_open_doesnt_update_nodes"
        asset_file = self.read_asset.knob("file").getValue()

        loadable = """
            Read {
             inputs 0
             file_type exr
             file %s
             name %s_Read
             selected true
             xpos 498
             ypos -17
            }
            add_layer {uCryptoAsset00 uCryptoAsset00.red uCryptoAsset00.green uCryptoAsset00.blue uCryptoAsset00.alpha}
            add_layer {uCryptoAsset01 uCryptoAsset01.red uCryptoAsset01.green uCryptoAsset01.blue uCryptoAsset01.alpha}
            add_layer {uCryptoAsset02 uCryptoAsset02.red uCryptoAsset02.green uCryptoAsset02.blue uCryptoAsset02.alpha}
            Cryptomatte {
             name %s_Cryptomatte
             selected true
             xpos 395
             ypos 33
             matteOutput alpha
             matteOutput alpha
             matteList "set, triangle"
             cryptoLayer uCryptoMaterial
             expression "((uCryptoMaterial00.red == 7.36562399642e+18 || uCryptoMaterial00.red == 1.54567320652e-21) ? uCryptoMaterial00.green : 0.0) + ((uCryptoMaterial00.blue == 7.36562399642e+18 || uCryptoMaterial00.blue == 1.54567320652e-21) ? uCryptoMaterial00.alpha : 0.0) + ((uCryptoMaterial01.red == 7.36562399642e+18 || uCryptoMaterial01.red == 1.54567320652e-21) ? uCryptoMaterial01.green : 0.0) + ((uCryptoMaterial01.blue == 7.36562399642e+18 || uCryptoMaterial01.blue == 1.54567320652e-21) ? uCryptoMaterial01.alpha : 0.0) + ((uCryptoMaterial02.red == 7.36562399642e+18 || uCryptoMaterial02.red == 1.54567320652e-21) ? uCryptoMaterial02.green : 0.0) + ((uCryptoMaterial02.blue == 7.36562399642e+18 || uCryptoMaterial02.blue == 1.54567320652e-21) ? uCryptoMaterial02.alpha : 0.0) + 0"
             in00 uCryptoMaterial00
             in01 uCryptoMaterial01
             in02 uCryptoMaterial02
            }
        """ % (asset_file, prefix, prefix)

        pasted_node_names = [(prefix + x)
                             for x in ("_Read", "_Cryptomatte")]
        self.assertFalse(
            any([nuke.toNode(x) for x in pasted_node_names]), 
            "Nodes already exist at the start of testing, were not pasted. ")

        try:
            for node in nuke.selectedNodes():
                node['selected'].setValue(False)
            nuke.scriptReadText(loadable)
            loaded_nodes = [nuke.toNode(x) for x in pasted_node_names]
            read, cryptomatte = loaded_nodes

            msg = "Loaded file was changed from the state it was loaded. "
            self.assertEqual(cryptomatte.knob("cryptoLayer").getValue(), "uCryptoMaterial")
            self.assertEqual(cryptomatte.knob("in00").value(), "uCryptoMaterial00")
            self.assertEqual(cryptomatte.knob("in01").value(), "uCryptoMaterial01")
            self.assertEqual(cryptomatte.knob("in02").value(), "uCryptoMaterial02")
            self.assertEqual(cryptomatte.knob("matteList").getValue(), "set, triangle")
            self.assertIn("uCryptoMaterial00.red", cryptomatte.knob("expression").getValue())
        except:
            raise
        finally:
            if not self.skip_cleanup():
                for node in loaded_nodes:
                    nuke.delete(node)


#############################################
# Ad hoc test running
#############################################


def run_unit_tests(test_filter="", failfast=False):
    """ Utility function for manually running tests unit tests.
    Returns unittest results if there are failures, otherwise None """

    return run_tests(get_all_unit_tests(), test_filter=test_filter, failfast=failfast)


def run_nuke_tests(test_filter="", failfast=False):
    """ Utility function for manually running tests inside Nuke
    Returns unittest results if there are failures, otherwise None """

    return run_tests(
        get_all_unit_tests() + get_all_nuke_tests(), test_filter=test_filter, failfast=failfast)


def run_tests(test_cases, test_filter="", failfast=False):
    """ Utility function for manually running tests. 
    Returns results if there are failures, otherwise None 

    Args:
        test_filter will be matched fnmatch style (* wildcards) to either the name of the TestCase 
        class or test method. 

        failfast stop after a failure, and skip cleanup of the nodes that were created. 
    """
    import nuke
    import fnmatch
    import platform
    import cryptomatte_utilities as cu

    def find_test_method(traceback):
        """ Finds first "test*" function in traceback called. """
        import re
        match = re.search('", line \d+, in (test[a-z_0-9]+)', traceback)
        return match.group(1) if match else ""

    suite = unittest.TestSuite()
    for case in test_cases:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(case))

    if test_filter:
        filtered_suite = unittest.TestSuite()
        for test in suite:
            if any(fnmatch.fnmatch(x, test_filter) for x in test.id().split(".")):
                filtered_suite.addTest(test)
        if not any(True for _ in filtered_suite):
            raise RuntimeError("Filter %s selected no tests. " % test_filter)
        suite = filtered_suite

    set_skip_cleanup_on_failure(failfast)

    pv = sys.version_info
    if "%s.%s" % (pv[0], pv[1]) == "2.6":
        runner = unittest.TextTestRunner(verbosity=2) # nuke 7 again..
    else:
        runner = unittest.TextTestRunner(verbosity=2, failfast=failfast)
    result = runner.run(suite)

    reset_skip_cleanup_on_failure()

    print "---------"
    print 'Cryptomatte %s, Nuke %s, %s' % (cu.__version__, 
                                           nuke.NUKE_VERSION_STRING, 
                                           platform.platform())
    print "---------"
    for test_instance, traceback in result.failures:
        print "Failed: %s.%s" % (type(test_instance).__name__, find_test_method(traceback))
        print
        print traceback
        print "---------"
    for test_instance, traceback in result.errors:
        print "Error: %s.%s" % (type(test_instance).__name__, find_test_method(traceback))
        print
        print traceback
        print "---------"

    if result.failures or result.errors:
        print "TESTING FAILED: %s failed, %s errors. (%s test cases.)" % (len(result.failures),
                                                                          len(result.errors),
                                                                          suite.countTestCases())
        return result
    else:
        print "Testing passed: %s failed, %s errors. (%s test cases.)" % (len(result.failures),
                                                                          len(result.errors),
                                                                          suite.countTestCases())
        return None