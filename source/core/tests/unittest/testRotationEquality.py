# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import math

import usdex.test
from pxr import Gf


class RotationAlmostEqual(usdex.test.TestCase):

    def testDifferentTypes(self):
        rot = Gf.Rotation()
        rot.SetIdentity()
        quatd = Gf.Quatd()
        quatf = Gf.Quatf()

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(rot, quatd)

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(rot, quatf)

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(quatd, rot)

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(quatd, quatf)

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(quatf, rot)

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(quatf, quatd)

    def testIdentity(self):
        # The default GfRotation constructor leaves the rotation undefined.
        rot = Gf.Rotation()
        rot.SetIdentity()
        quatd = Gf.Quatd()
        quatf = Gf.Quatf()

        self.assertRotationsAlmostEqual(rot, rot)
        self.assertRotationsAlmostEqual(quatd, quatd)
        self.assertRotationsAlmostEqual(quatf, quatf)

    def testAlmostEqual(self):
        rot1 = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 45.0)
        rot2 = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 45.0 + 1e-7)

        quatd1 = Gf.Quatd(30.0, Gf.Vec3d(0.0, 1.0, 0.0))
        quatd2 = Gf.Quatd(30.0 + 1e-10, Gf.Vec3d(0.0, 1.0, 0.0))

        quatf1 = Gf.Quatf(60.0, Gf.Vec3f(0.0, 0.0, 1.0))
        quatf2 = Gf.Quatf(60.0 + 1e-5, Gf.Vec3f(0.0, 0.0, 1.0))

        self.assertRotationsAlmostEqual(rot1, rot2)
        self.assertRotationsAlmostEqual(quatd1, quatd2)
        self.assertRotationsAlmostEqual(quatf1, quatf2, tolerance=1e-4)

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(rot1, rot2, tolerance=1e-8)

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(quatd1, quatd2, tolerance=1e-11)

        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(quatf1, quatf2, tolerance=1e-6)

    def testOppositeSenseQuats(self):
        quatf1 = Gf.Quatf(0.7071068, 0.0, 0.7071068, 0.0)
        quatf2 = Gf.Quatf(-0.7071068, 0.0, -0.7071068, 0.0)
        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(quatf1, quatf2)

    def testRotationAxisTolerance(self):
        base = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 30.0)
        inside = Gf.Rotation(Gf.Vec3d(1.0, 1e-7, 0.0), 30.0)  # within default tolerance 1e-6
        outside = Gf.Rotation(Gf.Vec3d(1.0, 1e-4, 0.0), 30.0)  # outside default tolerance
        self.assertRotationsAlmostEqual(base, inside)
        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(base, outside)

    def testRotationAxisPerturbOutsideTolerance(self):
        base = Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), 10.0)
        perturbed = Gf.Rotation(Gf.Vec3d(1e-5, 1 - 1e-5, 0.0), 10.0)
        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(base, perturbed)

    def testRotationAngleWrapping(self):
        r1 = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 10.0)
        r2 = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 370.0)  # mathematically equivalent but raw angle differs
        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(r1, r2)

    def testQuaternionMultiComponentTolerance(self):
        q1 = Gf.Quatd(1.0000000, Gf.Vec3d(0.0, 0.0, 0.0))
        q2 = Gf.Quatd(1.0000005, Gf.Vec3d(2e-7, -3e-7, 4e-7))  # within tolerance
        self.assertRotationsAlmostEqual(q1, q2)
        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(q1, q2, tolerance=1e-8)

    def testQuaternionNonUnitFails(self):
        q = Gf.Quatd(1.0, Gf.Vec3d(0.0, 0.0, 0.0))
        q_scaled = Gf.Quatd(2.0, Gf.Vec3d(0.0, 0.0, 0.0))
        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(q, q_scaled)

    def testToleranceWideAccepts(self):
        r1 = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), 25.0)
        r2 = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), 25.0 + 1e-4)  # outside default tolerance
        self.assertRotationsAlmostEqual(r1, r2, tolerance=1e-3)
        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(r1, r2)  # default tolerance should fail

    def testQuaternionOppositeSenseWithNoise(self):
        # base quaternion representing rotation of 30 degrees around Y axis
        angle_deg = 30.0
        angle_rad = math.radians(angle_deg)
        axis = Gf.Vec3d(0.0, 1.0, 0.0)
        sin_half = math.sin(angle_rad / 2.0)
        q1 = Gf.Quatd(math.cos(angle_rad / 2.0), axis * sin_half)
        # Negate and add tiny noise
        q2 = Gf.Quatd(-q1.GetReal() + 1e-9, -(q1.GetImaginary()) + Gf.Vec3d(1e-9, -1e-9, 1e-9))
        with self.assertRaises(AssertionError):
            self.assertRotationsAlmostEqual(q1, q2)

    def testValueMismatchMessageContents(self):
        # Angle mismatch message
        r1 = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 10.0)
        r2 = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), 11.0)
        with self.assertRaises(AssertionError) as ctx:
            self.assertRotationsAlmostEqual(r1, r2)
        self.assertIn("Angle mismatch", str(ctx.exception))

        r2 = Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), 10.0)
        with self.assertRaises(AssertionError) as ctx:
            self.assertRotationsAlmostEqual(r1, r2)
        self.assertIn("Axis mismatch", str(ctx.exception))

        r2 = Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), 12.0)
        with self.assertRaises(AssertionError) as ctx:
            self.assertRotationsAlmostEqual(r1, r2)
        self.assertIn("Angle mismatch", str(ctx.exception))
        self.assertIn("Axis mismatch", str(ctx.exception))

        # Quaternion real part mismatch message
        q1 = Gf.Quatd(1.0, Gf.Vec3d(0.0, 0.0, 0.0))
        q2 = Gf.Quatd(1.1, Gf.Vec3d(0.0, 0.0, 0.0))
        with self.assertRaises(AssertionError) as ctx:
            self.assertRotationsAlmostEqual(q1, q2)
        self.assertIn("Real part mismatch", str(ctx.exception))

        q2 = Gf.Quatd(1.0, Gf.Vec3d(1.0, 0.0, 0.0))
        with self.assertRaises(AssertionError) as ctx:
            self.assertRotationsAlmostEqual(q1, q2)
        self.assertIn("Imaginary part mismatch", str(ctx.exception))

        q2 = Gf.Quatd(1.1, Gf.Vec3d(0.0, 1.0, 0.0))
        with self.assertRaises(AssertionError) as ctx:
            self.assertRotationsAlmostEqual(q1, q2)
        self.assertIn("Real part mismatch", str(ctx.exception))
        self.assertIn("Imaginary part mismatch", str(ctx.exception))
