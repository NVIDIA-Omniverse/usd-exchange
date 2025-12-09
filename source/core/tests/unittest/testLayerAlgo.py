# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import usdex.core
import usdex.test
from pxr import Sdf, Tf


class LayerAlgoTest(usdex.test.TestCase):

    def __expectedAuthoringMetadata(self):
        return {
            "creator": LayerAlgoTest.defaultAuthoringMetadata,
        }

    def testLayerAuthoringMetadata(self):
        layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        self.assertEqual(layer.customLayerData, {})
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))
        usdex.core.setLayerAuthoringMetadata(layer, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        self.assertEqual(layer.customLayerData, self.__expectedAuthoringMetadata())

    def testLayerAuthoringMetadataWithExistingMetadata(self):
        layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        data = {"creator": "foo bar", "baz": "bongo"}
        layer.customLayerData = data
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        usdex.core.setLayerAuthoringMetadata(layer, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        expected = self.__expectedAuthoringMetadata()
        self.assertNotEqual(layer.customLayerData, expected)
        expected["baz"] = "bongo"
        self.assertEqual(layer.customLayerData, expected)

    def testGetLayerAuthoringMetadata(self):
        layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()

        # Test getting metadata from layer with no metadata
        self.assertEqual(layer.customLayerData, {})
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))
        authoringMetadata = usdex.core.getLayerAuthoringMetadata(layer)
        self.assertEqual(authoringMetadata, "")

        # Test getting metadata after setting it
        usdex.core.setLayerAuthoringMetadata(layer, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        authoringMetadata = usdex.core.getLayerAuthoringMetadata(layer)
        self.assertEqual(authoringMetadata, LayerAlgoTest.defaultAuthoringMetadata)

        # Test getting metadata with custom value
        customMetadata = "Custom Authoring Tool v2.1.0"
        usdex.core.setLayerAuthoringMetadata(layer, customMetadata)
        authoringMetadata = usdex.core.getLayerAuthoringMetadata(layer)
        self.assertEqual(authoringMetadata, customMetadata)

        # Test getting metadata with existing custom layer data
        layer.ClearCustomLayerData()
        layer.customLayerData = {"foo": "bar", "creator": "test metadata", "baz": "qux"}
        authoringMetadata = usdex.core.getLayerAuthoringMetadata(layer)
        self.assertEqual(authoringMetadata, "test metadata")

        # Test getting empty string metadata
        usdex.core.setLayerAuthoringMetadata(layer, "")
        authoringMetadata = usdex.core.getLayerAuthoringMetadata(layer)
        self.assertEqual(authoringMetadata, "")

    def testSaveLayer(self):
        layer: Sdf.Layer = self.tmpLayer()
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, f'Saving.* with comment "{self._testMethodName}"')]):
            success = usdex.core.saveLayer(layer, LayerAlgoTest.defaultAuthoringMetadata, comment=self._testMethodName)
        self.assertTrue(success)
        self.assertEqual(layer.comment, self._testMethodName)
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        self.assertEqual(layer.customLayerData, self.__expectedAuthoringMetadata())

        # Test native layer save to make sure the data has been cleared
        # when running on the same layer as before
        layer.ClearCustomLayerData()
        layer.Save()
        self.assertFalse(layer.HasCustomLayerData())  # not added back
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))
        self.assertEqual(layer.comment, self._testMethodName)  # remains in tact

    def testSaveLayerFails(self):
        layer: Sdf.Layer = Sdf.Layer.CreateAnonymous()
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_CODING_ERROR_TYPE, "Cannot save anonymous layer"),
                (Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Saving"),
            ],
        ):
            success = usdex.core.saveLayer(layer, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertFalse(success)

    def testSaveLayerWithoutComments(self):
        layer: Sdf.Layer = self.tmpLayer()

        # default comment is None
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Saving")]):
            success = usdex.core.saveLayer(layer, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertTrue(success)
        self.assertEqual(layer.comment, "")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        self.assertEqual(layer.customLayerData, self.__expectedAuthoringMetadata())

        # explicit comment=None
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Saving")]):
            success = usdex.core.saveLayer(layer, LayerAlgoTest.defaultAuthoringMetadata, comment=None)
        self.assertTrue(success)
        self.assertEqual(layer.comment, "")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        self.assertEqual(layer.customLayerData, self.__expectedAuthoringMetadata())

        # empty comment
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, 'Saving.*with comment ""')]):
            success = usdex.core.saveLayer(layer, LayerAlgoTest.defaultAuthoringMetadata, comment="")
        self.assertTrue(success)
        self.assertEqual(layer.comment, "")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        self.assertEqual(layer.customLayerData, self.__expectedAuthoringMetadata())

    def testSaveLayerWithoutAuthoringMetadata(self):
        layer: Sdf.Layer = self.tmpLayer()

        # default authoringMetadata is None
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Saving")]):
            success = usdex.core.saveLayer(layer)
        self.assertTrue(success)
        self.assertEqual(layer.comment, "")
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))

        # explicit authoringMetadata=None
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Saving")]):
            success = usdex.core.saveLayer(layer, authoringMetadata=None)
        self.assertTrue(success)
        self.assertEqual(layer.comment, "")
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))

        # empty authoringMetadata
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Saving")]):
            success = usdex.core.saveLayer(layer, authoringMetadata="")
        self.assertTrue(success)
        self.assertEqual(layer.comment, "")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        self.assertEqual(layer.customLayerData, {"creator": ""})

    def testSaveLayerWithExistingMetadata(self):
        layer: Sdf.Layer = self.tmpLayer()

        # setting authoringMetadata overrides existing metadata
        layer.customLayerData = {"creator": "foo bar"}
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, f'Saving.*with comment "{self._testMethodName}"')]):
            success = usdex.core.saveLayer(layer, LayerAlgoTest.defaultAuthoringMetadata, comment=self._testMethodName)
        self.assertTrue(success)
        self.assertEqual(layer.comment, self._testMethodName)
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        self.assertEqual(layer.customLayerData, self.__expectedAuthoringMetadata())

        # setting custom metadata does not prevent the automated authoring metadata
        layer.ClearCustomLayerData()
        layer.customLayerData = {"foo": "bar"}
        self.assertFalse(usdex.core.hasLayerAuthoringMetadata(layer))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, f'Saving.*with comment "{self._testMethodName}"')]):
            success = usdex.core.saveLayer(layer, LayerAlgoTest.defaultAuthoringMetadata, comment=self._testMethodName)
        self.assertTrue(success)
        self.assertEqual(layer.comment, self._testMethodName)
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(layer))
        data = self.__expectedAuthoringMetadata()
        data.update({"foo": "bar"})
        self.assertEqual(layer.customLayerData, data)

    def testExportLayerWithIdentifier(self):
        # The identifier is required and must be a valid value otherwise the layer will not be exported
        layer = Sdf.Layer.CreateAnonymous()

        # An invalid value will result in an unsuccessful stage creation
        identifier = ""
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid identifier")]):
            success = usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertFalse(success)

        identifier = self.tmpFile("test", "foo")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid identifier")]):
            success = usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertFalse(success)

        # A valid "usda" value will result in a successful layer export
        identifier = self.tmpFile("test", "usda")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Exporting")]):
            success = usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertTrue(success)
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(usdex.core.getUsdLayerEncoding(exportedLayer), "usda")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(exportedLayer))

        # A valid "usdc" value will result in a successful layer export
        identifier = self.tmpFile("test", "usdc")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Exporting")]):
            success = usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata)
        self.assertTrue(success)
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(usdex.core.getUsdLayerEncoding(exportedLayer), "usdc")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(exportedLayer))

    def testExportLayerWithComment(self):
        # Comment is optional but if specified will override existing comment in the layer
        layer = Sdf.Layer.CreateAnonymous()

        defaultComment = ""
        existingComment = "Existing Comment"
        exportComment = "Export Comment"

        # If there is not existing comment and one is not specified then there will be no comment after export
        # The comment in the source layer should not be changed
        self.assertEqual(layer.comment, defaultComment)
        identifier = self.tmpFile("test", "usda")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Exporting")]):
            self.assertTrue(usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata))
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(layer.comment, defaultComment)
        self.assertEqual(exportedLayer.comment, defaultComment)

        # Set a comment on the layer
        layer.comment = existingComment

        # If there is any existing comment and one is not specified then the existing comment is present after export
        # The comment in the source layer should not be changed
        self.assertEqual(layer.comment, existingComment)
        identifier = self.tmpFile("test", "usda")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Exporting")]):
            self.assertTrue(usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata))
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(layer.comment, existingComment)
        self.assertEqual(exportedLayer.comment, existingComment)

        # If there is any existing comment and one is specified then the export comment is present after export
        # The comment in the source layer should not be changed
        self.assertEqual(layer.comment, existingComment)
        identifier = self.tmpFile("test", "usda")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, f'Exporting.*with comment "{exportComment}"')]):
            self.assertTrue(usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata, comment=exportComment))
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(layer.comment, existingComment)
        self.assertEqual(exportedLayer.comment, exportComment)

        # If there is any existing comment and an explicitly empty one is specified then the empty comment is present after export
        # The comment in the source layer should not be changed
        self.assertEqual(layer.comment, existingComment)
        identifier = self.tmpFile("test", "usda")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, 'Exporting.*with comment ""')]):
            self.assertTrue(usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata, comment=""))
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(layer.comment, existingComment)
        self.assertEqual(exportedLayer.comment, defaultComment)

    def testExportLayerWithFileFormatArgs(self):
        # File format arguments are optional but are respected by the output file format
        layer = Sdf.Layer.CreateAnonymous()

        # A valid "usd" value will result in a successful layer export
        # The default encoding of "usdc" will be used
        identifier = self.tmpFile("test", "usd")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Exporting")]):
            success = usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata, fileFormatArgs={})
        self.assertTrue(success)
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(usdex.core.getUsdLayerEncoding(exportedLayer), "usdc")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(exportedLayer))

        # A valid "usd" value will result in a successful layer export
        # If explicitly set the format will be "usda"
        identifier = self.tmpFile("test", "usd")
        fileFormatArgs = {"format": "usda"}
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Exporting")]):
            success = usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata, fileFormatArgs=fileFormatArgs)
        self.assertTrue(success)
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(usdex.core.getUsdLayerEncoding(exportedLayer), "usda")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(exportedLayer))

        # A valid "usd" value will result in a successful layer export
        # If explicitly set the format will be "usdc"
        identifier = self.tmpFile("test", "usd")
        fileFormatArgs = {"format": "usdc"}
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Exporting")]):
            success = usdex.core.exportLayer(layer, identifier, LayerAlgoTest.defaultAuthoringMetadata, fileFormatArgs=fileFormatArgs)
        self.assertTrue(success)
        exportedLayer = Sdf.Layer.FindOrOpen(identifier)
        self.assertEqual(usdex.core.getUsdLayerEncoding(exportedLayer), "usdc")
        self.assertTrue(usdex.core.hasLayerAuthoringMetadata(exportedLayer))
