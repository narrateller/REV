"""Analytical fixture values below are test data, not REV scenario dimensions."""
import copy
import json
import math
from fractions import Fraction
from pathlib import Path
import unittest

import compare


class ForcePathChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data, bindings, _ = compare.load_inputs()
        cls.params = compare.flatten(data)
        cls.rows = bindings['rows']

    def test_global_transverse_force_and_moment_balance(self):
        # Independent rational free-body benchmark: 10 N at 1/5 m,
        # two guides 1/2 m apart. Required opposing guide pair = +/-4 N.
        f, e, a = Fraction(10), Fraction(1, 5), Fraction(1, 2)
        got = compare.eccentric_transfer(float(f), float(e), float(a))
        self.assertEqual(got['applied_Mz_Nm'], -2)
        self.assertEqual(got['guide_R0_N'], -4)
        self.assertEqual(got['guide_R1_N'], 4)
        self.assertEqual(got['guide_R0_N'] + got['guide_R1_N'], 0)
        self.assertEqual(float(a) * got['guide_R1_N'] + got['applied_Mz_Nm'], 0)

    def test_return_and_opposite_offset_reverse_the_guide_couple(self):
        work = compare.eccentric_transfer(10, .2, .5)
        for other in (compare.eccentric_transfer(-10, .2, .5),
                      compare.eccentric_transfer(10, -.2, .5)):
            for field in work:
                self.assertEqual(work[field], -other[field])

    def test_zero_known_offset_is_distinct_from_unknown_offset(self):
        unknown = compare.eccentric_transfer(10, None, .5)
        self.assertTrue(all(x is None for x in unknown.values()))
        centered = compare.eccentric_transfer(10, 0, .5)
        self.assertTrue(all(x == 0 for x in centered.values()))

    def test_unknown_span_keeps_reactions_unknown_even_for_centered_limit(self):
        got = compare.eccentric_transfer(10, 0, None)
        self.assertEqual(got['applied_Mz_Nm'], 0)
        self.assertIsNone(got['guide_R0_N'])
        self.assertIsNone(got['guide_R1_N'])

    def test_euler_length_and_end_condition_scaling(self):
        # Mathematical fixture; no material/E/I/K/L is assigned to REV.
        p = compare.euler_capacity(2e11, 1e-6, 1, 2)
        self.assertAlmostEqual(p, 50000 * math.pi ** 2)
        self.assertAlmostEqual(compare.euler_capacity(2e11, 1e-6, 1, 4), p / 4)
        self.assertAlmostEqual(compare.euler_capacity(2e11, 1e-6, 2, 2), p / 4)

    def test_unknown_buckling_input_does_not_produce_a_capacity(self):
        for missing in range(4):
            args = [2e11, 1e-6, 1, 2]
            args[missing] = None
            with self.subTest(missing=missing):
                self.assertIsNone(compare.euler_capacity(*args))

    def test_nominal_stress_units_and_sign(self):
        self.assertEqual(compare.nominal_stress(-1000, 1e-4), -1e7)
        self.assertEqual(compare.nominal_stress(1000, 1e-4), 1e7)
        self.assertIsNone(compare.nominal_stress(1000, None))

    def test_invalid_known_inputs_fail_instead_of_becoming_unknown(self):
        for value in (True, '1', float('nan'), float('inf'), -float('inf')):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    compare.eccentric_transfer(value, None, None)
                with self.assertRaises(ValueError):
                    compare.eccentric_transfer(10, value, None)
        for value in (0, -1, True):
            with self.subTest(span=value):
                with self.assertRaises(ValueError):
                    compare.eccentric_transfer(10, None, value)
                with self.assertRaises(ValueError):
                    compare.nominal_stress(10, value)
                with self.assertRaises(ValueError):
                    compare.euler_capacity(None, None, value, None)

    def test_source_44_binding_identity_and_no_argument_mutation(self):
        before = copy.deepcopy(self.rows)
        selected = compare.validate_bindings(self.rows, self.params)
        self.assertEqual(self.rows, before)
        self.assertEqual({k: len(v) for k, v in selected.items()}, {'BASE_A': 22, 'BASE_B': 22})

    def test_missing_duplicate_and_wrong_mode_bindings_rejected(self):
        bad = copy.deepcopy(self.rows)
        bad[0] = copy.deepcopy(bad[1])
        for rows in (self.rows[:-1], bad):
            with self.assertRaises(ValueError):
                compare.validate_bindings(rows, self.params)
        wrong = copy.deepcopy(self.rows)
        wrong[0]['mode'] = 'fixed-times'
        with self.assertRaises(ValueError):
            compare.validate_bindings(wrong, self.params)

    def test_changed_source_value_or_engineering_definition_rejected(self):
        changed = copy.deepcopy(self.rows)
        changed[0]['value'] *= 2
        with self.assertRaises(ValueError):
            compare.validate_bindings(changed, self.params)
        params = copy.deepcopy(self.params)
        params[self.rows[0]['parameter_id']]['meaning'] += ' changed'
        with self.assertRaises(ValueError):
            compare.validate_bindings(self.rows, params)

    def test_dimension_error_rejected_even_if_hash_matches(self):
        rows, params = copy.deepcopy(self.rows), copy.deepcopy(self.params)
        key = rows[0]['parameter_id']
        params[key]['unit'] = 'kg'
        for r in rows:
            if r['parameter_id'] == key:
                r['unit'] = 'kg'
                r['engineering_sha256'] = compare.engineering_sha(params[key])
        with self.assertRaises(ValueError):
            compare.validate_bindings(rows, params)

    def test_no_load_split_and_return_stress_uses_source_return(self):
        selected = compare.validate_bindings(self.rows, self.params)
        for rows in selected.values():
            source = {k: v['value'] for k, v in rows.items()}
            out = compare.coefficients(source)
            self.assertEqual(out['IDEAL_WORK_N']['value'], -source['load.work_peak'])
            self.assertEqual(out['IDEAL_RETURN_N']['value'], source['load.return_required'])
            ratio = out['ROD_RETURN_STRESS']['value'] / -out['ROD_WORK_STRESS']['value']
            self.assertAlmostEqual(ratio, source['load.return_required'] / source['load.work_peak'])

    def test_nominal_stress_invariant_under_load_area_scaling(self):
        selected = compare.validate_bindings(self.rows, self.params)['BASE_A']
        values = {k: v['value'] for k, v in selected.items()}
        scaled = dict(values)
        scaled['load.work_peak'] *= 4
        scaled['cylinder.rod_diameter'] *= 2
        self.assertAlmostEqual(compare.coefficients(values)['ROD_WORK_STRESS']['value'],
                               compare.coefficients(scaled)['ROD_WORK_STRESS']['value'])

    def test_all_four_variants_all_stages_keep_physical_results_unknown(self):
        files = compare.payload()
        rows = json.loads(files[compare.REL + '/state_matrix.json'])
        self.assertEqual(len(rows), 42)
        self.assertEqual({r['variant'] for r in rows}, {'A-V1', 'A-V2', 'B-V1', 'B-V2'})
        for row in rows:
            self.assertIsNone(row['actual_force_N'])
            self.assertIsNone(row['actual_moment_Nm'])
            self.assertEqual(row['reaction_available'], 'UNKNOWN')
        for letter in ('A', 'B'):
            manifest = json.loads(files[f'{compare.REL}/results_{letter}.json'])
            self.assertFalse(manifest['architecture_selected'])
            self.assertIsNone(manifest['actual_results']['buckling_capacity_N'])
            self.assertIsNone(manifest['actual_results']['new_drive_force_N'])


if __name__ == '__main__':
    unittest.main()
