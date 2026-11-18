import math
import unittest

from screening import Sample, buckling, reactions, released, section_properties, stresses


DIMENSIONS = {"chamber_width": 2.0, "chamber_height": 1.0, "rod_diameter": 1.0, "chamber_length": 3.0}
MATERIAL = {"young_modulus_Pa": 210e9, "reference_yield_Pa": 235e6}
ENDS = {"PIN_PIN": 1, "FIXED_FREE": 2}
SECTIONS = section_properties(DIMENSIONS)


class ScreeningChecks(unittest.TestCase):
    def setUp(self):
        self.pose = Sample(0.7, 2.0, 0.5, -0.25, 0.25)

    def test_independent_reaction_and_both_free_body_balances(self):
        model = reactions(120, self.pose, "INDEPENDENT_BENCH_FIXTURE", "A")
        self.assertEqual(model["applied_pair_moment_Nm"], (0, -30, -90))
        self.assertEqual(model["mobile"]["G_plus_N"], (0, 45, -15))
        self.assertEqual(model["frame"]["G_plus_N"], (0, -45, 15))
        self.assertEqual(model["mobile"]["axial_branch_x_N"], -120)
        self.assertEqual(model["frame"]["axial_branch_x_N"], 120)
        for body in ("mobile", "frame"):
            for component in (*model[body]["residual"]["force_N"], *model[body]["residual"]["moment_Nm_at_O"]):
                self.assertAlmostEqual(component, 0)

    def test_force_reversal_and_span_halving(self):
        reversed_load = reactions(-120, self.pose, "CAPTURED_RETENTION_FIXTURE", "A")
        self.assertEqual(reversed_load["mobile"]["G_plus_N"], (0, -45, 15))
        narrower = reactions(120, Sample(0.7, 1.0, 0.5, -0.25, 0.25), "INDEPENDENT_BENCH_FIXTURE", "A")
        self.assertEqual(narrower["mobile"]["G_plus_N"], (0, 90, -30))

    def test_seat_and_lock_are_alternative_axial_paths(self):
        for path, expected in (
            ("B_CLOSED_STOP_SEAT", (120, 0)),
            ("B_CLOSED_LOCK_BACKED_STOP", (0, 120)),
            ("B_OPEN_BENCH_FIXTURE", (0, 0)),
        ):
            with self.subTest(path=path):
                model = reactions(120, self.pose, path, "B")
                allocation = model["B_assumed_frame_path_x_N"]
                self.assertEqual((allocation["direct_seat"], allocation["lock_backed_stop"]), expected)
                self.assertIsNone(allocation["actual_split"])

    def test_carrier_corner_superposition_and_rod_axial_only(self):
        model = stresses(-120, -30, -90, DIMENSIONS, SECTIONS, MATERIAL["reference_yield_Pa"])
        self.assertAlmostEqual(model["rod"]["axial_stress_Pa"], -480 / math.pi)
        for corner, expected in {"-Y,-Z": -105, "-Y,+Z": -285, "+Y,-Z": 165, "+Y,+Z": -15}.items():
            self.assertAlmostEqual(model["carrier"]["corner_stress_Pa"][corner], expected)
        self.assertEqual(model["carrier"]["critical_corner"], "-Y,+Z")
        self.assertAlmostEqual(model["carrier"]["max_abs_stress_Pa"], 285)

    def test_euler_does_not_turn_tension_or_zero_into_compression(self):
        for force, reason in [(120, "TENSION"), (0, "ZERO_AXIAL_LOAD")]:
            result = buckling(force, 0, DIMENSIONS, SECTIONS, MATERIAL, ENDS)
            self.assertEqual(result["status"], "NOT_APPLICABLE")
            self.assertEqual(result["reason"], reason)
            self.assertFalse(result["comparisons"])

    def test_euler_plane_end_condition_and_elastic_limit(self):
        short = buckling(-120, 0, DIMENSIONS, SECTIONS, MATERIAL, ENDS)["comparisons"]
        long = buckling(-120, 100, DIMENSIONS, SECTIONS, MATERIAL, ENDS)["comparisons"]
        y_axis = short["carrier/y"]["PIN_PIN"]
        z_axis = short["carrier/z"]["PIN_PIN"]
        self.assertAlmostEqual(z_axis["euler_force_N"] / y_axis["euler_force_N"], 4)
        self.assertAlmostEqual(short["carrier/y"]["FIXED_FREE"]["euler_force_N"] / y_axis["euler_force_N"], 0.25)
        self.assertEqual(y_axis["elastic_check"], "EULER_STRESS_AT_OR_ABOVE_REFERENCE_YIELD")
        self.assertEqual(long["carrier/y"]["PIN_PIN"]["elastic_check"], "ELASTIC_COMPARISON_ONLY")

    def test_released_load_does_not_generate_support_response(self):
        for force in [-120, 120]:
            result = released(force)
            self.assertEqual(result["status"], "NO_STATIC_EQUILIBRIUM")
            self.assertEqual(result["section_4"]["unbalanced_mobile_axial_force_N"], force)
            self.assertIsNone(result["section_4"]["equilibrium_reactions"])
            self.assertEqual(result["section_5"]["status"], "NOT_RUN")
            self.assertEqual(result["section_6"]["status"], "NOT_RUN")
        with self.assertRaises(ValueError):
            released(0)
