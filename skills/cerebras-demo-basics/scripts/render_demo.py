#!/usr/bin/env python3
"""Render one reproducible, silent Cerebras SBS edit from recordings and timing data."""
from __future__ import annotations

import argparse
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS = 1280, 720, 24
ORANGE, INK, GRAY = '#F15A29', '#252525', '#555650'
BG, LINE, SOFT = '#FDFDFD', '#DFDFDA', '#F4F4F1'
CW, CH = 568, 398


class InputError(ValueError):
    pass


def ffmpeg_binary():
    configured = os.environ.get('FFMPEG_BINARY')
    if configured:
        found = shutil.which(configured)
        if not found:
            raise InputError('FFMPEG_BINARY does not point to an executable.')
        return found
    found = shutil.which('ffmpeg')
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise InputError('Install Pillow and imageio-ffmpeg, or provide ffmpeg on PATH. See scripts/requirements.txt.')


def number(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise InputError(f'{label} must be a finite number >= {minimum}.')
    return float(value)


def string(value, label, max_length=None):
    if not isinstance(value, str) or not value.strip():
        raise InputError(f'{label} must be a nonempty string.')
    if max_length and len(value) > max_length:
        raise InputError(f'{label} is too long (maximum {max_length} characters).')
    return value.strip()


def probe(ffmpeg, path):
    result = subprocess.run([ffmpeg, '-hide_banner', '-i', str(path)], capture_output=True, text=True)
    duration = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', result.stderr)
    video = next((s for s in result.stderr.splitlines() if 'Video:' in s), '')
    size = re.search(r'\b(\d{2,5})x(\d{2,5})\b', video)
    if not duration or not size:
        raise InputError(f'Cannot read duration/dimensions of {path.name}. Supply a finite local video recording.')
    hrs, mins, secs = map(float, duration.groups())
    return {'duration_s': hrs * 3600 + mins * 60 + secs,
            'width': int(size[1]), 'height': int(size[2])}


def resolve_plate(value, manifest_path, label):
    source = Path(string(value, label)).expanduser()
    if not source.is_absolute():
        source = manifest_path.parent / source
    source = source.resolve()
    try:
        with Image.open(source) as picture:
            width, height = picture.size
            if picture.format not in ('PNG', 'JPEG'):
                raise InputError(f'{label} needs a PNG or JPEG; edit SVG masters separately.')
            if width < W or height < H or abs(width / height - W / H) > 0.02:
                raise InputError(f'{label} must be 16:9 and at least 1280×720 pixels.')
            picture.verify()
    except (OSError, ValueError) as e:
        if isinstance(e, InputError):
            raise
        raise InputError(f'Cannot read {label}: {e}')
    return str(source)


def load_manifest(path, ffmpeg):
    try:
        m = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise InputError(f'Cannot read manifest: {e}')
    if not isinstance(m, dict) or m.get('schema_version') != 1:
        raise InputError('schema_version must be 1.')
    if type(m.get('synthetic')) is not bool:
        raise InputError('Set synthetic explicitly to true for fixtures or false for real recordings.')
    for key in ('display_prompt', 'full_prompt', 'audience', 'takeaway', 'completion_boundary', 'disclosure'):
        m[key] = string(m.get(key), key, 200 if key == 'disclosure' else None)
    if m.get('comparison_kind') not in ('same_model_infrastructure', 'different_models_workflow'):
        raise InputError('comparison_kind must be same_model_infrastructure or different_models_workflow.')
    if m.get('background') is not None:
        plate = m['background']
        if not isinstance(plate, dict) or plate.get('fit', 'cover') != 'cover':
            raise InputError('background must be an object with image and optional fit=cover.')
        plate['image'] = resolve_plate(plate.get('image'), path, 'background.image')
        plate['fit'] = 'cover'
    for key, default in (('opening_s', 3), ('result_hold_s', 2), ('outro_s', 3)):
        m[key] = number(m.get(key, default), key, 1)
    if len(m['display_prompt'].split()) / m['opening_s'] > 5:
        raise InputError('Opening is too short for the displayed prompt. Shorten the prompt or increase opening_s.')
    for side in ('left', 'right'):
        p = m.get(side)
        if not isinstance(p, dict):
            raise InputError(f'{side} must be an object.')
        for key in ('model', 'provider', 'timing_evidence', 'result_note'):
            p[key] = string(p.get(key), f'{side}.{key}', 72 if key in ('model', 'provider') else None)
        source = Path(string(p.get('video'), f'{side}.video')).expanduser()
        if not source.is_absolute():
            source = path.parent / source
        source = source.resolve()
        if not source.is_file():
            raise InputError(f'{side}.video does not exist: {source}')
        p['video'] = str(source)
        p['start_s'] = number(p.get('start_s'), f'{side}.start_s')
        p['completion_s'] = number(p.get('completion_s'), f'{side}.completion_s', 1 / FPS)
        p['source_info'] = probe(ffmpeg, source)
        # Need an actual source frame at the supplied completion boundary.
        if p['start_s'] + p['completion_s'] > p['source_info']['duration_s'] - 1 / FPS + 1e-6:
            raise InputError(f'{side} recording needs footage through completion (plus at least one frame).')
        if p.get('crop') is not None:
            c = p['crop']
            if not isinstance(c, list) or len(c) != 4 or any(type(v) is not int for v in c):
                raise InputError(f'{side}.crop must be [x, y, width, height] in source pixels.')
            x, y, width, height = c
            if min(x, y) < 0 or min(width, height) <= 0 or x + width > p['source_info']['width'] or y + height > p['source_info']['height']:
                raise InputError(f'{side}.crop exceeds the recording bounds.')
    if m['left']['provider'].casefold() != 'cerebras':
        raise InputError('This layout puts provider Cerebras on the left; set left.provider to Cerebras.')
    if m['comparison_kind'] == 'same_model_infrastructure' and m['left']['model'] != m['right']['model']:
        raise InputError('same_model_infrastructure requires identical model labels; otherwise use different_models_workflow.')
    endpoint = max(m[s]['completion_s'] for s in ('left', 'right'))
    timeline = m.get('timeline')
    if not isinstance(timeline, list) or not timeline:
        raise InputError('timeline must contain explicit contiguous from_s/to_s/speed segments.')
    cursor, output_time = 0.0, 0.0
    for i, seg in enumerate(timeline):
        if not isinstance(seg, dict):
            raise InputError(f'timeline[{i}] must be an object.')
        for key in ('from_s', 'to_s', 'speed'):
            seg[key] = number(seg.get(key), f'timeline[{i}].{key}', 1 if key == 'speed' else 0)
        if abs(seg['from_s'] - cursor) > 1e-6 or seg['to_s'] <= seg['from_s']:
            raise InputError('Timeline must be contiguous, increasing, and start at elapsed time 0. No hidden cuts.')
        seg['output_from_s'] = output_time
        output_time += (seg['to_s'] - seg['from_s']) / seg['speed']
        seg['output_to_s'] = output_time
        cursor = seg['to_s']
    if abs(cursor - endpoint) > 1e-6:
        raise InputError('Timeline must end at the later supplied completion time.')
    # Return to real time for a readable final reveal, instead of hiding it in acceleration.
    if timeline[-1]['speed'] != 1 or timeline[-1]['to_s'] - timeline[-1]['from_s'] < 1:
        raise InputError('Keep the final second or more of the comparison at 1x for the result reveal.')
    claim = m.get('outro', {})
    if not isinstance(claim, dict) or claim.get('metric', 'elapsed_time') not in ('elapsed_time', 'measured_throughput'):
        raise InputError('outro.metric must be elapsed_time or measured_throughput.')
    claim['metric'] = claim.get('metric', 'elapsed_time')
    if claim['metric'] == 'measured_throughput':
        claim['tokens_per_second'] = number(claim.get('tokens_per_second'), 'outro.tokens_per_second', 0.001)
        claim['evidence'] = string(claim.get('evidence'), 'outro.evidence')
    if claim.get('image') is not None:
        claim['image'] = resolve_plate(claim['image'], path, 'outro.image')
        claim['summary_s'] = number(claim.get('summary_s', 1.5), 'outro.summary_s', 0.5)
        if claim['summary_s'] > m['outro_s'] - 1:
            raise InputError('Leave at least one second of the supplied outro artwork after the summary fades.')
    m['outro'] = claim
    card = m.get('completion_card', {})
    if not isinstance(card, dict) or type(card.get('enabled', True)) is not bool:
        raise InputError('completion_card must be an object with an optional enabled boolean.')
    card['enabled'] = card.get('enabled', True)
    card['duration_s'] = number(card.get('duration_s', 2.5), 'completion_card.duration_s', 1.5)
    card['partner_name'] = string(card.get('partner_name', 'Partner'), 'completion_card.partner_name', 50)
    if card.get('partner_logo') is not None:
        source = Path(string(card['partner_logo'], 'completion_card.partner_logo')).expanduser()
        if not source.is_absolute():
            source = path.parent / source
        source = source.resolve()
        try:
            with Image.open(source) as logo:
                if logo.format not in ('PNG', 'JPEG'):
                    raise InputError('Partner logo must be PNG or JPEG; render an SVG to PNG first.')
                logo.verify()
        except OSError as e:
            raise InputError(f'Cannot read completion_card.partner_logo: {e}')
        card['partner_logo'] = str(source)
    m['completion_card'] = card
    m['comparison_s'] = output_time
    m['comparison_end_s'] = m['opening_s'] + output_time + m['result_hold_s']
    m['outro_start_s'] = m['comparison_end_s'] + (card['duration_s'] if card['enabled'] else 0)
    m['duration_s'] = m['outro_start_s'] + m['outro_s']
    if m['duration_s'] >= 60:
        raise InputError(f'Edit is {m["duration_s"]:.2f}s; this social SBS layout requires <60s. Choose an explicit timeline or a different format.')
    return m


def elapsed_at(m, comparison_t):
    if comparison_t >= m['comparison_s']:
        return m['timeline'][-1]['to_s'], 1.0
    for seg in m['timeline']:
        if comparison_t < seg['output_to_s']:
            return seg['from_s'] + max(0, comparison_t - seg['output_from_s']) * seg['speed'], seg['speed']
    raise AssertionError('unreachable')


def time_label(seconds):
    # Integer tenths keep carry correct at e.g. 59.96 seconds.
    tenths = int(math.floor(seconds * 10 + 0.5))
    minutes, rem = divmod(tenths, 600)
    return f'{minutes}m{rem // 10:02d}.{rem % 10}s'


def recorded_progress(elapsed, completion):
    """Position in a completed recording, not a model's estimate of work finished."""
    return min(1.0, max(0.0, elapsed / completion))


def phase_at(m, t):
    if t < m['opening_s']:
        return 'prompt'
    if t < m['comparison_end_s']:
        return 'comparison'
    if t < m['outro_start_s']:
        return 'completion_card'
    return 'outro'


def font(name, size):
    return ImageFont.truetype(str(ROOT / 'assets' / 'fonts' / name), size)


def wrap(draw, text, face, width):
    lines, line = [], ''
    for word in text.split():
        if draw.textlength(word, font=face) > width:
            raise InputError('An unbroken text token is too wide for this layout. Shorten the display copy.')
        candidate = f'{line} {word}'.strip()
        if draw.textlength(candidate, font=face) <= width:
            line = candidate
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def text_block(draw, text, xy, width, size, max_lines, fill=INK, family='manrope-700.ttf', center=False, min_size=16):
    for chosen in range(size, min_size - 1, -1):
        face = font(family, chosen)
        lines = wrap(draw, text, face, width)
        if len(lines) <= max_lines:
            break
    else:
        raise InputError(f'Text does not fit: {text[:90]}')
    x, y = xy
    for line in lines:
        dx = (width - draw.textlength(line, font=face)) / 2 if center else 0
        draw.text((x + dx, y), line, font=face, fill=fill)
        y += chosen * 1.35
    return y


def decode_frame(ffmpeg, p, elapsed):
    timestamp = p['start_s'] + min(elapsed, p['completion_s'])
    filters = []
    if p.get('crop'):
        x, y, width, height = p['crop']
        filters.append(f'crop={width}:{height}:{x}:{y}')
    filters += [f'scale={CW}:{CH}:force_original_aspect_ratio=decrease',
                f'pad={CW}:{CH}:(ow-iw)/2:(oh-ih)/2:color=0xF4F4F1', 'setsar=1']
    r = subprocess.run([ffmpeg, '-v', 'error', '-ss', f'{timestamp:.8f}', '-i', p['video'],
                        '-frames:v', '1', '-vf', ','.join(filters), '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'], capture_output=True)
    if r.returncode or len(r.stdout) != CW * CH * 3:
        raise InputError(f'Cannot decode {Path(p["video"]).name} at {timestamp:.3f}s: {r.stderr.decode(errors="replace")[-500:]}')
    return Image.frombytes('RGB', (CW, CH), r.stdout)


def decode_stream(ffmpeg, p, m, destination):
    """Normalize the exact same explicit edit map used by the overlay clocks."""
    frames_total = math.ceil((m['comparison_s'] + m['result_hold_s']) * FPS)
    # Explicit source sampling makes timestamps auditable and avoids filter/overlay drift.
    # ffmpeg decodes source frames once; Python chooses nearest preceding source frame.
    filters = []
    if p.get('crop'):
        x, y, width, height = p['crop']
        filters.append(f'crop={width}:{height}:{x}:{y}')
    filters += [f'fps={FPS}', f'scale={CW}:{CH}:force_original_aspect_ratio=decrease',
                f'pad={CW}:{CH}:(ow-iw)/2:(oh-ih)/2:color=0xF4F4F1', 'setsar=1']
    cmd = [ffmpeg, '-v', 'error', '-ss', str(p['start_s']), '-i', p['video'],
           '-t', str(p['completion_s'] + 2 / FPS), '-vf', ','.join(filters), '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']
    with tempfile.TemporaryFile() as err, open(destination, 'wb') as target:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err)
        current, source_index = None, -1
        try:
            for i in range(frames_total):
                elapsed, _ = elapsed_at(m, i / FPS)
                wanted = int(math.floor(min(elapsed, p['completion_s']) * FPS + 1e-7))
                while source_index < wanted:
                    chunk = proc.stdout.read(CW * CH * 3)
                    if len(chunk) != CW * CH * 3:
                        raise InputError(f'Source {Path(p["video"]).name} ended before its supplied completion timestamp.')
                    current, source_index = chunk, source_index + 1
                target.write(current)
        finally:
            proc.stdout.close()
            proc.terminate()
            proc.wait()


@lru_cache(maxsize=8)
def load_background(path):
    with Image.open(path) as picture:
        return ImageOps.fit(picture.convert('RGB'), (W, H), method=Image.Resampling.LANCZOS)


def base(m):
    plate = m.get('background')
    canvas = load_background(plate['image']).copy() if plate else Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(canvas)
    d.rectangle((0, 626, W, H), fill=BG)
    if m['synthetic']:
        d.rectangle((0, 0, W, 38), fill=SOFT)
        text_block(d, 'SYNTHETIC EXAMPLE  /  NOT A BENCHMARK', (30, 8), 1220, 16, 1, GRAY, center=True)
    text_block(d, m['disclosure'], (48, 630), 1184, 32, 2, GRAY, family='manrope-600.ttf', center=True, min_size=28)
    return canvas


def outro_copy(m):
    left, right = m['left'], m['right']
    if m['outro']['metric'] == 'measured_throughput':
        metric = f'{m["outro"]["tokens_per_second"]:g} tokens/s'
        detail = 'Measured Cerebras token throughput · see project evidence'
    elif m['comparison_kind'] == 'same_model_infrastructure' and right['completion_s'] > left['completion_s']:
        ratio = right['completion_s'] / left['completion_s']
        metric = f'{ratio:.1f}× faster on this task'
        detail = f'{time_label(left["completion_s"])} on Cerebras  /  {time_label(right["completion_s"])} on {right["provider"]}'
    else:
        metric = f'{time_label(left["completion_s"])} vs {time_label(right["completion_s"])}'
        detail = f'Cerebras: {left["model"]}  /  {right["provider"]}: {right["model"]}'
    return metric, detail


def draw_supplied_outro(m, elapsed):
    """Use the user's complete artwork; add a brief summary in its empty upper area."""
    canvas = load_background(m['outro']['image']).copy().convert('RGBA')
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    if m['synthetic']:
        d.rectangle((0, 0, W, 36), fill=(18, 14, 12, 235))
        text_block(d, 'SYNTHETIC EXAMPLE  /  NOT A BENCHMARK', (30, 7), 1220, 16, 1, 'white', center=True)
    d.rounded_rectangle((28, 626, 1252, 716), radius=12, fill=(18, 14, 12, 215))
    text_block(d, m['disclosure'], (48, 630), 1184, 32, 2, 'white', family='manrope-600.ttf', center=True, min_size=28)
    canvas = Image.alpha_composite(canvas, overlay)
    summary_s = m['outro']['summary_s']
    if elapsed < summary_s:
        layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        metric, detail = outro_copy(m)
        text_block(d, m['left']['model'], (90, 92), 1100, 34, 2, 'white', center=True)
        text_block(d, metric, (80, 177), 1120, 48, 1, ORANGE, family='sometype-mono-700.ttf', center=True, min_size=28)
        text_block(d, detail, (80, 251), 1120, 22, 2, 'white', center=True)
        opacity = min(1, max(0, (summary_s - elapsed) / 0.35))
        layer.putalpha(layer.getchannel('A').point(lambda value: round(value * opacity)))
        canvas = Image.alpha_composite(canvas, layer)
    return canvas.convert('RGB')


@lru_cache(maxsize=16)
def contained_logo(path, width, height):
    with Image.open(path) as image:
        return ImageOps.contain(image.convert('RGBA'), (width, height), method=Image.Resampling.LANCZOS)


def draw_completion_card(m):
    canvas = base(m)
    d = ImageDraw.Draw(canvas)
    d.rounded_rectangle((116, 76, 1164, 612), radius=24, fill='white', outline=LINE, width=2)
    text_block(d, 'DONE', (160, 98), 960, 96, 1, ORANGE, family='manrope-800.ttf', center=True)
    text_block(d, m['left']['model'], (160, 223), 960, 30, 2, INK, family='manrope-700.ttf', center=True)
    times = f'{time_label(m["left"]["completion_s"])}  /  {time_label(m["right"]["completion_s"])}'
    text_block(d, times, (160, 284), 960, 32, 1, INK, family='sometype-mono-600.ttf', center=True)
    text_block(d, 'Cerebras / comparison · recorded task times', (160, 334), 960, 18, 1, GRAY, family='manrope-600.ttf', center=True)
    # Rasterized from the supplied vector master, not a typeset imitation of the wordmark.
    logo = contained_logo(str(ROOT / 'assets' / 'cerebras-wordmark-rendered.png'), 308, 142)
    canvas.paste(logo, (244 + (320 - logo.width) // 2, 403 + (150 - logo.height) // 2), logo)
    text_block(d, '/', (610, 445), 60, 40, 1, GRAY, family='manrope-600.ttf', center=True)
    card = m['completion_card']
    if card.get('partner_logo'):
        logo = contained_logo(card['partner_logo'], 308, 126)
        canvas.paste(logo, (716 + (320 - logo.width) // 2, 415 + (126 - logo.height) // 2), logo)
    else:
        d.rounded_rectangle((716, 419, 1036, 541), radius=14, fill=SOFT, outline='#A6A6A0', width=2)
        text_block(d, 'PARTNER LOGO', (734, 448), 284, 25, 1, GRAY, family='manrope-700.ttf', center=True)
        text_block(d, 'Replace with partner asset', (734, 486), 284, 16, 1, GRAY, family='manrope-600.ttf', center=True)
    return canvas


def draw_frame(m, t, sources=None, ffmpeg=None):
    canvas = base(m)
    d = ImageDraw.Draw(canvas)
    opening, phase = m['opening_s'], phase_at(m, t)
    if t < opening:
        d.rounded_rectangle((108, 198, 1172, 498), radius=24, fill='white', outline=LINE, width=2)
        text_block(d, 'PROMPT', (146, 230), 988, 16, 1, GRAY)
        # Start typing on frame zero; finish with a short readable hold.
        progress = min(1, max(1 / len(m['display_prompt']), t / (opening * 0.72)))
        n = max(1, math.ceil(len(m['display_prompt']) * progress))
        visible = m['display_prompt'][:n] + ('|' if n < len(m['display_prompt']) else '')
        text_block(d, visible, (146, 281), 988, 38, 3, family='instrument-sans-latin.woff2', min_size=26)
        return canvas
    if phase == 'completion_card':
        return draw_completion_card(m)
    if phase == 'outro':
        left, right = m['left'], m['right']
        if m['outro'].get('image'):
            return draw_supplied_outro(m, t - m['outro_start_s'])
        if m.get('background'):
            d.rounded_rectangle((60, 76, 1220, 610), radius=24, fill='white', outline=LINE, width=2)
        text_block(d, left['model'], (100, 146), 1080, 42, 2, center=True)
        metric, detail = outro_copy(m)
        text_block(d, metric, (70, 272), 1140, 56, 2, ORANGE, family='sometype-mono-700.ttf', center=True, min_size=30)
        text_block(d, detail, (100, 380), 1080, 21, 2, GRAY, center=True)
        logo = Image.open(ROOT / 'assets' / 'cerebras-logo.png').convert('RGBA')
        logo.thumbnail((96, 96), Image.Resampling.LANCZOS)
        canvas.paste(logo, ((W - logo.width) // 2, 474), logo)
        return canvas
    comparison_t = t - opening
    elapsed, speed = elapsed_at(m, comparison_t)
    for index, side in enumerate(('left', 'right')):
        p = m[side]
        x = 32 + index * 616
        done = elapsed + 1e-7 >= p['completion_s']
        accent = ORANGE if side == 'left' else GRAY
        d.rounded_rectangle((x, 78, x + 600, 618), radius=20, fill='white', outline=ORANGE if side == 'left' and done else LINE, width=4 if side == 'left' and done else 2)
        text_block(d, f'on {p["provider"]}', (x + 20, 98), 350, 17, 1, accent, min_size=16)
        text_block(d, p['model'], (x + 20, 124), 350, 24, 2, min_size=18)
        timer_bg = ORANGE if side == 'left' and done else (SOFT if not done else GRAY)
        d.rounded_rectangle((x + 398, 98, x + 580, 168), radius=14, fill=timer_bg)
        if done:
            text_block(d, 'DONE', (x + 406, 104), 166, 14, 1, 'white', center=True, min_size=14)
        label = time_label(min(elapsed, p['completion_s']))
        text_block(d, label, (x + 406, 128 if done else 118), 166, 25, 1, 'white' if done else accent, family='sometype-mono-700.ttf', center=True, min_size=18)
        if sources:
            recording = sources[index]
        else:
            recording = decode_frame(ffmpeg, p, elapsed)
        mask = Image.new('L', (CW, CH), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, CW, CH), radius=10, fill=255)
        canvas.paste(recording, (x + 16, 182), mask)
        # This is the position in the known recorded run; no live progress is inferred.
        d.rounded_rectangle((x + 28, 596, x + 572, 604), radius=4, fill='#F3D9CF' if side == 'left' else '#E5E5E1')
        fill_width = round(544 * recorded_progress(elapsed, p['completion_s']))
        if fill_width:
            d.rounded_rectangle((x + 28, 596, x + 28 + fill_width, 604), radius=min(4, fill_width / 2), fill=accent)
        if not done and speed > 1:
            # Large enough to read while leaving part of the task visible.
            d.rounded_rectangle((x + 70, 370, x + 530, 480), radius=14, fill=GRAY)
            text_block(d, 'FAST FORWARD', (x + 86, 385), 428, 28, 1, 'white', center=True)
            text_block(d, f'{speed:g}×', (x + 86, 426), 428, 30, 1, 'white', family='sometype-mono-700.ttf', center=True)
    return canvas


def preview_times(m):
    samples = [('01-prompt', m['opening_s'] * 0.65), ('02-start', m['opening_s'])]
    mid_run = min(m[side]['completion_s'] for side in ('left', 'right')) / 2
    for seg in m['timeline']:
        if mid_run <= seg['to_s']:
            samples.append(('02-progress', m['opening_s'] + seg['output_from_s'] + (mid_run - seg['from_s']) / seg['speed']))
            break
    for side in ('left', 'right'):
        completion = m[side]['completion_s']
        for seg in m['timeline']:
            if completion <= seg['to_s'] + 1e-6:
                samples.append((f'03-{side}-done', m['opening_s'] + seg['output_from_s'] + (completion - seg['from_s']) / seg['speed']))
                break
    for seg in m['timeline']:
        if seg['speed'] > 1:
            samples.append(('04-fast-forward', m['opening_s'] + (seg['output_from_s'] + seg['output_to_s']) / 2))
            break
    samples += [('05-both-results', m['opening_s'] + m['comparison_s'] + m['result_hold_s'] / 2)]
    if m['completion_card']['enabled']:
        samples += [('06-done-card', m['comparison_end_s'] + m['completion_card']['duration_s'] / 2)]
    samples += [('07-outro-summary', m['outro_start_s'] + 0.5),
                ('08-outro-brand', m['duration_s'] - 0.5)]
    return samples


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        ffmpeg = ffmpeg_binary()
        m = load_manifest(args.manifest.resolve(), ffmpeg)
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        (output / 'manifest.resolved.json').write_text(json.dumps(m, indent=2) + '\n')
        timing = {'fps': FPS, 'width': W, 'height': H, 'duration_s': m['duration_s'],
                  'source_audio': 'muted', 'synthetic': m['synthetic'],
                  'comparison_segments': m['timeline'],
                  'phase_boundaries_s': {'prompt_end': m['opening_s'], 'comparison_and_result_hold_end': m['comparison_end_s'],
                                         'outro_start': m['outro_start_s'], 'video_end': m['duration_s']},
                  'completion_s': {s: m[s]['completion_s'] for s in ('left', 'right')}}
        (output / 'timing-map.json').write_text(json.dumps(timing, indent=2) + '\n')
        tiles = []
        for label, t in preview_times(m):
            frame = draw_frame(m, t, ffmpeg=ffmpeg)
            frame.save(output / f'{label}.png')
            tile = frame.resize((640, 360), Image.Resampling.LANCZOS)
            tiles.append(tile)
        sheet = Image.new('RGB', (1280, 360 * math.ceil(len(tiles) / 2)), SOFT)
        for i, tile in enumerate(tiles):
            sheet.paste(tile, (640 * (i % 2), 360 * (i // 2)))
        sheet.save(output / 'contact-sheet.png')
        mobile = Image.new('RGB', (375, 211 * len(tiles)), SOFT)
        for i, tile in enumerate(tiles):
            mobile.paste(tile.resize((375, 211), Image.Resampling.LANCZOS), (0, 211 * i))
        mobile.save(output / 'mobile-review.png')
        if args.preview_only:
            print(f'Preview ready: {output / "contact-sheet.png"}')
            return 0
        total_frames = math.ceil(m['duration_s'] * FPS)
        with tempfile.TemporaryDirectory(prefix='cerebras-demo-') as tmp:
            normalized = [Path(tmp) / f'{side}.rgb' for side in ('left', 'right')]
            for side, path in zip(('left', 'right'), normalized):
                decode_stream(ffmpeg, m[side], m, path)
            partial = Path(tmp) / 'demo.mp4'
            cmd = [ffmpeg, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
                   '-r', str(FPS), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
                   '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(partial)]
            with tempfile.TemporaryFile() as err:
                encoder = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=err)
                streams = [open(p, 'rb') for p in normalized]
                previous = -1
                cached = None
                try:
                    for i in range(total_frames):
                        t = i / FPS
                        sources = None
                        if phase_at(m, t) == 'comparison':
                            j = int(math.floor((t - m['opening_s']) * FPS + 1e-6))
                            if j != previous:
                                sources = []
                                for stream in streams:
                                    stream.seek(j * CW * CH * 3)
                                    raw = stream.read(CW * CH * 3)
                                    if len(raw) != CW * CH * 3:
                                        raise InputError('Normalized recording ended unexpectedly.')
                                    sources.append(Image.frombytes('RGB', (CW, CH), raw))
                                cached, previous = sources, j
                            sources = cached
                        encoder.stdin.write(draw_frame(m, t, sources=sources, ffmpeg=ffmpeg).tobytes())
                    encoder.stdin.close()
                    if encoder.wait():
                        err.seek(0)
                        raise InputError(err.read().decode(errors='replace')[-2000:])
                except Exception:
                    encoder.terminate()
                    encoder.wait()
                    raise
                finally:
                    for stream in streams:
                        stream.close()
            shutil.copy2(partial, output / 'demo.mp4')
        print(f'Rendered {total_frames} frames: {output / "demo.mp4"}')
        return 0
    except (InputError, OSError, BrokenPipeError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
