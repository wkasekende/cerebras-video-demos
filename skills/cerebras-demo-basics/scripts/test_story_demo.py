#!/usr/bin/env python3
"""Check the reference-story timing semantics against the bundled raw fixtures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image

from render_story_demo import ROOT, VIEW_H, VIEW_W, InputError, draw_panels, ffmpeg_binary, load_manifest, phase_at, source_at


class StoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = ffmpeg_binary()
        cls.manifest = ROOT / 'examples' / 'reference-story.json'
        cls.raw = json.loads(cls.manifest.read_text())
        for side in ('left', 'right'):
            cls.raw[side]['video'] = str((cls.manifest.parent / cls.raw[side]['video']).resolve())
        for key in ('background', 'closing_background', 'speedup_background'):
            cls.raw[key] = str((cls.manifest.parent / cls.raw[key]).resolve())

    def load(self, value):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'story.json'
            path.write_text(json.dumps(value))
            return load_manifest(path, self.ffmpeg)

    def test_sample_phases(self):
        m = self.load(copy.deepcopy(self.raw))
        self.assertEqual(m['duration_s'], 28.5)
        self.assertEqual(phase_at(m, 4.6), 'transition')
        self.assertEqual(phase_at(m, 5.3), 'start_hold')
        self.assertEqual(phase_at(m, 5.5), 'comparison')
        self.assertEqual(phase_at(m, 19.5), 'comparison')
        self.assertEqual(phase_at(m, 20.5), 'result_cards')
        self.assertEqual(phase_at(m, 23), 'speedup')
        self.assertEqual(phase_at(m, 25.5), 'logos')

    def test_recording_continues_after_measurement(self):
        m = self.load(copy.deepcopy(self.raw))
        position, speed = source_at(m, 6, 'left')
        self.assertEqual((position, speed), (6, 1))
        self.assertEqual(min(position, m['left']['stop_s']), 4)
        self.assertEqual(m['left']['measurement_output_s'], 4)

    def test_only_waiting_side_accelerates(self):
        m = self.load(copy.deepcopy(self.raw))
        self.assertEqual(source_at(m, 12, 'left'), (11, 0))
        self.assertEqual(source_at(m, 12, 'right'), (15, 4))
        self.assertEqual(source_at(m, 14, 'right'), (20, 0))

    def test_done_fades_in_even_if_source_holds_at_response(self):
        raw = copy.deepcopy(self.raw)
        for scene in raw['scenes'][1:]:
            scene['left'] = {'hold_s': 4}
        m = self.load(raw)
        self.assertEqual(source_at(m, 6, 'left'), (4, 0))
        footage = [Image.new('RGB', (VIEW_W, VIEW_H), 'white') for _ in range(2)]
        before = draw_panels(m, 3.9, footage, self.ffmpeg)
        after = draw_panels(m, 6, footage, self.ffmpeg)
        self.assertNotEqual(before.getpixel((250, 310)), after.getpixel((250, 310)))

    def test_invalid_maps_and_missing_measurement_are_rejected(self):
        cases = {
            'hidden jump': lambda m: m['scenes'][1]['left'].update(from_s=5),
            'hold jumps': lambda m: m['scenes'][3]['left'].update(hold_s=12),
            'missing response': lambda m: m['right'].update(stop_s=21),
            'source too short': lambda m: m['right'].update(start_s=10),
            'unlabeled fixture': lambda m: m.pop('synthetic'),
            'overlong social edit': lambda m: m.update(logos_s=60),
        }
        for name, edit in cases.items():
            with self.subTest(name=name):
                m = copy.deepcopy(self.raw)
                edit(m)
                with self.assertRaises(InputError):
                    self.load(m)


if __name__ == '__main__':
    unittest.main()
