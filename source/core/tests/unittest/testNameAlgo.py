# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import usdex.core
import usdex.test
from pxr import Sdf, Tf, Usd, UsdGeom


class TranscodingTestCase(usdex.test.TestCase):
    def testEncodeEmpty(self):
        self.assertEqual(
            usdex.core.getValidPrimName(""),
            "tn__",
        )

    def testEncodeUtf8Identifier(self):
        self.assertEqual(
            usdex.core.getValidPrimName("カーテンウォール"),
            "tn__sxB76l2Y5o0X16",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("straße 3"),
            "tn__strae3_h6im0",
        )

    def testEncodeAsciiIdentifier(self):
        self.assertEqual(
            usdex.core.getValidPrimName("hello"),
            "hello",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("tn__my_encoded_identifier_x134bc"),
            "tn__my_encoded_identifier_x134bc",
        )

    def testEncodeAsciiInvalid(self):
        self.assertEqual(
            usdex.core.getValidPrimName("123-456/555"),
            "tn__123456555_oDT",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("#123 4"),
            "tn__1234_d4I",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("1234567890"),
            "tn__1234567890_",
        )

    def testEncodeUtf8Character(self):
        self.assertEqual(
            usdex.core.getValidPrimName("٪"),
            "tn__zp0",
        )

    def testEncodeInvalidUtf8CodePoints(self):
        self.assertEqual(
            usdex.core.getValidPrimName(b"\x83"),
            "_",
        )
        self.assertEqual(
            usdex.core.getValidPrimName(b"\xc3\x28"),
            "__",
        )
        self.assertEqual(
            usdex.core.getValidPrimName(b"\xe2\x82\x28"),
            "___",
        )
        self.assertEqual(
            usdex.core.getValidPrimName(b"\xf0\x28\x8c\x28"),
            "____",
        )

    def testEncodeLimits(self):
        # U+0000
        self.assertEqual(
            usdex.core.getValidPrimName("\x00"),
            "tn__0",
        )
        # U+10FFFF
        self.assertEqual(
            usdex.core.getValidPrimName("\xf4\x8f\xbf\xbf"),
            "tn__o3Z22v5",
        )

    def testEncodeEmoji(self):
        self.assertEqual(
            usdex.core.getValidPrimName("😁"),
            "tn__nqd3",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("😍"),
            "tn__zqd3",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("😸"),
            "tn__gsd3",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("🙈"),
            "tn__wsd3",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("🙏"),
            "tn__Ytd3",
        )
        self.assertEqual(
            usdex.core.getValidPrimName("🙌"),
            "tn__Vtd3",
        )


class ValidPrimNamesTestCase(usdex.test.TestCase):
    def assertPropertyNameIsValid(self, name, msg=None):
        """Assert that the given name is valid for a UsdProperty"""
        path = Sdf.Path("/foo").AppendProperty(name)
        if msg is None:
            msg = f"Appending '{name}' as a property of an SdfPath produces an invalid path."
        self.assertTrue(path, msg=msg)

    def testGetValidPrimName(self):
        # An empty string will return the minimal valid name
        self.assertEqual(usdex.core.getValidPrimName(""), "tn__")

        # Illegal characters are correctly encoded
        self.assertEqual(usdex.core.getValidPrimName("/"), "tn__l0")
        self.assertEqual(usdex.core.getValidPrimName("#"), "tn__Z0")
        self.assertEqual(usdex.core.getValidPrimName(" "), "tn__W0")

        # Leading numerics are correctly encoded
        self.assertEqual(usdex.core.getValidPrimName("1"), "tn__1_")
        self.assertEqual(usdex.core.getValidPrimName("1_mesh"), "tn__1_mesh_")

        # A combination of illegal characters and leading numerics
        self.assertEqual(usdex.core.getValidPrimName("1 mesh"), "tn__1mesh_c5")

        # A valid name will return that same value
        self.assertEqual(usdex.core.getValidPrimName("_"), "_")
        self.assertEqual(usdex.core.getValidPrimName("_1"), "_1")
        self.assertEqual(usdex.core.getValidPrimName("mesh"), "mesh")

        # UTF-8 characters are correctly encoded and decoded.
        self.assertEqual(usdex.core.getValidPrimName("カーテンウォール"), "tn__sxB76l2Y5o0X16")

        # ISO-8859-1 encoding will cause encoding to fail resulting in the fallback character substitution being used.
        # The fallback character substitution slightly differs from pxr::TfMakeValidIdentifier in how it handles leading numerics
        self.assertEqual(usdex.core.getValidPrimName("mesh_Ä".encode("latin-1")), "mesh__")
        self.assertEqual(usdex.core.getValidPrimName("1_Ä".encode("latin-1")), "_1__")

    def testGetValidPrimNames(self):
        def assertEqualPrimNames(inputNames, reservedNames, expectNames):
            self.assertEqual(usdex.core.getValidPrimNames(inputNames, reservedNames), expectNames)

        # Basic tests
        assertEqualPrimNames(["cube", "cube_1", "sphere", "cube_3"], [], ["cube", "cube_1", "sphere", "cube_3"])

        # Invalid characters
        assertEqualPrimNames(
            ["123cube", "cube1", r"sphere%$%#ad@$1", "cube_3", "cube$3"],
            [],
            ["tn__123cube_", "cube1", "tn__spheread1_kAHAJ8jC", "cube_3", "tn__cube3_Y6"],
        )

        # Duplicated names in list
        assertEqualPrimNames(["cube", "sphere", "sphere", "cube_1", "cube_1"], [], ["cube", "sphere", "sphere_1", "cube_1", "cube_1_1"])

        # Reserved names
        assertEqualPrimNames(
            ["cube_1", "sphere", "sphere", "sphere_1", "cube_1"],
            ["cube_1", "cube_1_1", "cube_3", "sphere_1", "sphere_1_1"],
            ["cube_1_2", "sphere", "sphere_2", "sphere_1_2", "cube_1_3"],
        )

        # Double underscores
        assertEqualPrimNames(
            ["cube__1", "cube__1", "sphere", "sphere", "cube__1"],
            ["sphere_1"],
            ["cube__1", "cube__1_1", "sphere", "sphere_2", "cube__1_2"],
        )

        # Collisions created when making values valid
        assertEqualPrimNames(["100_mesh", "200_mesh", "300_mesh"], [], ["tn__100_mesh_", "tn__200_mesh_", "tn__300_mesh_"])

        # Empty string names
        assertEqualPrimNames(["", "", ""], [], ["tn__", "_1", "_2"])

        # Empty name
        assertEqualPrimNames([], [], [])

        # Return as many preferred names as possible
        assertEqualPrimNames(["sphere", "sphere", "sphere_1", "sphere", "sphere_2"], [], ["sphere", "sphere_3", "sphere_1", "sphere_4", "sphere_2"])

        # UTF-8 words
        assertEqualPrimNames(["カーテンウォール", "カーテンウォール"], [], ["tn__sxB76l2Y5o0X16", "tn___1_cvb0DAd4k7Z1p16"])

        # ISO-8859-1 encoding will cause encoding to fail resulting in the fallback character substitution being used.
        # This can increase the number of name collisions.
        assertEqualPrimNames(
            [x.encode("latin-1") for x in ["mesh_Ä", "mesh-Ä", "mesh/Ä", "mesh.Ä"]],
            [],
            ["mesh__", "mesh___1", "mesh___2", "mesh___3"],
        )

    def testGetValidChildName(self):
        # Define a prim for which we will get a valid child name
        stage = Usd.Stage.CreateInMemory()
        prim = UsdGeom.Xform.Define(stage, "/Root").GetPrim()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        self.assertIsValidUsd(stage)

        # Add a child with a "def" specifier
        UsdGeom.Xform.Define(stage, "/Root/cube")
        # Add a child with an "class" specifier
        stage.CreateClassPrim("/Root/cube_1")
        # Add a child with an "over" specifier
        UsdGeom.Xform.Define(stage, "/Root/cube_2")
        # Define and deactivate a child
        UsdGeom.Xform.Define(stage, "/Root/cube_3").GetPrim().SetActive(False)

        # Existing names on stage with inactivate prim
        self.assertEqual(usdex.core.getValidChildName(prim, "cube"), "cube_4")
        self.assertEqual(usdex.core.getValidChildName(prim, "cube_1"), "cube_1_1")
        self.assertEqual(usdex.core.getValidChildName(prim, "sphere"), "sphere")
        self.assertEqual(usdex.core.getValidChildName(prim, "cube_3"), "cube_3_1")

        # Illegal names
        self.assertEqual(usdex.core.getValidChildName(prim, "123cube"), "tn__123cube_")
        self.assertEqual(usdex.core.getValidChildName(prim, r"sphere%$%#ad@$1"), "tn__spheread1_kAHAJ8jC")
        self.assertEqual(usdex.core.getValidChildName(prim, "cube$3"), "tn__cube3_Y6")
        self.assertEqual(usdex.core.getValidChildName(prim, ""), "tn__")

    def testGetValidChildNames(self):
        # Define a prim for which we will get valid child names
        stage = Usd.Stage.CreateInMemory()
        prim = UsdGeom.Xform.Define(stage, "/Root").GetPrim()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        self.assertIsValidUsd(stage)

        # Add a child with a "def" specifier
        UsdGeom.Xform.Define(stage, "/Root/cube")
        # Add a child with an "class" specifier
        stage.CreateClassPrim("/Root/cube_1")
        # Add a child with an "over" specifier
        UsdGeom.Xform.Define(stage, "/Root/cube_2")
        # Define and deactivate a child
        UsdGeom.Xform.Define(stage, "/Root/cube_3").GetPrim().SetActive(False)

        def assertEqualPrimNames(inputNames, expectNames):
            self.assertEqual(usdex.core.getValidChildNames(prim, inputNames), expectNames)

        # Exist names on stage with inactivate prim
        assertEqualPrimNames(["cube", "cube_1", "sphere", "cube_3"], ["cube_4", "cube_1_1", "sphere", "cube_3_1"])

        # Exist names on stage with inactivate prim - invalid characters
        assertEqualPrimNames(
            ["123cube", "cube1", r"sphere%$%#ad@$1", "cube_3", "cube$3"],
            ["tn__123cube_", "cube1", "tn__spheread1_kAHAJ8jC", "cube_3_1", "tn__cube3_Y6"],
        )

        # Duplicated names in list
        assertEqualPrimNames(["cube", "sphere", "sphere", "cube_1"], ["cube_4", "sphere", "sphere_1", "cube_1_1"])

        # Conflicted names
        assertEqualPrimNames(["cube_1", "sphere", "sphere", "sphere_1", "cube_1"], ["cube_1_1", "sphere", "sphere_2", "sphere_1", "cube_1_2"])

        # Double underscores
        assertEqualPrimNames(["cube__1", "cube__1", "sphere", "sphere", "cube__1"], ["cube__1", "cube__1_1", "sphere", "sphere_1", "cube__1_2"])

        # Collisions created when making values valid
        assertEqualPrimNames(["100_mesh", "200_mesh", "300_mesh"], ["tn__100_mesh_", "tn__200_mesh_", "tn__300_mesh_"])

        # Empty string names
        assertEqualPrimNames(["", "", ""], ["tn__", "_1", "_2"])

        # Empty name
        assertEqualPrimNames([], [])

        # Return as many preferred names as possible
        assertEqualPrimNames(["sphere", "sphere", "sphere_1", "sphere", "sphere_2"], ["sphere", "sphere_3", "sphere_1", "sphere_4", "sphere_2"])

        self.assertIsValidUsd(stage)

    def testGetValidPropertyName(self):
        # Test cases for getValidPropertyName() where the values are (<name>, <result>)
        data = [
            # An empty string will return the minimal valid name
            ("", "tn__"),
            # Names containing only delimiters will imply an empty string before, after and between delimiters
            (":", "tn__:tn__"),
            ("::", "tn__:tn__:tn__"),
            # In the presence of valid names delimiters still imply a minimum of empty string before, after and between delimiters
            (":name", "tn__:name"),
            ("name:", "name:tn__"),
            ("name::name", "name:tn__:name"),
            ("name:name::", "name:name:tn__:tn__"),
            ("::name:name", "tn__:tn__:name:name"),
            # Illegal characters are correctly encoded, but encoding occurs within namespaces
            ("/", "tn__l0"),
            ("/:name:/", "tn__l0:name:tn__l0"),
            ("name:#:#", "name:tn__Z0:tn__Z0"),
            (" :%:", "tn__W0:tn__b0:tn__"),
            # Leading numerics are correctly encoded
            ("1", "tn__1_"),
            ("1:2:3", "tn__1_:tn__2_:tn__3_"),
            ("1_name", "tn__1_name_"),
            # A combination of illegal characters and leading numerics
            ("1 name", "tn__1name_c5"),
            # A property SdfPath will be encoded as it contains additional delimiters that a property name cannot support
            # These tests are included to assert our requirements that differ from the behavior of default transcoding
            ("/foo/bar.property:name:space", "tn__foobarproperty_jLG4:name:space"),
            ("/foo/bar.property[/target].relAttr", "tn__foobarpropertytargetrelAttr_se0LU4Hhk0V2"),
            ("/foo/bar{var=sel}", "tn__foobarvarsel_rI4Z6dV0o0"),
            # A valid name will return that same value
            ("_", "_"),
            ("_1", "_1"),
            ("name", "name"),
            ("primvars:my:color", "primvars:my:color"),
            # UTF-8 characters are correctly encoded.
            ("カーテンウォール", "tn__sxB76l2Y5o0X16"),
            ("カーテンウォール:Bäcker", "tn__sxB76l2Y5o0X16:tn__Bcker_ah0"),
        ]

        # Assert that each test returns the expected result and that the name is in fact a valid property name.
        # FUTURE: Add an assertion about decoding once that is supported.
        for name, expected in data:
            returned = usdex.core.getValidPropertyName(name)
            self.assertEqual(returned, expected, msg=f"Unexpected result calling getValidPropertyName('{name}')")
            self.assertPropertyNameIsValid(returned)

    def testGetValidPropertyNames(self):
        # Test cases for getValidPropertyNames() where the values are (<names>, <reservedNames>, <result>)
        data = [
            # An empty list is supported
            ([], [], []),
            # Empty values are supported via encoding, when empty values collide the numeric suffix alone is legal and will not be encoded
            ([""], [], ["tn__"]),
            (["", ""], [], ["tn__", "_1"]),
            # Valid names are supported and will have a numeric suffix added when they collide
            (["foo", "bar"], [], ["foo", "bar"]),
            (["foo", "foo"], [], ["foo", "foo_1"]),
            (["foo", "foo"], ["foo"], ["foo_1", "foo_2"]),
            # The supplied name will be used for any index if possible, even if another collision would generate that name
            (["foo", "foo", "foo_1"], [], ["foo", "foo_2", "foo_1"]),
            (["foo", "foo_1"], ["foo"], ["foo_2", "foo_1"]),
            # When namespaced property names collide the last token will have a numeric suffix added
            # The same rules about using requested names where possible apply
            (["foo:bar", "foo:bar"], [], ["foo:bar", "foo:bar_1"]),
            (["foo:bar", "foo:bar", "foo:bar_1"], [], ["foo:bar", "foo:bar_2", "foo:bar_1"]),
            # Names with illegal characters (from a property name POV) will be encoded, the encoding will happen within each namespace
            (["foo bar", "1_foo", "foo/bar", "foo.bar"], [], ["tn__foobar_f6", "tn__1_foo_", "tn__foobar_r9", "tn__foobar_k9"]),
            (["foo bar:1_foo", "foo/bar:foo.bar"], [], ["tn__foobar_f6:tn__1_foo_", "tn__foobar_r9:tn__foobar_k9"]),
            # UTF-8 characters will be encoded and collisions will be resolved before encoding
            (["カーテンウォール", "Bäcker"], [], ["tn__sxB76l2Y5o0X16", "tn__Bcker_ah0"]),
            (["fooØ:münich", "fooØ:münich"], [], ["tn__foo_zQ:tn__mnich_ul0", "tn__foo_zQ:tn__mnich_1_XX1"]),
            # When an encoded names collides with a reserved or requested name, the numeric suffix appears to be added happen
            ([""], ["tn__"], ["_1"]),
            # NOTE: This is an unexpected result, but is probably of little concern
            # I would prefer the result to be ["_1", "tn__", "tn___1"] so that;
            # - the 1st value is made unique by adding a suffix before encoding.
            # - the 2nd value is retained because it can be.
            # - the 3rd value is made unique by adding a suffix.
            (["", "tn__", "tn__"], [], ["tn__", "tn___1", "tn___2"]),
        ]

        # FUTURE: Add an assertion about decoding once that is supported.
        for names, reservedNames, expected in data:
            returned = usdex.core.getValidPropertyNames(names, reservedNames=reservedNames)

            # There should always be the same number of values in the return as the number of names supplied.
            msg = f"Unexpected result count calling getValidPropertyName({str(names)}, reservedNames={str(reservedNames)})"
            self.assertEqual(len(names), len(returned), msg=msg)

            # There should never be any duplicates in the return
            msg = f"Duplicate names produced calling getValidPropertyName({str(names)}, reservedNames={str(reservedNames)})"
            self.assertTrue((len(returned) == len(set(returned))), msg=msg)

            # The result should match
            msg = f"Unexpected result calling getValidPropertyName({str(names)}, reservedNames={str(reservedNames)})"
            self.assertEqual(returned, expected, msg=msg)

            # None of the reserved names should have been returned
            for name in reservedNames:
                msg = f"Reserved name returned when calling getValidPropertyName({str(names)}, reservedNames={str(reservedNames)})"
                self.assertNotIn(name, returned, msg=msg)

            # Each name returned should be valid for a property name
            for name in returned:
                msg = f"Invalid property name '{name}' returned when calling getValidPropertyName({str(names)}, reservedNames={str(reservedNames)})"
                self.assertPropertyNameIsValid(name, msg=msg)

    def testGetValidPropertyNamesForMultiApplySchema(self):
        # The getValidPropertyNames() function can be used to get valid and unique names that can be used with multi-apply schema

        def getAllCollectionNames(prim):
            return [x.GetName() for x in Usd.CollectionAPI.GetAllCollections(prim)]

        # Define a prim on which to apply some collections
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        prim = stage.GetPrimAtPath("/Root")

        # Apply some that we know are valid
        Usd.CollectionAPI.Apply(prim, "foo")
        Usd.CollectionAPI.Apply(prim, "bar")

        # Assert the expected collection names
        self.assertEqual(set(getAllCollectionNames(prim)), set(["foo", "bar"]))

        # With the existing collection names reserved apply the same named collections again
        # The names will be made unique and valid and the new collections will not collide
        names = ["foo", "bar"]
        for name in usdex.core.getValidPropertyNames(names, reservedNames=getAllCollectionNames(prim)):
            Usd.CollectionAPI.Apply(prim, name)

        # Assert the expected collection names
        self.assertEqual(set(getAllCollectionNames(prim)), set(["foo", "bar", "foo_1", "bar_1"]))

        # Apply some collections with names that are illegal for properties
        names = ["😍.😸", "Bäcker", "foo bar"]
        for name in usdex.core.getValidPropertyNames(names, reservedNames=getAllCollectionNames(prim)):
            Usd.CollectionAPI.Apply(prim, name)

        # Assert the expected collection names
        self.assertEqual(set(getAllCollectionNames(prim)), set(["foo", "bar", "foo_1", "bar_1", "tn__foobar_f6", "tn__Bcker_ah0", "tn__k0zfn7c3"]))


class NameCacheTestCase(usdex.test.TestCase):
    """
    Assert the expected behavior of the NameCache class

    The test in this case assume that the underlying getValidChildNames() and getValidPropertyNames() behave as expected.
    Only the interface and caching behavior of the NameCache class are exercised.
    """

    def setUp(self):
        super().setUp()

        self.layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        self.stage: Usd.Stage = Usd.Stage.Open(self.layer)
        self.nameCache = usdex.core.NameCache()

    def assertInvalidPathParentArg(self, func, args, result, msg, root):
        # A non-absolute SdfPath cannot be used as a stable cache key, so will return an invalid token
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
            self.assertEqual(func(Sdf.Path(), *args), result)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
            self.assertEqual(func(Sdf.Path("relative/path"), *args), result)

        # A non-prim SdfPath cannot be used as a meaningful cache key, so will return an invalid token
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
            self.assertEqual(func(Sdf.Path("/path.property"), *args), result)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
            self.assertEqual(func(Sdf.Path(".property"), *args), result)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
            self.assertEqual(func(Sdf.Path("/foo{color=red}"), *args), result)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
            self.assertEqual(func(Sdf.Path("/foo{color=red}bar"), *args), result)

        # The absolute root path is not valid for some functions because it cannot have properties
        if not root:
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
                self.assertEqual(func(Sdf.Path.absoluteRootPath, *args), result)

    def assertInvalidPrimParentArg(self, func, args, result, msg, root):
        # An invalid UsdPrim does not have a path that can be used as a stable cache key, so will return an invalid token
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
            self.assertEqual(func(Usd.Prim(), *args), result)

        # The pseudo root prim is not valid for some functions because it cannot have properties
        if not root:
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
                self.assertEqual(func(self.stage.GetPseudoRoot(), *args), result)

    def assertInvalidPrimSpecParentArg(self, func, args, result, msg, root):
        # An invalid SdfPrimSpec does not have a path that can be used as a stable cache key, so will return an invalid token
        # TODO: Find a way to pass an invalid SdfPrimSpec through to c++

        # The pseudo root prim spec is not valid for some functions because it cannot have properties
        if not root:
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, msg)]):
                self.assertEqual(func(self.layer.pseudoRoot, *args), result)

    def testGetPrimNameParentTypes(self):
        # An SdfPath can be passed as the parent and a valid an unique name will be returned
        parent: Sdf.Path = Sdf.Path("/path")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo_1")

        # A UsdPrim can be passed as the parent and a valid an unique name will be returned
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/prim"))
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo_1")

        # An SdfPrimSpec can be passed as the parent and a valid an unique name will be returned
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/primSpec"))
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo_1")

        # A mixture of the three parent types can be used to get unique names, provided they have the same path
        path: Sdf.Path = Sdf.Path("/mixed")
        prim: Usd.Prim = self.stage.DefinePrim(path)
        primSpec: Sdf.PrimSpec = self.layer.GetPrimAtPath(path)
        self.assertEqual(self.nameCache.getPrimName(path, "foo"), "foo")
        self.assertEqual(self.nameCache.getPrimName(prim, "foo"), "foo_1")
        self.assertEqual(self.nameCache.getPrimName(primSpec, "foo"), "foo_2")

    def testGetPrimNameExistingChildren(self):
        # If a UsdPrim has existing children, then those names will be reserved when the names for that path are requested
        # Existing child prim names are reserved regardless of specifier, active state, or being instance proxies. Composition is respected.
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/prim"))
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo"))
        self.stage.OverridePrim(parent.GetPath().AppendChild("foo_1"))
        self.stage.CreateClassPrim(parent.GetPath().AppendChild("foo_2"))
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo_3")).SetActive(False)
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo_4")
        # TODO: Add instance proxy and composition example

        # However child names are not reserved if the path exists in the NameCache before the prims are defined
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo_5"))
        self.assertEqual(self.nameCache.getPrimName(parent, "foo_5"), "foo_5")

        # If an SdfPrimSpec has existing children, then those names will be reserved when the names for that path are requested
        # Existing child prim names are reserved regardless of specifier or active state. Composition is NOT respected.
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/primSpec"))
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo")).specifier = Sdf.SpecifierDef
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_1")).specifier = Sdf.SpecifierOver
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_2")).specifier = Sdf.SpecifierClass
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_3")).active = False
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo_4")
        # TODO: Add composition example

        # However child names are not reserved if the path exists in the NameCache before the prims are defined
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_5"))
        self.assertEqual(self.nameCache.getPrimName(parent, "foo_5"), "foo_5")

    def testGetPrimNameInvalidParent(self):
        func, args, result, message = self.nameCache.getPrimName, ["foo"], "", "Unable to get prim name:"
        self.assertInvalidPathParentArg(func, args, result, message, True)
        self.assertInvalidPrimParentArg(func, args, result, message, True)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, True)

    def testGetPrimNamePseudoRootParent(self):
        # The absolute root path, pseudo root prim and pseudo root prim spec are all valid and equal
        self.assertEqual(self.nameCache.getPrimName(Sdf.Path.absoluteRootPath, "foo"), "foo")
        self.assertEqual(self.nameCache.getPrimName(self.stage.GetPseudoRoot(), "foo"), "foo_1")
        self.assertEqual(self.nameCache.getPrimName(self.layer.pseudoRoot, "foo"), "foo_2")

    def testGetPrimNameReservedNameCollision(self):
        # Because names are requested one at a time it is not possible to check that future preferred names are not reserved
        # This means that the names returned by repeated calls to `getPrimName()` can differ from a single call to `getPrimNames()`
        parent: Sdf.Path = Sdf.Path("/path")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo_1")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo_1"), "foo_1_1")

    def testGetPrimNamesReservedNameCollision(self):
        # When making a name unique we check for the new name in the preferred names list to maximizes the number of preferred names returned.
        # This means that the names returned by a single call to `getPrimNames()` can differ from repeated calls to `getPrimName()`
        parent: Sdf.Path = Sdf.Path("/path")
        self.assertEqual(self.nameCache.getPrimNames(parent, ["foo", "foo", "foo_1"]), ["foo", "foo_2", "foo_1"])

    def testGetPrimNamesParentTypes(self):
        # An SdfPath can be passed as the parent and valid an unique names will be returned
        parent: Sdf.Path = Sdf.Path("/path")
        self.assertEqual(self.nameCache.getPrimNames(parent, ["foo", "foo"]), ["foo", "foo_1"])

        # A UsdPrim can be passed as the parent and valid an unique names will be returned
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/prim"))
        self.assertEqual(self.nameCache.getPrimNames(parent, ["foo", "foo"]), ["foo", "foo_1"])

        # An SdfPrimSpec can be passed as the parent and a valid an unique name will be returned
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/primSpec"))
        self.assertEqual(self.nameCache.getPrimNames(parent, ["foo", "foo"]), ["foo", "foo_1"])

        # A mixture of the three parent types can be used to get unique names, provided they have the same path
        path: Sdf.Path = Sdf.Path("/mixed")
        prim: Usd.Prim = self.stage.DefinePrim(path)
        primSpec: Sdf.PrimSpec = self.layer.GetPrimAtPath(path)
        self.assertEqual(self.nameCache.getPrimNames(path, ["foo", "foo"]), ["foo", "foo_1"])
        self.assertEqual(self.nameCache.getPrimNames(prim, ["foo", "foo"]), ["foo_2", "foo_3"])
        self.assertEqual(self.nameCache.getPrimNames(primSpec, ["foo", "foo"]), ["foo_4", "foo_5"])

    def testGetPrimNamesExistingChildren(self):
        # If a UsdPrim has existing children, then those names will be reserved when the names for that path are requested
        # Existing child prim names are reserved regardless of specifier, active state, or being instance proxies. Composition is respected.
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/prim"))
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo"))
        self.stage.OverridePrim(parent.GetPath().AppendChild("foo_1"))
        self.stage.CreateClassPrim(parent.GetPath().AppendChild("foo_2"))
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo_3")).SetActive(False)
        self.assertEqual(self.nameCache.getPrimNames(parent, ["foo", "foo"]), ["foo_4", "foo_5"])
        # TODO: Add instance proxy and composition example

        # However child names are not reserved if the path exists in the NameCache before the prims are defined
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo_6"))
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo_7"))
        self.assertEqual(self.nameCache.getPrimNames(parent, ["foo_6", "foo_7"]), ["foo_6", "foo_7"])

        # If an SdfPrimSpec has existing children, then those names will be reserved when the names for that path are requested
        # Existing child prim names are reserved regardless of specifier or active state. Composition is NOT respected.
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/primSpec"))
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo")).specifier = Sdf.SpecifierDef
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_1")).specifier = Sdf.SpecifierOver
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_2")).specifier = Sdf.SpecifierClass
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_3")).active = False
        self.assertEqual(self.nameCache.getPrimNames(parent, ["foo", "foo"]), ["foo_4", "foo_5"])
        # TODO: Add composition example

        # However child names are not reserved if the path exists in the NameCache before the prims are defined
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_6"))
        Sdf.CreatePrimInLayer(self.layer, parent.path.AppendChild("foo_7"))
        self.assertEqual(self.nameCache.getPrimNames(parent, ["foo_6", "foo_7"]), ["foo_6", "foo_7"])

    def testGetPrimNamesInvalidParent(self):
        func, args, result, message = self.nameCache.getPrimNames, [["foo", "foo"]], [], "Unable to get prim names:"
        self.assertInvalidPathParentArg(func, args, result, message, True)
        self.assertInvalidPrimParentArg(func, args, result, message, True)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, True)

    def testGetPrimNamesPseudoRootParent(self):
        # The absolute root path, pseudo root prim and pseudo root prim spec are all valid and equal
        self.assertEqual(self.nameCache.getPrimNames(Sdf.Path.absoluteRootPath, ["foo", "foo"]), ["foo", "foo_1"])
        self.assertEqual(self.nameCache.getPrimNames(self.stage.GetPseudoRoot(), ["foo", "foo"]), ["foo_2", "foo_3"])
        self.assertEqual(self.nameCache.getPrimNames(self.layer.pseudoRoot, ["foo", "foo"]), ["foo_4", "foo_5"])

    def testGetPropertyNameParentTypes(self):
        # An SdfPath can be passed as the parent and a valid an unique name will be returned
        parent: Sdf.Path = Sdf.Path("/path")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo_1")

        # A UsdPrim can be passed as the parent and a valid an unique name will be returned
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/prim"))
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo_1")

        # An SdfPrimSpec can be passed as the parent and a valid an unique name will be returned
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/primSpec"))
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo_1")

        # A mixture of the three parent types can be used to get unique names, provided they have the same path
        path: Sdf.Path = Sdf.Path("/mixed")
        prim: Usd.Prim = self.stage.DefinePrim(path)
        primSpec: Sdf.PrimSpec = self.layer.GetPrimAtPath(path)
        self.assertEqual(self.nameCache.getPropertyName(path, "foo"), "foo")
        self.assertEqual(self.nameCache.getPropertyName(prim, "foo"), "foo_1")
        self.assertEqual(self.nameCache.getPropertyName(primSpec, "foo"), "foo_2")

    def testGetPropertyNameExistingChildren(self):
        # If a UsdPrim has existing properties, then those names will be reserved when the names for that path are requested
        # Existing property names are reserved regardless of them being relationships, attributes, authored, un-authored or blocked.
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/prim"))
        parent.CreateRelationship("foo")
        parent.CreateAttribute("foo_1", Sdf.ValueTypeNames.Bool)
        parent.CreateAttribute("foo_2", Sdf.ValueTypeNames.Bool).Set(False)
        parent.CreateAttribute("foo_3", Sdf.ValueTypeNames.Bool).Block()
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo_4")

        # However property names are not reserved if the path exists in the NameCache before the properties are defined
        parent.CreateRelationship("foo_5")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo_5"), "foo_5")

        # Schema properties are reserved for concrete and applied schema
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/meshPrim"), "Mesh")
        Usd.CollectionAPI.Apply(parent, "foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "points"), "points_1")
        self.assertEqual(self.nameCache.getPropertyName(parent, "collection:foo:expansionRule"), "collection:foo:expansionRule_1")

        # Composition is respected.
        # # TODO: Add composition example

        # If an SdfPrimSpec has existing children, then those names will be reserved when the names for that path are requested
        # Existing child prim names are reserved regardless of specifier or active state.
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/primSpec"))
        Sdf.RelationshipSpec(parent, "foo")
        Sdf.AttributeSpec(parent, "foo_1", Sdf.ValueTypeNames.Bool)
        Sdf.AttributeSpec(parent, "foo_2", Sdf.ValueTypeNames.Bool).defaultValue = True
        Sdf.AttributeSpec(parent, "foo_3", Sdf.ValueTypeNames.Bool).defaultValue = Sdf.ValueBlock
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo_4")

        # However child names are not reserved if the path exists in the NameCache before the prims are defined
        Sdf.RelationshipSpec(parent, "foo_5")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo_5"), "foo_5")

        # Schema properties are NOT reserved for concrete and applied schema
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/meshPrimSpec"), "Mesh")
        Usd.CollectionAPI.Apply(parent, "foo")
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/meshPrimSpec"))
        parent.typeName == "Mesh"
        Usd.CollectionAPI.Apply(self.stage.GetPrimAtPath(parent.path), "foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "points"), "points")
        self.assertEqual(self.nameCache.getPropertyName(parent, "collection:foo:expansionRule"), "collection:foo:expansionRule")

        # Composition is NOT respected.
        # TODO: Add composition example

    def testGetPropertyNameInvalidParent(self):
        func, args, result, message = self.nameCache.getPropertyName, ["foo"], "", "Unable to get property name:"
        self.assertInvalidPathParentArg(func, args, result, message, False)
        self.assertInvalidPrimParentArg(func, args, result, message, False)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, False)

    def testGetPropertyNamesParentTypes(self):
        # An SdfPath can be passed as the parent and valid and unique names will be returned
        parent: Sdf.Path = Sdf.Path("/path")
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["foo", "foo"]), ["foo", "foo_1"])

        # A UsdPrim can be passed as the parent and valid and unique names will be returned
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/prim"))
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["foo", "foo"]), ["foo", "foo_1"])

        # An SdfPrimSpec can be passed as the parent and valid and unique names will be returned
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/primSpec"))
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["foo", "foo"]), ["foo", "foo_1"])

        # A mixture of the three parent types can be used to get unique names, provided they have the same path
        path: Sdf.Path = Sdf.Path("/mixed")
        prim: Usd.Prim = self.stage.DefinePrim(path)
        primSpec: Sdf.PrimSpec = self.layer.GetPrimAtPath(path)
        self.assertEqual(self.nameCache.getPropertyNames(path, ["foo", "foo"]), ["foo", "foo_1"])
        self.assertEqual(self.nameCache.getPropertyNames(prim, ["foo", "foo"]), ["foo_2", "foo_3"])
        self.assertEqual(self.nameCache.getPropertyNames(primSpec, ["foo", "foo"]), ["foo_4", "foo_5"])

    def testGetPropertyNamesExistingChildren(self):
        # If a UsdPrim has existing properties, then those names will be reserved when the names for that path are requested
        # Existing property names are reserved regardless of them being relationships, attributes, authored, un-authored or blocked.
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/prim"))
        parent.CreateRelationship("foo")
        parent.CreateAttribute("foo_1", Sdf.ValueTypeNames.Bool)
        parent.CreateAttribute("foo_2", Sdf.ValueTypeNames.Bool).Set(False)
        parent.CreateAttribute("foo_3", Sdf.ValueTypeNames.Bool).Block()
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["foo", "foo"]), ["foo_4", "foo_5"])

        # However property names are not reserved if the path exists in the NameCache before the properties are defined
        parent.CreateRelationship("foo_6")
        parent.CreateRelationship("foo_7")
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["foo_6", "foo_7"]), ["foo_6", "foo_7"])

        # Schema properties are reserved for concrete and applied schema
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/meshPrim"), "Mesh")
        Usd.CollectionAPI.Apply(parent, "foo")
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["points"]), ["points_1"])
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["collection:foo:expansionRule"]), ["collection:foo:expansionRule_1"])

        # Composition is respected.
        # # TODO: Add composition example

        # If a SdfPrimSpec has existing properties, then those names will be reserved when the names for that path are requested
        # Existing property names are reserved regardless of them being relationships, attributes, authored, un-authored or blocked.
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/primSpec"))
        Sdf.RelationshipSpec(parent, "foo")
        Sdf.AttributeSpec(parent, "foo_1", Sdf.ValueTypeNames.Bool)
        Sdf.AttributeSpec(parent, "foo_2", Sdf.ValueTypeNames.Bool).defaultValue = True
        Sdf.AttributeSpec(parent, "foo_3", Sdf.ValueTypeNames.Bool).defaultValue = Sdf.ValueBlock
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["foo", "foo"]), ["foo_4", "foo_5"])

        # However child names are not reserved if the path exists in the NameCache before the prims are defined
        Sdf.RelationshipSpec(parent, "foo_6")
        Sdf.RelationshipSpec(parent, "foo_7")
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["foo_6", "foo_7"]), ["foo_6", "foo_7"])

        # Schema properties are NOT reserved for concrete and applied schema
        parent: Usd.Prim = self.stage.DefinePrim(Sdf.Path("/meshPrimSpec"), "Mesh")
        Usd.CollectionAPI.Apply(parent, "foo")
        parent: Sdf.PrimSpec = Sdf.CreatePrimInLayer(self.layer, Sdf.Path("/meshPrimSpec"))
        parent.typeName == "Mesh"
        Usd.CollectionAPI.Apply(self.stage.GetPrimAtPath(parent.path), "foo")
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["points"]), ["points"])
        self.assertEqual(self.nameCache.getPropertyNames(parent, ["collection:foo:expansionRule"]), ["collection:foo:expansionRule"])

        # Composition is NOT respected.
        # TODO: Add composition example

    def testGetPropertyNamesInvalidParent(self):
        func, args, result, message = self.nameCache.getPropertyNames, [["foo", "foo"]], [], "Unable to get property names:"
        self.assertInvalidPathParentArg(func, args, result, message, False)
        self.assertInvalidPrimParentArg(func, args, result, message, False)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, False)

    def testUpdatePrimNames(self):
        # Updates to the stage are not reflected in the reserved names if a path exists in the NameCache
        # The updatePrimNames() function forces the names of existing child prims to be added to the reserved names

        # Add path to the NameCache
        parent = self.stage.DefinePrim("/parent")
        self.nameCache.getPrimName(parent, "test")

        # Defining a child does not stop that name from being returned
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo"))
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo")

        # Defining a child then calling updatePrimNames() does stop that name from being returned
        self.stage.DefinePrim(parent.GetPath().AppendChild("bar"))
        self.nameCache.updatePrimNames(parent)
        self.assertEqual(self.nameCache.getPrimName(parent, "bar"), "bar_1")

        # The update does not clear already reserved names that are not child prim names
        self.assertEqual(self.nameCache.getPrimName(parent, "test"), "test_1")

        # An SdfPrimSpec can also be passed to updatePrimNames()
        self.stage.DefinePrim(parent.GetPath().AppendChild("baz"))
        self.nameCache.updatePrimNames(self.layer.GetPrimAtPath(parent.GetPath()))
        self.assertEqual(self.nameCache.getPrimName(parent, "baz"), "baz_1")

        # The update does not clear already reserved names that are not existing prim names
        self.assertEqual(self.nameCache.getPrimName(parent, "test"), "test_2")

    def testUpdatePrimNamesInvalidParent(self):
        func, args, result, message = self.nameCache.updatePrimNames, [], None, "Unable to update prim names:"
        self.assertInvalidPrimParentArg(func, args, result, message, True)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, True)

    def testUpdatePropertyNames(self):
        # Updates to the stage are not reflected in the reserved names if a path exists in the NameCache
        # The updatePropertyNames() function forces the names of existing properties to be added to the reserved names

        # Add path to the NameCache
        parent = self.stage.DefinePrim("/parent")
        self.nameCache.getPropertyName(parent, "test")

        # Defining a property does not stop that name from being returned
        parent.CreateRelationship("foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo")

        # Defining a property then calling updatePrimNames() does stop that name from being returned
        parent.CreateRelationship("bar")
        self.nameCache.updatePropertyNames(parent)
        self.assertEqual(self.nameCache.getPropertyName(parent, "bar"), "bar_1")

        # The update does not clear already reserved names that are not existing property names
        self.assertEqual(self.nameCache.getPropertyName(parent, "test"), "test_1")

        # An SdfPrimSpec can also be passed to updatePropertyNames()
        parent.CreateRelationship("baz")
        self.nameCache.updatePropertyNames(self.layer.GetPrimAtPath(parent.GetPath()))
        self.assertEqual(self.nameCache.getPropertyName(parent, "baz"), "baz_1")

        # The update does not clear already reserved names that are not existing property names
        self.assertEqual(self.nameCache.getPropertyName(parent, "test"), "test_2")

    def testUpdatePropertyNamesInvalidParent(self):
        func, args, result, message = self.nameCache.updatePropertyNames, [], None, "Unable to update property names:"
        self.assertInvalidPrimParentArg(func, args, result, message, False)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, False)

    def testUpdate(self):
        # Updates to the stage are not reflected in the reserved names if a path exists in the NameCache
        # The update() function forces the names of existing prims and properties to be added to the reserved names

        # Add path to the NameCache
        parent = self.stage.DefinePrim("/parent")
        self.nameCache.getPrimName(parent, "test")
        self.nameCache.getPropertyName(parent, "test")

        # Defining a prim or property does not stop those names from being returned
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo"))
        parent.CreateRelationship("foo")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo")

        # Defining a prim or property then calling update() does stop those names from being returned
        self.stage.DefinePrim(parent.GetPath().AppendChild("bar"))
        parent.CreateRelationship("bar")
        self.nameCache.update(parent)
        self.assertEqual(self.nameCache.getPrimName(parent, "bar"), "bar_1")
        self.assertEqual(self.nameCache.getPropertyName(parent, "bar"), "bar_1")

        # The update does not clear already reserved names that are not existing property names
        self.assertEqual(self.nameCache.getPrimName(parent, "test"), "test_1")
        self.assertEqual(self.nameCache.getPropertyName(parent, "test"), "test_1")

        # An SdfPrimSpec can also be passed to update()
        self.stage.DefinePrim(parent.GetPath().AppendChild("baz"))
        parent.CreateRelationship("baz")
        self.nameCache.update(self.layer.GetPrimAtPath(parent.GetPath()))
        self.assertEqual(self.nameCache.getPrimName(parent, "baz"), "baz_1")
        self.assertEqual(self.nameCache.getPropertyName(parent, "baz"), "baz_1")

        # The update does not clear already reserved names that are not existing prim or property names
        self.assertEqual(self.nameCache.getPrimName(parent, "test"), "test_2")
        self.assertEqual(self.nameCache.getPropertyName(parent, "test"), "test_2")

    def testUpdateInvalidParent(self):
        func, args, result, message = self.nameCache.update, [], None, "Unable to update prim and property names:"
        self.assertInvalidPrimParentArg(func, args, result, message, True)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, True)

    def testClearPrimNames(self):
        # Updates to the stage are not reflected in the reserved names if a path exists in the NameCache
        # The clearPrimNames() function removes the path from the cache

        # Add path to the NameCache
        parent = self.stage.DefinePrim("/parent")
        self.nameCache.getPrimName(parent, "test")

        # Defining a child does not stop that name from being returned
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo"))
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo")

        # Defining a child then calling clearPrimNames() does stop that name from being returned
        self.stage.DefinePrim(parent.GetPath().AppendChild("bar"))
        self.nameCache.clearPrimNames(parent)
        self.assertEqual(self.nameCache.getPrimName(parent, "bar"), "bar_1")

        # The update clears already reserved names that are not child prim names
        self.assertEqual(self.nameCache.getPrimName(parent, "test"), "test")

        # An SdfPrimSpec can also be passed to clearPrimNames()
        self.stage.DefinePrim(parent.GetPath().AppendChild("baz"))
        self.nameCache.clearPrimNames(self.layer.GetPrimAtPath(parent.GetPath()))
        self.assertEqual(self.nameCache.getPrimName(parent, "baz"), "baz_1")

        # The update clears already reserved names that are not existing prim names
        self.assertEqual(self.nameCache.getPrimName(parent, "test"), "test")

    def testClearPrimNamesInvalidParent(self):
        func, args, result, message = self.nameCache.clearPrimNames, [], None, "Unable to clear prim names:"
        self.assertInvalidPathParentArg(func, args, result, message, True)
        self.assertInvalidPrimParentArg(func, args, result, message, True)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, True)

    def testClearPropertyNames(self):
        # Updates to the stage are not reflected in the reserved names if a path exists in the NameCache
        # The clearPropertyNames() function removes the path from the cache

        # Add path to the NameCache
        parent = self.stage.DefinePrim("/parent")
        self.nameCache.getPropertyName(parent, "test")

        # Defining a property does not stop that name from being returned
        parent.CreateRelationship("foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo")

        # Defining a property then calling updatePrimNames() does stop that name from being returned
        parent.CreateRelationship("bar")
        self.nameCache.clearPropertyNames(parent)
        self.assertEqual(self.nameCache.getPropertyName(parent, "bar"), "bar_1")

        # The update clears already reserved names that are not existing property names
        self.assertEqual(self.nameCache.getPropertyName(parent, "test"), "test")

        # An SdfPrimSpec can also be passed to updatePropertyNames()
        parent.CreateRelationship("baz")
        self.nameCache.clearPropertyNames(self.layer.GetPrimAtPath(parent.GetPath()))
        self.assertEqual(self.nameCache.getPropertyName(parent, "baz"), "baz_1")

        # The update clears already reserved names that are not existing property names
        self.assertEqual(self.nameCache.getPropertyName(parent, "test"), "test")

    def testClearPropertyNamesInvalidParent(self):
        func, args, result, message = self.nameCache.clearPropertyNames, [], None, "Unable to clear property names:"
        self.assertInvalidPathParentArg(func, args, result, message, False)
        self.assertInvalidPrimParentArg(func, args, result, message, False)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, False)

    def testClear(self):
        # Updates to the stage are not reflected in the reserved names if a path exists in the NameCache
        # The clear() function removes the path from the cache

        # Add path to the NameCache
        parent = self.stage.DefinePrim("/parent")
        self.nameCache.getPrimName(parent, "test")
        self.nameCache.getPropertyName(parent, "test")

        # Defining a prim or property does not stop those names from being returned
        self.stage.DefinePrim(parent.GetPath().AppendChild("foo"))
        parent.CreateRelationship("foo")
        self.assertEqual(self.nameCache.getPrimName(parent, "foo"), "foo")
        self.assertEqual(self.nameCache.getPropertyName(parent, "foo"), "foo")

        # Defining a prim or property then calling update() does stop those names from being returned
        self.stage.DefinePrim(parent.GetPath().AppendChild("bar"))
        parent.CreateRelationship("bar")
        self.nameCache.clear(parent)
        self.assertEqual(self.nameCache.getPrimName(parent, "bar"), "bar_1")
        self.assertEqual(self.nameCache.getPropertyName(parent, "bar"), "bar_1")

        # The update does not clear already reserved names that are not existing property names
        self.assertEqual(self.nameCache.getPrimName(parent, "test"), "test")
        self.assertEqual(self.nameCache.getPropertyName(parent, "test"), "test")

        # An SdfPrimSpec can also be passed to update()
        self.stage.DefinePrim(parent.GetPath().AppendChild("baz"))
        parent.CreateRelationship("baz")
        self.nameCache.clear(self.layer.GetPrimAtPath(parent.GetPath()))
        self.assertEqual(self.nameCache.getPrimName(parent, "baz"), "baz_1")
        self.assertEqual(self.nameCache.getPropertyName(parent, "baz"), "baz_1")

        # The update does not clear already reserved names that are not existing prim or property names
        self.assertEqual(self.nameCache.getPrimName(parent, "test"), "test")
        self.assertEqual(self.nameCache.getPropertyName(parent, "test"), "test")

    def testClearInvalidParent(self):
        func, args, result, message = self.nameCache.clear, [], None, "Unable to clear prim and property names:"
        self.assertInvalidPathParentArg(func, args, result, message, True)
        self.assertInvalidPrimParentArg(func, args, result, message, True)
        self.assertInvalidPrimSpecParentArg(func, args, result, message, True)


class DisplayNameTestCase(usdex.test.TestCase):

    def setUp(self):
        super().setUp()

        # Build a layered stage that allows us to change the edit target
        self.weakerLayer = self.tmpLayer(name="Weaker")
        self.strongerLayer = self.tmpLayer(name="Stronger")

        layer = Sdf.Layer.CreateAnonymous()
        layer.subLayerPaths.append(self.strongerLayer.identifier)
        layer.subLayerPaths.append(self.weakerLayer.identifier)

        self.stage = Usd.Stage.Open(layer)
        usdex.core.configureStage(
            self.stage,
            self.defaultPrimName,
            self.defaultUpAxis,
            self.defaultLinearUnits,
            self.defaultAuthoringMetadata,
        )

        # Define the prim in the weaker layer
        self.stage.SetEditTarget(Usd.EditTarget(self.weakerLayer))
        primName = usdex.core.getValidPrimName(self.defaultPrimName)
        self.prim = self.stage.DefinePrim(Sdf.Path.absoluteRootPath.AppendChild(primName))

    def testGetDisplayName(self):
        # The newly created prim will have an empty display name
        self.assertEqual(usdex.core.getDisplayName(self.prim), "")

        weakerValue = "Weaker Display Name"
        self.assertTrue(usdex.core.setDisplayName(self.prim, weakerValue))
        self.assertEqual(usdex.core.getDisplayName(self.prim), weakerValue)

        self.stage.SetEditTarget(Usd.EditTarget(self.strongerLayer))
        strongerValue = "Stronger Display Name"
        self.assertTrue(usdex.core.setDisplayName(self.prim, strongerValue))
        self.assertEqual(usdex.core.getDisplayName(self.prim), strongerValue)

        self.assertIsValidUsd(self.stage)

        # Invalid input is rejected by usdex before any USD metadata API is called.
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, "Unable to get display name from an invalid prim")],
        ):
            self.assertEqual(usdex.core.getDisplayName(Usd.Prim()), "")

    def testSetDisplayName(self):
        # Setting the display name will produce a success result
        weakerValue = "Weaker Display Name"
        self.assertTrue(usdex.core.setDisplayName(self.prim, weakerValue))
        self.assertEqual(usdex.core.getDisplayName(self.prim), weakerValue)

        # Setting a bytes string as the display name will convert it to a string
        rocketEmoji = "🚀"
        rocketBytesString = b"\xf0\x9f\x9a\x80"
        self.assertTrue(usdex.core.setDisplayName(self.prim, rocketBytesString))
        self.assertEqual(usdex.core.getDisplayName(self.prim), rocketEmoji)

        # Setting the corresponding string will produce the same display name
        self.assertTrue(usdex.core.setDisplayName(self.prim, rocketEmoji))
        self.assertEqual(usdex.core.getDisplayName(self.prim), rocketEmoji)

        self.assertIsValidUsd(self.stage)

        # Invalid input is rejected by usdex before any USD metadata API is called.
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, "Unable to set display name on an invalid prim")],
        ):
            self.assertFalse(usdex.core.setDisplayName(Usd.Prim(), "foo"))

    def testClearDisplayName(self):
        weakerValue = "Weaker Display Name"
        self.assertTrue(usdex.core.setDisplayName(self.prim, weakerValue))

        self.stage.SetEditTarget(Usd.EditTarget(self.strongerLayer))
        strongerValue = "Stronger Display Name"
        self.assertTrue(usdex.core.setDisplayName(self.prim, strongerValue))

        # Clearing the display name in the stronger layer will produce a success result
        self.assertTrue(usdex.core.clearDisplayName(self.prim))

        # The weaker value will now be reflected in the get function
        self.assertEqual(usdex.core.getDisplayName(self.prim), weakerValue)

        self.assertIsValidUsd(self.stage)

        # Invalid input is rejected by usdex before any USD metadata API is called.
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, "Unable to clear display name on an invalid prim")],
        ):
            self.assertFalse(usdex.core.clearDisplayName(Usd.Prim()))

    def testBlockDisplayName(self):
        weakerValue = "Weaker Display Name"
        self.assertTrue(usdex.core.setDisplayName(self.prim, weakerValue))

        self.stage.SetEditTarget(Usd.EditTarget(self.strongerLayer))

        # Blocking the display name in the stronger layer will produce a success result
        self.assertTrue(usdex.core.blockDisplayName(self.prim))

        # The prim will now have an empty display name
        self.assertEqual(usdex.core.getDisplayName(self.prim), "")

        self.assertIsValidUsd(self.stage)

        # Invalid input is rejected by usdex before any USD metadata API is called.
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, "Unable to block display name on an invalid prim")],
        ):
            self.assertFalse(usdex.core.blockDisplayName(Usd.Prim()))

    def testComputeEffectiveDisplayName(self):
        # The prim name will be returned when no display name is authored
        self.assertEqual(usdex.core.computeEffectiveDisplayName(self.prim), self.prim.GetName())

        weakerValue = "Weaker Display Name"
        self.assertTrue(usdex.core.setDisplayName(self.prim, weakerValue))
        self.assertEqual(usdex.core.computeEffectiveDisplayName(self.prim), weakerValue)

        self.stage.SetEditTarget(Usd.EditTarget(self.strongerLayer))
        strongerValue = "Stronger Display Name"
        self.assertTrue(usdex.core.setDisplayName(self.prim, strongerValue))
        self.assertEqual(usdex.core.computeEffectiveDisplayName(self.prim), strongerValue)

        self.assertTrue(usdex.core.blockDisplayName(self.prim))
        self.assertEqual(usdex.core.computeEffectiveDisplayName(self.prim), self.prim.GetName())

        self.assertIsValidUsd(self.stage)

        # Invalid input is rejected by usdex before any USD metadata API is called.
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, "Unable to compute effective display name for an invalid prim")],
        ):
            self.assertEqual(usdex.core.computeEffectiveDisplayName(Usd.Prim()), "")
