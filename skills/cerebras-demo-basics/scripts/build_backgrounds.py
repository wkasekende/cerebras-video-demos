#!/usr/bin/env python3
"""Build geometric, editable recreations of two quiet demo background styles.

These are newly generated pattern plates inspired by the source guide's visible
styles. They are not original design-tool exports or evidence of design approval.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'backgrounds'
WIDTH, HEIGHT = 3840, 2160
BASE = '#F4F4F1'
ORANGE = '#F15A29'


def rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def blend(color, opacity):
    base, foreground = rgb(BASE), rgb(color)
    return tuple(round(b + (f - b) * opacity) for b, f in zip(base, foreground))


class Plate:
    def __init__(self, description):
        self.image = Image.new('RGB', (WIDTH, HEIGHT), BASE)
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
            '<title>Cerebras demo background style recreation</title>',
            f'<desc>{description} Newly generated geometric artwork; not an original design-tool export or approved design.</desc>',
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BASE}"/>',
        ]

    def dot(self, x, y, radius, color=ORANGE):
        self.draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
        self.svg.append(f'<circle cx="{x:g}" cy="{y:g}" r="{radius:.3f}" fill="{color}"/>')

    def line(self, points, opacity, width=2, color=ORANGE):
        self.draw.line(points, fill=blend(color, opacity), width=width)
        coords = ' '.join(f'{x:.3f},{y:.3f}' for x, y in points)
        self.svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" stroke-opacity="{opacity:.4f}"/>')

    def save(self, stem):
        self.image.save(OUT / f'{stem}.png', optimize=True)
        (OUT / f'{stem}.svg').write_text('\n'.join(self.svg + ['</svg>']) + '\n')


def halftone():
    plate = Plate('Light neutral plate with orange halftone accents at the upper right and lower left; calm unpatterned center.')
    spacing, max_radius = 24, 9.5
    for y in range(0, HEIGHT + spacing, spacing):
        for x in range(0, WIDTH + spacing, spacing):
            upper_right = math.hypot((WIDTH - x) / 1810, y / 1320)
            lower_left = math.hypot(x / 1810, (HEIGHT - y) / 1320)
            strength = max(0, 1 - min(upper_right, lower_left))
            radius = max_radius * strength ** 0.84
            if radius >= 0.75:
                plate.dot(x, y, radius)
    plate.save('light-halftone-recreated')


def grid():
    plate = Plate('Light neutral plate with a fine, subtly bowed orange grid; the grid becomes lighter toward the center.')
    spacing = 48

    def warp(x, y):
        # A small deterministic bow, visible in the reference family but quiet
        # enough that the pattern never competes with recording panels.
        return (x + 5 * math.sin(y / 410) * math.sin(x / 780),
                y + 5 * math.sin(x / 520) * math.sin(y / 610))

    def opacity(x, y):
        normalized = min(1, math.hypot((x - WIDTH / 2) / (WIDTH / 2),
                                      (y - HEIGHT / 2) / (HEIGHT / 2)))
        return 0.055 + 0.105 * normalized ** 1.6

    for x in range(0, WIDTH + spacing, spacing):
        for y in range(0, HEIGHT, spacing):
            plate.line([warp(x, y), warp(x, min(HEIGHT, y + spacing))], opacity(x, y + spacing / 2))
    for y in range(0, HEIGHT + spacing, spacing):
        for x in range(0, WIDTH, spacing):
            plate.line([warp(x, y), warp(min(WIDTH, x + spacing), y)], opacity(x + spacing / 2, y))
    plate.save('light-grid-recreated')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    halftone()
    grid()
    provenance = {
        'status': 'recreated_geometric_assets',
        'original_design_exports': False,
        'design_approval_claimed': False,
        'width': WIDTH,
        'height': HEIGHT,
        'color': ORANGE,
        'base_color': BASE,
        'generator': 'scripts/build_backgrounds.py',
        'assets': [
            {'stem': 'light-halftone-recreated', 'role': 'quiet default', 'formats': ['svg', 'png']},
            {'stem': 'light-grid-recreated', 'role': 'quiet alternative', 'formats': ['svg', 'png']},
        ],
        'notes': 'Newly drawn geometric recreations of a quiet halftone and a fine grid; not original design-tool exports.'
    }
    (OUT / 'recreation-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    for path in sorted(OUT.iterdir()):
        if path.is_file():
            print(f'{path.name}: {path.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
