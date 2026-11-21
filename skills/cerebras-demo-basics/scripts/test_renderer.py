#!/usr/bin/env python3
"""Check timing and input-validation invariants against the shipped local fixture."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from render_demo import ROOT, InputError, draw_completion_card, elapsed_at, ffmpeg_binary, font, load_manifest, phase_at, recorded_progress, time_label


class TimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = ffmpeg_binary()
        cls.example = ROOT / 'examples' / 'synthetic-demo.json'
        cls.raw = json.loads(cls.example.read_text())
        for side in ('left', 'right'):
            cls.raw[side]['video'] = str(cls.example.parent / cls.raw[side]['video'])
        cls.raw['background']['image'] = str((cls.example.parent / cls.raw['background']['image']).resolve())
        cls.raw['outro']['image'] = str((cls.example.parent / cls.raw['outro']['image']).resolve())

    def load(self, manifest):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'test.json'
            path.write_text(json.dumps(manifest))
            return load_manifest(path, self.ffmpeg)

    def test_common_time_map_and_duration(self):
        m = self.load(copy.deepcopy(self.raw))
        self.assertEqual(m['duration_s'], 18.5)
        self.assertEqual(elapsed_at(m, 4), (4, 3))
        self.assertEqual(elapsed_at(m, 5), (7, 3))
        self.assertEqual(elapsed_at(m, 6), (10, 1))
        self.assertEqual(elapsed_at(m, 7), (11, 1))
        self.assertEqual(elapsed_at(m, 9), (12, 1))

    def test_tenths_carry_to_minutes(self):
        self.assertEqual(time_label(25), '0m25.0s')
        self.assertEqual(time_label(59.96), '1m00.0s')
        self.assertEqual(time_label(193.1), '3m13.1s')

    def test_other_side_can_finish_first(self):
        m = copy.deepcopy(self.raw)
        m['left']['video'], m['right']['video'] = m['right']['video'], m['left']['video']
        m['left']['completion_s'], m['right']['completion_s'] = 12, 4
        self.assertEqual(self.load(m)['duration_s'], 18.5)

    def test_done_card_has_its_own_phase(self):
        m = self.load(copy.deepcopy(self.raw))
        self.assertEqual(phase_at(m, 11.99), 'comparison')
        self.assertEqual(phase_at(m, 12), 'completion_card')
        self.assertEqual(phase_at(m, 14.49), 'completion_card')
        self.assertEqual(phase_at(m, 14.5), 'outro')
        self.assertNotIn('partner_logo', m['completion_card'])
        raw = copy.deepcopy(self.raw)
        raw['completion_card']['enabled'] = False
        self.assertEqual(self.load(raw)['duration_s'], 16)

    def test_fonts_are_the_bundled_design_faces(self):
        for filename, family in [
            ('manrope-800.ttf', 'Manrope'),
            ('manrope-700.ttf', 'Manrope'),
            ('sometype-mono-600.ttf', 'Sometype Mono'),
            ('sometype-mono-700.ttf', 'Sometype Mono'),
            ('instrument-sans-latin.woff2', 'Instrument Sans'),
        ]:
            self.assertEqual(font(filename, 24).getname()[0], family)

    def test_partner_asset_replaces_placeholder(self):
        raw = copy.deepcopy(self.raw)
        raw['completion_card']['partner_logo'] = str(ROOT / 'assets' / 'cerebras-logo.png')
        raw['completion_card']['partner_name'] = 'Renderer test fixture'
        m = self.load(raw)
        frame = draw_completion_card(m)
        self.assertEqual(frame.size, (1280, 720))
        # The optional-asset branch has real image content where the blank
        # placeholder's neutral fill would otherwise be, without resizing the canvas.
        self.assertNotEqual(frame.getpixel((876, 478)), frame.getpixel((750, 430)))

    def test_recorded_progress_stops_at_completion(self):
        self.assertEqual(recorded_progress(0, 12), 0)
        self.assertEqual(recorded_progress(3, 12), 0.25)
        self.assertEqual(recorded_progress(12, 12), 1)
        self.assertEqual(recorded_progress(20, 12), 1)
        self.assertEqual(recorded_progress(-1, 12), 0)

    def test_supplied_outro_keeps_a_clean_brand_hold(self):
        m = copy.deepcopy(self.raw)
        m['outro']['summary_s'] = 3.5
        with self.assertRaises(InputError):
            self.load(m)

    def test_different_models_need_correct_scope(self):
        m = copy.deepcopy(self.raw)
        m['right']['model'] = 'A different model'
        with self.assertRaises(InputError):
            self.load(m)
        m['comparison_kind'] = 'different_models_workflow'
        self.assertEqual(self.load(m)['comparison_kind'], 'different_models_workflow')

    def test_invalid_inputs_are_rejected(self):
        changes = {
            'hidden gap': lambda m: m['timeline'][1].update(from_s=4.5),
            'source ends early': lambda m: m['right'].update(completion_s=20),
            'missing throughput evidence': lambda m: m.update(outro={'metric': 'measured_throughput', 'tokens_per_second': 750}),
            'sixty seconds or longer': lambda m: m.update(outro_s=60),
            'unreadable opening': lambda m: m.update(display_prompt='word ' * 50),
            'invalid crop': lambda m: m['left'].update(crop=[0, 0, 99999, 10]),
            'nonfinite time': lambda m: m['left'].update(completion_s=float('nan')),
            'missing fixture classification': lambda m: m.pop('synthetic'),
            'missing background': lambda m: m['background'].update(image='/nonexistent/background.png'),
            'missing outro art': lambda m: m['outro'].update(image='/nonexistent/outro.png'),
            'missing partner asset': lambda m: m['completion_card'].update(partner_logo='/nonexistent/logo.png'),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                m = copy.deepcopy(self.raw)
                change(m)
                with self.assertRaises(InputError):
                    self.load(m)


if __name__ == '__main__':
    unittest.main()
