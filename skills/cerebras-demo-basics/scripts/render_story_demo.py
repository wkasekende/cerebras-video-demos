#!/usr/bin/env python3
"""Render the observed prompt → live SBS → result → claim → partner-logo story."""
from __future__ import annotations

import argparse
from functools import lru_cache
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont, ImageOps

from render_demo import ROOT, InputError, ffmpeg_binary, font, number, probe, resolve_plate, string, text_block

W, H, FPS = 1280, 720, 24
VIEW_W, VIEW_H = 586, 582
CARD_X = (22, 648)
CARD_TOP, CARD_BOTTOM, CARD_W = 16, 685, 610
VIEW_Y = 80
ORANGE, INK, GRAY = '#F15A29', '#252525', '#555650'
LIGHT, LINE = '#F5F5F0', '#E7E7E2'
POWERED_FONT = 'manrope-500.ttf'
POWERED_COLOR = '#EBE4DB'
POWERED_TRACKING_EM = -0.065


def _local_file(value, manifest, label):
    path = Path(string(value, label)).expanduser()
    if not path.is_absolute():
        path = manifest.parent / path
    path = path.resolve()
    if not path.is_file():
        raise InputError(f'{label} does not exist: {path}')
    return path


def load_manifest(path, ffmpeg):
    try:
        m = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise InputError(f'Cannot read manifest: {error}')
    if not isinstance(m, dict) or m.get('schema_version') != 1 or m.get('layout') != 'reference_story':
        raise InputError('This renderer requires schema_version=1 and layout=reference_story.')
    if type(m.get('synthetic')) is not bool:
        raise InputError('Set synthetic explicitly for test footage versus real recordings.')
    for key in ('title', 'display_prompt', 'full_prompt', 'disclosure', 'measurement_label'):
        m[key] = string(m.get(key), key)
    if len(m['disclosure']) > 110:
        raise InputError('Keep this single-line disclosure under 110 characters or adapt the layout.')
    for key, default, minimum in (
        ('opening_s', 4.5, 1), ('transition_s', 0.75, 0.2), ('start_hold_s', 0.25, 0),
        ('result_cards_s', 2.5, 1), ('speedup_card_s', 2.5, 1), ('logos_s', 3, 1),
    ):
        m[key] = number(m.get(key, default), key, minimum)
    for key in ('background', 'closing_background'):
        m[key] = resolve_plate(m.get(key), path, key)
    if m.get('speedup_background') is not None:
        m['speedup_background'] = resolve_plate(m['speedup_background'], path, 'speedup_background')
    for side in ('left', 'right'):
        panel = m.get(side)
        if not isinstance(panel, dict):
            raise InputError(f'{side} must be a recording object.')
        for key in ('title', 'label', 'timing_evidence', 'result_note'):
            panel[key] = string(panel.get(key), f'{side}.{key}')
        panel['video'] = str(_local_file(panel.get('video'), path, f'{side}.video'))
        panel['start_s'] = number(panel.get('start_s'), f'{side}.start_s')
        panel['stop_s'] = number(panel.get('stop_s'), f'{side}.stop_s', 1 / FPS)
        panel['source_info'] = probe(ffmpeg, panel['video'])
        if panel.get('crop') is not None:
            crop = panel['crop']
            if not isinstance(crop, list) or len(crop) != 4 or any(type(v) is not int for v in crop):
                raise InputError(f'{side}.crop must be [x,y,width,height] source pixels.')
            x, y, width, height = crop
            if min(x, y) < 0 or min(width, height) <= 0 or x + width > panel['source_info']['width'] or y + height > panel['source_info']['height']:
                raise InputError(f'{side}.crop exceeds the source recording.')
    if not isinstance(m.get('scenes'), list) or not m['scenes']:
        raise InputError('Supply explicit scenes with a duration and per-side source maps.')
    cursors = {'left': 0.0, 'right': 0.0}
    output_s = 0.0
    for i, scene in enumerate(m['scenes']):
        if not isinstance(scene, dict):
            raise InputError(f'scenes[{i}] must be an object.')
        scene['label'] = string(scene.get('label'), f'scenes[{i}].label')
        scene['duration_s'] = number(scene.get('duration_s'), f'scenes[{i}].duration_s', 1 / FPS)
        scene['output_from_s'] = output_s
        output_s += scene['duration_s']
        scene['output_to_s'] = output_s
        for side in ('left', 'right'):
            mapping = scene.get(side)
            if not isinstance(mapping, dict):
                raise InputError(f'scenes[{i}].{side} must be a source map.')
            if 'hold_s' in mapping:
                hold = number(mapping['hold_s'], f'scenes[{i}].{side}.hold_s')
                if 'from_s' in mapping or 'to_s' in mapping or abs(hold - cursors[side]) > 1e-6:
                    raise InputError('A hold must match the preceding source position and have no from/to keys.')
                mapping['hold_s'], mapping['speed'] = hold, 0.0
            else:
                start = number(mapping.get('from_s'), f'scenes[{i}].{side}.from_s')
                end = number(mapping.get('to_s'), f'scenes[{i}].{side}.to_s')
                if abs(start - cursors[side]) > 1e-6 or end <= start:
                    raise InputError('Source maps must begin at zero and remain contiguous and increasing. Use hold_s to pause.')
                mapping.update(from_s=start, to_s=end, speed=(end - start) / scene['duration_s'])
                cursors[side] = end
    for side in ('left', 'right'):
        panel = m[side]
        panel['max_source_s'] = cursors[side]
        if cursors[side] + 1e-6 < panel['stop_s']:
            raise InputError(f'{side} never reaches the verified measurement stop.')
        if panel['start_s'] + cursors[side] > panel['source_info']['duration_s'] - 1 / FPS + 1e-6:
            raise InputError(f'{side} recording ends before the final requested showcase/source position.')
        panel['measurement_output_s'] = measurement_output_time(m, side)
    m['partner_name'] = string(m.get('partner_name', 'PARTNER LOGO'), 'partner_name')
    if m.get('partner_logo') is not None:
        logo_path = _local_file(m['partner_logo'], path, 'partner_logo')
        try:
            with Image.open(logo_path) as logo:
                if logo.format not in ('PNG', 'JPEG'):
                    raise InputError('partner_logo requires PNG/JPEG; rasterize a vector master first.')
                logo.verify()
        except OSError as error:
            raise InputError(f'Cannot read partner_logo: {error}')
        m['partner_logo'] = str(logo_path)
    m['comparison_s'] = output_s
    m['comparison_start_s'] = m['opening_s'] + m['transition_s'] + m['start_hold_s']
    m['result_start_s'] = m['comparison_start_s'] + output_s
    m['speedup_start_s'] = m['result_start_s'] + m['result_cards_s']
    m['logos_start_s'] = m['speedup_start_s'] + m['speedup_card_s']
    m['duration_s'] = m['logos_start_s'] + m['logos_s']
    if m['duration_s'] >= 60:
        raise InputError(f'This edit is {m["duration_s"]:.2f}s. Keep this short-form edit under 60s explicitly.')
    return m


def measurement_output_time(m, side):
    stop = m[side]['stop_s']
    for scene in m['scenes']:
        mapping = scene[side]
        if 'from_s' in mapping and mapping['from_s'] <= stop <= mapping['to_s']:
            return scene['output_from_s'] + (stop - mapping['from_s']) / mapping['speed']
    raise InputError(f'{side} measurement stop is not reached by a playing source segment.')


def source_at(m, comparison_t, side):
    """Return source elapsed time and playback multiplier for one independent panel."""
    if comparison_t >= m['comparison_s']:
        return m[side]['max_source_s'], 0.0
    comparison_t = max(0.0, comparison_t)
    for scene in m['scenes']:
        if comparison_t < scene['output_to_s']:
            mapping = scene[side]
            if 'hold_s' in mapping:
                return mapping['hold_s'], 0.0
            return mapping['from_s'] + (comparison_t - scene['output_from_s']) * mapping['speed'], mapping['speed']
    raise AssertionError('Unmapped comparison time')


def scene_at(m, comparison_t):
    for scene in m['scenes']:
        if comparison_t < scene['output_to_s']:
            return scene['label']
    return m['scenes'][-1]['label']


def phase_at(m, t):
    if t < m['opening_s']:
        return 'composer'
    if t < m['opening_s'] + m['transition_s']:
        return 'transition'
    if t < m['comparison_start_s']:
        return 'start_hold'
    if t < m['result_start_s']:
        return 'comparison'
    if t < m['speedup_start_s']:
        return 'result_cards'
    if t < m['logos_start_s']:
        return 'speedup'
    return 'logos'


def ease(value):
    value = min(1.0, max(0.0, value))
    return 1 - (1 - value) ** 3


@lru_cache(maxsize=8)
def plate(path):
    with Image.open(path) as image:
        return ImageOps.fit(image.convert('RGB'), (W, H), method=Image.Resampling.LANCZOS)


@lru_cache(maxsize=8)
def logo(path, width, height):
    with Image.open(path) as image:
        return ImageOps.contain(image.convert('RGBA'), (width, height), method=Image.Resampling.LANCZOS)


def footer(canvas, m, dark=False, family='manrope-600.ttf', color=None):
    if not dark:
        # During the card-rise transition, the footer can briefly overlap a white
        # recording. A small translucent backing keeps the fixture label legible.
        backing = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(backing)
        width = min(1232, bd.textlength(m['disclosure'], font=font(family, 15)) + 24)
        bd.rounded_rectangle(((W - width) / 2, 692, (W + width) / 2, 719), radius=6, fill=(20, 20, 15, 108))
        canvas.alpha_composite(backing)
    d = ImageDraw.Draw(canvas)
    # The sample disclosure is intentionally concise; recording space stays dominant.
    text_block(d, m['disclosure'], (24, 696), 1232, 15, 1, color or (INK if dark else 'white'),
               family=family, center=True, min_size=12)


def powered_headline(draw, text):
    """Match the supplied artwork's lighter, tightly tracked warm lettering."""
    for size in range(64, 35, -1):
        face = font(POWERED_FONT, size)
        tracking = size * POWERED_TRACKING_EM
        width = face.getlength(text) + tracking * (len(text) - 1)
        if width <= 1080:
            break
    else:
        raise InputError('Shorten the speedup headline to fit its supplied-artwork frame.')
    x = (W - width) / 2
    baseline = 206 - face.getbbox(text, anchor='ls')[1]
    for index, glyph in enumerate(text):
        offset = face.getlength(text[:index + 1]) - face.getlength(glyph) + tracking * index
        draw.text((x + offset, baseline), glyph, font=face, fill=POWERED_COLOR, anchor='ls')


def composer(m, progress=1.0):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((80, 268, 1200, 484), radius=34, fill='#FEFEFE')
    d.line((111, 366, 137, 366), fill=INK, width=3)
    d.line((124, 353, 124, 379), fill=INK, width=3)
    count = max(1, math.ceil(len(m['display_prompt']) * min(1, progress)))
    copy = m['display_prompt'][:count] + ('|' if count < len(m['display_prompt']) else '')
    text_block(d, copy, (168, 297), 900, 26, 4, INK, family='instrument-sans-latin.woff2', min_size=20)
    # Simple vector input controls, avoiding a new icon dependency.
    d.rounded_rectangle((1097, 349, 1107, 368), radius=5, outline=INK, width=2)
    d.arc((1091, 352, 1113, 376), 0, 180, fill=INK, width=2)
    d.line((1102, 376, 1102, 382), fill=INK, width=2)
    d.ellipse((1134, 344, 1178, 388), fill='#E2EEF9')
    d.line((1156, 375, 1156, 356), fill=INK, width=2)
    d.line((1148, 364, 1156, 356, 1164, 364), fill=INK, width=2)
    return layer


def filters_for(panel):
    filters = []
    if panel.get('crop'):
        x, y, width, height = panel['crop']
        filters.append(f'crop={width}:{height}:{x}:{y}')
    return filters + [f'scale={VIEW_W}:{VIEW_H}:force_original_aspect_ratio=decrease',
                      f'pad={VIEW_W}:{VIEW_H}:(ow-iw)/2:(oh-ih)/2:color=0xF8F9F7', 'setsar=1']


def decode_frame(ffmpeg, panel, source_s):
    cmd = [ffmpeg, '-v', 'error', '-ss', f'{panel["start_s"] + source_s:.8f}', '-i', panel['video'],
           '-frames:v', '1', '-vf', ','.join(filters_for(panel)), '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode or len(result.stdout) != VIEW_W * VIEW_H * 3:
        raise InputError(f'Cannot decode {Path(panel["video"]).name} at source elapsed {source_s:.3f}s.')
    return Image.frombytes('RGB', (VIEW_W, VIEW_H), result.stdout)


def _read_exact(stream, size):
    data = bytearray()
    while len(data) < size:
        part = stream.read(size - len(data))
        if not part:
            break
        data.extend(part)
    return bytes(data)


def normalize_side(ffmpeg, m, side, path):
    panel = m[side]
    cmd = [ffmpeg, '-v', 'error', '-ss', str(panel['start_s']), '-i', panel['video'],
           '-t', str(panel['max_source_s'] + 2 / FPS), '-vf', ','.join([f'fps={FPS}'] + filters_for(panel)),
           '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']
    # Only comparison frames are materialized. Output cards never request source data.
    with tempfile.TemporaryFile() as error, open(path, 'wb') as destination:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=error)
        index, current = -1, None
        try:
            for i in range(math.ceil(m['comparison_s'] * FPS) + 1):
                position, _ = source_at(m, min(i / FPS, m['comparison_s']), side)
                wanted = int(math.floor(position * FPS + 1e-6))
                while index < wanted:
                    current = _read_exact(proc.stdout, VIEW_W * VIEW_H * 3)
                    if len(current) != VIEW_W * VIEW_H * 3:
                        raise InputError(f'{side} footage ended before its final requested frame.')
                    index += 1
                destination.write(current)
        finally:
            proc.stdout.close()
            proc.terminate()
            proc.wait()


def draw_panels(m, comparison_t, sources, ffmpeg, results=False):
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for index, side in enumerate(('left', 'right')):
        panel, x = m[side], CARD_X[index]
        position, speed = source_at(m, comparison_t, side)
        clock = min(position, panel['stop_s'])
        done = position + 1e-7 >= panel['stop_s']
        accent = ORANGE if side == 'left' else GRAY
        d.rounded_rectangle((x, CARD_TOP, x + CARD_W, CARD_BOTTOM), radius=17, fill='#FEFEFE')
        title_x = x + 16
        if side == 'left':
            mark = logo(str(ROOT / 'assets' / 'cerebras-logo.png'), 19, 19)
            layer.paste(mark, (x + 16, 28), mark)
            title_x += 28
        text_block(d, panel['title'], (title_x, 25), x + 470 - title_x, 21, 1, INK, min_size=16)
        text_block(d, m['title'], (title_x, 52), x + 470 - title_x, 12, 1, GRAY, family='manrope-600.ttf', min_size=11)
        d.rounded_rectangle((x + 486, 29, x + 591, 56), radius=13,
                            fill='#FFF0E8' if side == 'left' else '#F0F2EB')
        text_block(d, f'{clock:.1f} SEC', (x + 493, 34), 91, 13, 1, accent,
                   family='sometype-mono-600.ttf', center=True, min_size=11)
        d.line((x + 1, 72, x + CARD_W - 1, 72), fill=LINE, width=1)
        recording = sources[index] if sources is not None else decode_frame(ffmpeg, panel, position)
        mask = Image.new('L', (VIEW_W, VIEW_H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, VIEW_W, VIEW_H), radius=9, fill=255)
        layer.paste(recording, (x + 12, VIEW_Y), mask)
        d.rounded_rectangle((x + 22, 672, x + 588, 677), radius=2, fill='#EBDAD1' if side == 'left' else '#E5E6E0')
        fraction = min(1, clock / panel['stop_s'])
        if fraction:
            d.rounded_rectangle((x + 22, 672, x + 22 + round(566 * fraction), 677), radius=2, fill=accent)
        if side == 'left' and done and not results:
            badge = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            bd = ImageDraw.Draw(badge)
            alpha = min(1, max(0, (comparison_t - panel['measurement_output_s']) / 0.25))
            bd.rounded_rectangle((x + 207, 297, x + 403, 404), radius=15, fill=(163, 84, 62, round(190 * alpha)))
            text_block(bd, 'DONE', (x + 214, 321), 182, 47, 1, (255, 255, 255, round(255 * alpha)),
                       family='manrope-800.ttf', center=True, min_size=40)
            layer = Image.alpha_composite(layer, badge)
            d = ImageDraw.Draw(layer)
        if speed > 1.01 and not done and not results:
            # Keep the actual multiplier continuously legible, rather than only blinking.
            d.rounded_rectangle((x + 232, 322, x + 378, 418), radius=14, fill='#111714')
            text_block(d, f'{speed:g}×', (x + 240, 337), 130, 49, 1, 'white',
                       family='sometype-mono-700.ttf', center=True, min_size=32)
        if results:
            shade = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shade)
            sd.rounded_rectangle((x, CARD_TOP, x + CARD_W, CARD_BOTTOM), radius=17, fill=(50, 55, 49, 69))
            layer = Image.alpha_composite(layer, shade)
            d = ImageDraw.Draw(layer)
            d.rounded_rectangle((x + 161, 302, x + 449, 451), radius=18,
                                fill='#FFE1D4' if side == 'left' else '#F2F4EC')
            text_block(d, panel['label'], (x + 179, 320), 252, 19, 1, accent, center=True)
            text_block(d, f'{panel["stop_s"]:.1f}', (x + 179, 347), 252, 48, 1, accent,
                       family='sometype-mono-700.ttf', center=True)
            text_block(d, f'SEC · {m["measurement_label"]}', (x + 179, 412), 252, 12, 1, accent,
                       family='sometype-mono-600.ttf', center=True, min_size=10)
    return layer


def closing(m, phase, t):
    powered_page = phase == 'speedup' and bool(m.get('speedup_background'))
    background = m['speedup_background'] if powered_page else m['closing_background']
    canvas = plate(background).copy().convert('RGBA')
    d = ImageDraw.Draw(canvas)
    if phase == 'speedup':
        ratio = m['right']['stop_s'] / m['left']['stop_s']
        copy = f'{ratio:.1f}× faster to first response' if ratio > 1 and m['measurement_label'].casefold() == 'first response' else f'{m["left"]["stop_s"]:.1f}s vs {m["right"]["stop_s"]:.1f}s'
        if powered_page:
            powered_headline(d, copy)
        else:
            text_block(d, copy, (100, 310), 1080, 54, 2, INK, family='manrope-700.ttf', center=True, min_size=36)
    else:
        reveal = ease((t - m['logos_start_s']) / 0.65)
        wordmark = logo(str(ROOT / 'assets' / 'cerebras-wordmark-rendered.png'), 330, 150)
        x = round(280 + 25 * (1 - reveal))
        canvas.paste(wordmark, (x, 277), wordmark)
        d.line((640, 280, 640, 425), fill='#C8C9C3', width=1)
        if m.get('partner_logo'):
            partner = logo(m['partner_logo'], 330, 130)
            canvas.paste(partner, (round(702 - 25 * (1 - reveal)) + (330 - partner.width) // 2, 287 + (130 - partner.height) // 2), partner)
        else:
            x = round(710 - 25 * (1 - reveal))
            d.rounded_rectangle((x, 302, x + 314, 402), radius=12, fill='#F1F1EB', outline='#B7B9B0', width=2)
            text_block(d, m['partner_name'], (x + 16, 328), 282, 24, 1, GRAY, center=True, min_size=18)
            text_block(d, 'Template placeholder', (x + 16, 367), 282, 13, 1, GRAY, family='manrope-600.ttf', center=True, min_size=12)
        if reveal < 1:
            cover = plate(m['closing_background']).convert('RGBA')
            cover.putalpha(round(255 * (1 - reveal)))
            canvas = Image.alpha_composite(canvas, cover)
    footer(canvas, m, dark=not powered_page, family=POWERED_FONT if powered_page else 'manrope-600.ttf',
           color=POWERED_COLOR if powered_page else None)
    return canvas.convert('RGB')


def draw_frame(m, t, sources=None, ffmpeg=None):
    phase = phase_at(m, t)
    if phase in ('speedup', 'logos'):
        closing_frame = closing(m, phase, t)
        if phase == 'speedup' and t < m['speedup_start_s'] + 0.4:
            prior = plate(m['background']).copy().convert('RGBA')
            prior = Image.alpha_composite(prior, draw_panels(m, m['comparison_s'], sources, ffmpeg, results=True))
            footer(prior, m)
            return Image.blend(prior.convert('RGB'), closing_frame, ease((t - m['speedup_start_s']) / 0.4))
        return closing_frame
    canvas = plate(m['background']).copy().convert('RGBA')
    if phase == 'composer':
        progress = min(1, max(1 / len(m['display_prompt']), t / (m['opening_s'] * 0.82)))
        canvas = Image.alpha_composite(canvas, composer(m, progress))
    elif phase == 'transition':
        progress = ease((t - m['opening_s']) / m['transition_s'])
        panels = draw_panels(m, 0, sources, ffmpeg)
        canvas.alpha_composite(panels, (0, round(730 * (1 - progress))))
        prompt = composer(m)
        prompt = prompt.rotate(-3 * progress, resample=Image.Resampling.BICUBIC)
        factor = 1 - 0.13 * progress
        prompt = prompt.resize((round(W * factor), round(H * factor)), Image.Resampling.LANCZOS)
        prompt.putalpha(prompt.getchannel('A').point(lambda value: round(value * (1 - progress))))
        canvas.alpha_composite(prompt, (round((W - prompt.width) / 2), round(-150 * progress)))
    else:
        comparison_t = min(m['comparison_s'], max(0, t - m['comparison_start_s']))
        panels = draw_panels(m, comparison_t, sources, ffmpeg, results=(phase == 'result_cards'))
        if phase == 'result_cards' and t < m['result_start_s'] + 0.25:
            prior = draw_panels(m, comparison_t, sources, ffmpeg, results=False)
            panels = Image.blend(prior, panels, ease((t - m['result_start_s']) / 0.25))
        canvas = Image.alpha_composite(canvas, panels)
    footer(canvas, m)
    return canvas.convert('RGB')


def preview_times(m):
    values = [('01-composer', m['opening_s'] * 0.78), ('02-panel-frame', m['comparison_start_s']),
              ('03-both-working', m['comparison_start_s'] + min(2, m['comparison_s'] / 4))]
    for i, scene in enumerate(m['scenes']):
        values.append((f'04-scene-{i + 1:02d}', m['comparison_start_s'] + (scene['output_from_s'] + scene['output_to_s']) / 2))
    values += [('05-measured-results', m['result_start_s'] + m['result_cards_s'] / 2),
               ('06-speedup', m['speedup_start_s'] + m['speedup_card_s'] / 2),
               ('07-partner-logos', m['logos_start_s'] + m['logos_s'] / 2)]
    return values


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        ffmpeg = ffmpeg_binary()
        m = load_manifest(args.manifest.resolve(), ffmpeg)
        out = args.output.resolve()
        out.mkdir(parents=True, exist_ok=True)
        (out / 'manifest.resolved.json').write_text(json.dumps(m, indent=2) + '\n')
        mapping = {'duration_s': m['duration_s'], 'fps': FPS, 'width': W, 'height': H,
                   'measurement_label': m['measurement_label'], 'source_audio': 'muted',
                   'phase_boundaries_s': {key: m[key] for key in ('opening_s', 'comparison_start_s', 'result_start_s', 'speedup_start_s', 'logos_start_s', 'duration_s')},
                   'scenes': m['scenes'], 'note': 'Per-side clocks stop at stop_s; post-stop recording may keep playing as result showcase.'}
        (out / 'timing-map.json').write_text(json.dumps(mapping, indent=2) + '\n')
        tiles = []
        for label, t in preview_times(m):
            frame = draw_frame(m, t, ffmpeg=ffmpeg)
            frame.save(out / f'{label}.png')
            tiles.append((label, frame.resize((640, 360), Image.Resampling.LANCZOS)))
        sheet = Image.new('RGB', (1280, math.ceil(len(tiles) / 2) * 389), LIGHT)
        d = ImageDraw.Draw(sheet)
        for i, (label, frame) in enumerate(tiles):
            x, y = (i % 2) * 640, (i // 2) * 389
            d.text((x + 12, y + 4), label, font=font('manrope-700.ttf', 16), fill=INK)
            sheet.paste(frame, (x, y + 29))
        sheet.save(out / 'contact-sheet.png')
        mobile = Image.new('RGB', (375, len(tiles) * 211), LIGHT)
        for i, (_, frame) in enumerate(tiles):
            mobile.paste(frame.resize((375, 211), Image.Resampling.LANCZOS), (0, i * 211))
        mobile.save(out / 'mobile-review.png')
        if args.preview_only:
            print(f'Preview ready: {out / "contact-sheet.png"}')
            return 0
        with tempfile.TemporaryDirectory(prefix='cerebras-story-') as temp:
            paths = [Path(temp) / f'{side}.rgb' for side in ('left', 'right')]
            for side, path in zip(('left', 'right'), paths):
                normalize_side(ffmpeg, m, side, path)
            partial = Path(temp) / 'demo.mp4'
            command = [ffmpeg, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                       '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p',
                       '-movflags', '+faststart', str(partial)]
            with tempfile.TemporaryFile() as error:
                encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=error)
                streams = [open(path, 'rb') for path in paths]
                try:
                    for i in range(math.ceil(m['duration_s'] * FPS)):
                        t, sources = i / FPS, None
                        if phase_at(m, t) in ('transition', 'start_hold', 'comparison', 'result_cards') or (phase_at(m, t) == 'speedup' and t < m['speedup_start_s'] + 0.4):
                            comparison_t = min(m['comparison_s'], max(0, t - m['comparison_start_s']))
                            j = min(math.ceil(m['comparison_s'] * FPS), int(math.floor(comparison_t * FPS + 1e-6)))
                            sources = []
                            for stream in streams:
                                stream.seek(j * VIEW_W * VIEW_H * 3)
                                raw = stream.read(VIEW_W * VIEW_H * 3)
                                if len(raw) != VIEW_W * VIEW_H * 3:
                                    raise InputError('A comparison normalized stream ended unexpectedly.')
                                sources.append(Image.frombytes('RGB', (VIEW_W, VIEW_H), raw))
                        encoder.stdin.write(draw_frame(m, t, sources=sources, ffmpeg=ffmpeg).tobytes())
                    encoder.stdin.close()
                    if encoder.wait():
                        error.seek(0)
                        raise InputError(error.read().decode(errors='replace')[-1800:])
                except Exception:
                    encoder.terminate()
                    encoder.wait()
                    raise
                finally:
                    for stream in streams:
                        stream.close()
            shutil.copy2(partial, out / 'demo.mp4')
        print(f'Rendered {m["duration_s"]:.2f}s reference-story edit: {out / "demo.mp4"}')
        return 0
    except (InputError, OSError, BrokenPipeError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
