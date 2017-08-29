#
#
#  Copyright (c) 2014, 2015, 2016, 2017 Psyop Media Company, LLC
#  See license.txt
#
#

import unittest

def get_all_unit_tests():
    """ Returns the list of unit tests (to run in any context)"""
    return [CSVParsing, CryptoHashing]

def get_all_nuke_tests():
    """ Returns the list of maya integration tests (Only run in Maya)"""
    return [CryptomatteGizmoSetup]

#############################################
# Unit tests
#############################################

class CSVParsing(unittest.TestCase):
    csv_str = ("""str, "str with space", "single 'quotes'", """
        '"with_a,_comma", "with comma, and \\"quotes\\"", <123.45>, '
        '" space_in_front", "space_at_end ", "has_escape\\\\chars", '
        '"cyrillic \xd1\x80\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb8\xd0\xbd\xd0\xb0"')
    name_list = ["str", "str with space", "single 'quotes'",
        "with_a,_comma", 'with comma, and "quotes"', "<123.45>", 
        " space_in_front", "space_at_end ", "has_escape\\chars", 
        "cyrillic \xd1\x80\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb8\xd0\xbd\xd0\xb0"]

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
        # utf-8 bytes for "plane" in Bulgarian
        "\xd1\x80\xd0\xb0\xd0\xb2\xd0\xbd\xd0\xb8\xd0\xbd\xd0\xb0": -1.3192631212399999468e-25,
        # utf-8 bytes for "girl" in German
        "m\xc3\xa4dchen": 6.2361298211599995797e+25,
    }

    def test_mm3hash_float(self):
        import cryptomatte_utilities as cu
        for name, hashvalue in self.mm3hash_float_values.iteritems():
            self.assertEqual(cu.single_precision(hashvalue), cu.mm3hash_float(name), 
                "%s hash does not line up: %s %s" % (name, hashvalue, cu.mm3hash_float(name)))


#############################################
# Nuke tests
#############################################

class CryptomatteGizmoSetup(unittest.TestCase):
    """ 
    Many tests are combined into one big class because setupClass takes significant time,
    and many tests in the same class is the lesser evil. 
    """

    @classmethod
    def setUpClass(self):
        import nuke
        import os
        sample_images = os.path.normpath(os.path.join(__file__, "../", "../", "sample_images"))
        obj_path = os.path.join(sample_images, "bunny_CryptoObject.exr").replace("\\", "/")
        asset_path = os.path.join(sample_images, "bunny_CryptoAsset.exr").replace("\\", "/")
        material_path = os.path.join(sample_images, "bunny_CryptoMaterial.exr").replace("\\", "/")
        sidecar_path = os.path.join(sample_images, "sidecar_manifest", "bunny_CryptoObject.exr").replace("\\", "/")

        self.read_obj = nuke.nodes.Read(file=obj_path)
        self.read_obj_dot = nuke.nodes.Dot(inputs=[self.read_obj])
        self.read_asset = nuke.nodes.Read(file=asset_path)
        self.read_material = nuke.nodes.Read(file=material_path)
        self.read_sidecar = nuke.nodes.Read(file=sidecar_path)

    @classmethod
    def tearDownClass(self):
        import nuke
        nuke.delete(self.read_obj)
        nuke.delete(self.read_obj_dot)
        nuke.delete(self.read_asset)
        nuke.delete(self.read_material)
        nuke.delete(self.read_sidecar)

    def setUp(self):
        import nuke
        self.gizmo = nuke.nodes.Cryptomatte(inputs=[self.read_asset])
        self.merge = nuke.nodes.Merge(inputs=[self.read_obj, self.read_asset], also_merge="all")
        self.copyMetadata = nuke.nodes.CopyMetaData(inputs=[self.merge, self.read_asset])

    def tearDown(self):
        import nuke
        nuke.delete(self.gizmo)
        nuke.delete(self.merge)
        nuke.delete(self.copyMetadata)

    #############################################
    # Keying constants (for cryptoAsset example)
    #############################################

    heroflower_expr = ("((uCryptoAsset00.red == 2.07262543558e+26) ? uCryptoAsset00.green : 0.0) + "
        "((uCryptoAsset00.blue == 2.07262543558e+26) ? uCryptoAsset00.alpha : 0.0) + "
        "((uCryptoAsset01.red == 2.07262543558e+26) ? uCryptoAsset01.green : 0.0) + "
        "((uCryptoAsset01.blue == 2.07262543558e+26) ? uCryptoAsset01.alpha : 0.0) + "
        "((uCryptoAsset02.red == 2.07262543558e+26) ? uCryptoAsset02.green : 0.0) + "
        "((uCryptoAsset02.blue == 2.07262543558e+26) ? uCryptoAsset02.alpha : 0.0) + 0"
    )

    black_pkr =             ("add", (700.0, 700.0))
    floweredge_pkr =        ("add", (884.0, 662.0))
    bunny_pkr =             ("add", (769.0, 429.0))
    set_pkr =               ("add", (490.0, 250.0)) # on this pixel, extracted alpha == 1.0
    bunnyflower_pkr =       ("add", (842.0, 441.0))
    rm_black_pkr =          ("remove", black_pkr[1])
    rm_floweredge_pkr =     ("remove", floweredge_pkr[1])
    rm_bunny_pkr =          ("remove", bunny_pkr[1])
    rm_set_pkr =            ("remove", set_pkr[1])
    rm_bunnyflower_pkr =    ("remove", bunnyflower_pkr[1])

    #############################################
    # Utils - Keying and sampling
    #############################################

    def key_on_image(self, *args):
        def pickerCoords(coord):
            return [0.0, 0.0, 0.0, 0.0, coord[0], coord[1], 0.0, 0.0 ]

        for action, coordinates in args:
            if action == "add":
                self.gizmo.knob("pickerAdd").setValue(pickerCoords(coordinates))
            elif action == "remove":
                self.gizmo.knob("pickerRemove").setValue(pickerCoords(coordinates))

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
        self.assertEqual(ml, value, "%s. (%s vs %s)" % (msg, value, ml))

    #############################################
    # Manifest tests
    #############################################

    def test_manifests(self):
        # Embedded and sidecar
        import cryptomatte_utilities as cu
        for read in [self.read_obj, self.read_asset, self.read_material, self.read_sidecar]:
            cinfo = cu.CryptomatteInfo(read)
            mismatches, collisions = cinfo.test_manifest(quiet=True)
            self.assertTrue(cinfo.parse_manifest(), 
                "%s manifest not loaded. " % read.knob("file").getValue())
            self.assertEqual(mismatches, [], 
                "%s manifest mismatch" % read.knob("file").getValue())

    #############################################
    # Layer Selection
    #############################################

    def test_layer_selection(self):
        # layer selection set up properly in the first place
        self.assertEqual(self.gizmo.knob("cryptoLayer").value(), "uCryptoAsset", 
            "Layer selection not set.")

        # switching inputs switches layer selections
        self.gizmo.setInput(0, self.read_obj)
        self.assertEqual(self.gizmo.knob("cryptoLayer").value(), "uCryptoObject",
            "Input change did not switch layers")

        # switching inputs to a multi-cryptomatte stream does not switch layer selections
        self.gizmo.setInput(0, self.read_asset)
        self.gizmo.setInput(0, self.copyMetadata)
        self.assertEqual(self.gizmo.knob("cryptoLayer").value(), "uCryptoAsset",
            "Input change to multi did not switch layers")
        
        self.gizmo.setInput(0, self.read_obj)
        self.gizmo.setInput(0, self.copyMetadata)
        self.assertEqual(self.gizmo.knob("cryptoLayer").value(), "uCryptoObject",
            "Input change to multi did not switch layers")

    def test_layer_lock(self):
        # locking layer selection stops the switching
        self.gizmo.setInput(0, self.read_asset)
        self.gizmo.knob("cryptoLayerLock").setValue(True)
        self.gizmo.setInput(0, self.read_obj_dot)
        self.assertEqual(self.gizmo.knob("cryptoLayer").value(), "uCryptoAsset",
            "cryptoLayerLock did not keep things from changing.")
        self.gizmo.knob("cryptoLayerLock").setValue(False)
        self.assertEqual(self.gizmo.knob("cryptoLayer").value(), "uCryptoObject",
            "Disabling cryptoLayerLock did not set gizmo back to uCryptoObject.")

    def test_layer_forced_update(self):
        import cryptomatte_utilities as cu
        self.gizmo.setInput(0, self.read_obj_dot)
        self.read_obj_dot.setInput(0, self.read_asset)
        if (self.gizmo.knob("cryptoLayer").value() != "uCryptoObject"):
            raise RuntimeError("Upstream changes now trigger updates, test is invalid")
        cu.update_cryptomatte_gizmo(self.gizmo, True)
        self.assertEqual(self.gizmo.knob("cryptoLayer").value(), "uCryptoObject",
            "Forced update should have changed layer selection %s" % self.gizmo.knob("cryptoLayer").value())
        self.read_obj_dot.setInput(0, self.read_obj) # cleanup

    #############################################
    # Keying
    #############################################

    def test_keying_nothing(self):
        import cryptomatte_utilities as cu

        self.key_on_image(self.black_pkr)
        self.assertMatteList("", "Something selected on black. ")

    def _test_keying_partial_black(self):
        # used as setup for other tests
        self.key_on_image(self.floweredge_pkr)
        self.assertMatteList("heroflower", "Hero flower not selected on partial pixels. ")
        self.assertEqual(self.gizmo.knob("expression").getValue(), self.heroflower_expr, 
            "Hero flower expression was wrong. ")

    def test_keying_partial_black(self):
        self._test_keying_partial_black()

    def test_keying_manual(self):
        self.gizmo.knob("matteList").setValue("heroflower")
        self.assertEqual(self.gizmo.knob("expression").getValue(), self.heroflower_expr, 
            "Expression did not update on setting matte list. ")

    def test_keying_blank_matteList(self):
        self._test_keying_partial_black()
        self.gizmo.knob("matteList").setValue("")
        self.assertEqual(self.gizmo.knob("expression").getValue(), "", 
            "Expression did not update on blanking matte list. ")

    def test_keying_clear(self):
        import cryptomatte_utilities as cu
        self._test_keying_partial_black()
        cu.clear_cryptomatte_gizmo(self.gizmo)
        self.assertMatteList("", "Clear() failed. ")
        self.assertEqual(self.gizmo.knob("expression").getValue(), "", "Clear() failed. ")

    def test_keying_multiselect(self):
        import cryptomatte_utilities as cu

        # Multiselect over partial black
        self.key_on_image(self.floweredge_pkr, self.floweredge_pkr, self.floweredge_pkr)
        self.assertMatteList("heroflower", 
            "Multiselect on edge didn't select only 'heroflower': (%s)" % self.gizmo.knob("matteList").getValue())
        
        # Multiselect over partial pixels
        cu.clear_cryptomatte_gizmo(self.gizmo)
        self.key_on_image(self.bunnyflower_pkr, self.black_pkr,self.bunnyflower_pkr)
        self.assertMatteList("bunny, heroflower", 
            "Same pixel multiple selection was wrong: (%s)" % self.gizmo.knob("matteList").getValue())

        # Add set to selection
        self.key_on_image(self.set_pkr)
        self.assertMatteList("bunny, heroflower, set", 
            "Multi selection was wrong: (%s)" % self.gizmo.knob("matteList").getValue())

        # Remove bunny and flower
        self.key_on_image(self.rm_bunny_pkr, self.rm_black_pkr, self.rm_floweredge_pkr) 
        self.assertMatteList("set", 
            "Bunny and flower not removed: (%s)" % self.gizmo.knob("matteList").getValue())

    def test_keying_single_selection(self):
        # Single selection
        self.gizmo.knob("matteList").setValue("bunny, heroflower, set")
        self.gizmo.knob("singleSelection").setValue(True)
        self.assertMatteList("bunny, heroflower, set", 
            "Single selection knob changed without selection changed matte list.")
        self.key_on_image(self.set_pkr)
        self.assertMatteList("set", 
            "Single selection seems to have failed: (%s)" % self.gizmo.knob("matteList").getValue())

        for _ in range(5):
            self.key_on_image(self.black_pkr, self.bunnyflower_pkr)
            self.assertMatteList("bunny", 
                "Single selection may be flickering on partials")

    def test_keying_stop_auto_update(self):
        self.gizmo.knob("stopAutoUpdate").setValue(True)
        self.gizmo.knob("expression").setValue(self.heroflower_expr)
        self.key_on_image(self.bunny_pkr) 
        self.key_on_image(self.rm_set_pkr)
        self.key_on_image(self.rm_black_pkr)
        self.gizmo.knob("matteList").setValue("hello") 
        self.assertEqual(self.gizmo.knob("expression").getValue(), self.heroflower_expr, 
            "Stop auto update did not work. ")

    #############################################
    # Output checking
    #############################################

    def test_output_keyable_surface(self):
        self.key_on_image(self.bunny_pkr)
        msg = "Selection did not light up properly. %s, %s"
        self.assertSampleEqual(self.bunny_pkr, "Keyable surface did not light up", 
            red=1.0, green=1.0, alpha=1.0)
        self.assertSampleNotEqual(self.set_pkr, "Set pixels should be dark.", 
            red=1.0, green=1.0)
        self.assertSampleEqual(self.set_pkr, "Set pixels should be unselected.", 
            alpha=0.0)

    def test_output_keyable_surface_disabled(self):
        # stops lighting up after disabled, but alpha still correct
        self.key_on_image(self.bunny_pkr)
        self.gizmo.knob("keyableSurfaceEnabled").setValue(False)
        self.assertSampleEqual(self.bunny_pkr, 
            "Keyable surface bunny pixels wrong when disabled", 
            red=0.0, green=0.0, alpha=1.0)
        self.assertSampleEqual(self.set_pkr, 
            "Keyable surface set pixels wrong when disabled", 
            red=0.0, green=0.0, alpha=0.0)
        self.gizmo.knob("keyableSurfaceEnabled").setValue(True)

    def test_output_keyable_surface_multi(self):
        # add an item, make sure it lights up too
        self.key_on_image(self.bunny_pkr, self.set_pkr)
        self.assertSampleEqual(self.bunny_pkr, 
            "Bunny pixels are wrong.", red=1.0, green=1.0, alpha=1.0)
        self.assertSampleEqual(self.set_pkr, 
            "Set pixels are wrong.", red=1.0, green=1.0, alpha=1.0)

    def _clear_manifest_cache(self):
        import cryptomatte_utilities as cu
        cu.g_cryptomatte_manf_from_names = {}
        cu.g_cryptomatte_manf_from_IDs = {}

    #############################################
    # Matte list manipulations
    #############################################

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

        mod_md_node = nuke.nodes.ModifyMetaData(
            inputs=[self.read_asset], 
            metadata='{set exr/cryptomatte/d593dd7/manifest "\{\}"}'
        )
        try:
            self.gizmo.setInput(0, mod_md_node)
            self._clear_manifest_cache()

            self.key_on_image(self.bunny_pkr)        
            self.assertMatteList(numeric_mlist_bunny, "Numeric mattelist incorrect.")
            
            # test adding redundant item numerically to a named selection
            self.gizmo.knob("matteList").setValue(name_mlist_bunny)
            self.key_on_image(self.bunny_pkr)
            self.assertMatteList("bunny",
                "Redundant matte list generated.")

            # test that removing named item by number works
            self.key_on_image(self.rm_bunny_pkr)
            self.assertMatteList("",
                "Removal of name by number failed.")

            # test that adding and removing numeric items works from a named list
            self.gizmo.knob("matteList").setValue("bunny, heroflower")
            self.key_on_image(self.set_pkr, self.rm_bunny_pkr)
            self.assertMatteList("<7.36562399642e+18>, heroflower", 
                "Removal of name by number failed.")
            self.key_on_image(self.bunny_pkr)
            self.assertMatteList("<3.36000126251e-27>, <7.36562399642e+18>, heroflower", 
                "Adding number to a name list failed.")
        except Exception, e:
            raise e
        finally:
            nuke.delete(mod_md_node) # now gizmo will be connected to just the gizmo

    def test_matte_list_name_modifications(self):
        self.gizmo.knob("matteList").setValue("<3.36000126251e-27>, <7.36562399642e+18>, heroflower")
        self.key_on_image(self.rm_bunny_pkr, self.rm_set_pkr, self.rm_floweredge_pkr, self.rm_floweredge_pkr)
        self.assertMatteList("", "Could not remove numbers by name.")
        self.key_on_image(self.bunny_pkr, self.set_pkr)
        self.assertMatteList("bunny, set", "Could not re-add by picking.")



#############################################
# Ad hoc test running
#############################################

def run_unit_tests():
    """ Utility function for manually running tests unit tests.
    Returns unittest results if there are failures, otherwise None """

    return run_tests(get_all_unit_tests())

def run_nuke_tests():
    """ Utility function for manually running tests inside Nuke
    Returns unittest results if there are failures, otherwise None """

    return run_tests(get_all_unit_tests() + get_all_nuke_tests())

def run_tests(test_cases):
    """ Utility function for manually running tests inside Nuke. 
    Returns results if there are failures, otherwise None """
    result = unittest.TestResult()
    result.failfast = True
    suite = unittest.TestSuite()
    for case in test_cases:
        suite.addTests(unittest.TestLoader().loadTestsFromTestCase(case))
    suite.run(result)
    for test_instance, traceback in result.failures:
        print "%s Failed: " % type(test_instance).__name__
        print 
        print traceback
        print "---------"
    for test_instance, traceback in result.errors:
        print "%s Error: " % type(test_instance).__name__
        print 
        print traceback
        print "---------"

    if result.failures or result.errors:
        print  "TESTING FAILED: %s failed, %s errors. (%s test cases.)" % (
            len(result.failures), len(result.errors), suite.countTestCases())
        return result
    else:
        print  "Testing passed: %s failed, %s errors. (%s test cases.)" % (
            len(result.failures), len(result.errors), suite.countTestCases())
        return None