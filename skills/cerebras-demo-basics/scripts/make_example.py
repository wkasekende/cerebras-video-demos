#!/usr/bin/env python3
"""Regenerate the small, conspicuously synthetic videos shipped with the skill."""
from pathlib import Path
import subprocess
from PIL import Image, ImageDraw
from render_demo import ffmpeg_binary, font, ORANGE, GRAY, INK, SOFT

ROOT = Path(__file__).resolve().parents[1]
FPS, WIDTH, HEIGHT = 12, 960, 540


def main():
    ffmpeg = ffmpeg_binary()
    media = ROOT / 'examples' / 'media'
    media.mkdir(parents=True, exist_ok=True)
    for side, completion in [('left', 4), ('right', 12)]:
        color = ORANGE if side == 'left' else GRAY
        path = media / f'synthetic-{side}.mp4'
        cmd = [ffmpeg, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{WIDTH}x{HEIGHT}',
               '-r', str(FPS), '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for i in range(int((completion + 1.5) * FPS)):
                elapsed = min(completion, max(0, i / FPS - 0.5))
                progress = elapsed / completion
                canvas = Image.new('RGB', (WIDTH, HEIGHT), '#FDFDFD')
                d = ImageDraw.Draw(canvas)
                d.rectangle((0, 0, WIDTH, 48), fill=SOFT)
                d.text((26, 10), 'SYNTHETIC SOURCE  ·  TEST FIXTURE', font=font('sometype-mono-700.ttf', 20), fill=GRAY)
                d.text((38, 88), 'Create a financial dashboard', font=font('manrope-700.ttf', 30), fill=INK)
                d.text((38, 140), 'Simulated build progress — no model was run', font=font('manrope-600.ttf', 22), fill=GRAY)
                d.line((38, 207, 922, 207), fill=SOFT, width=2)
                if progress >= 1:
                    for j, (label, value) in enumerate([('EXAMPLE VALUE', '$128,400'), ('EXAMPLE CHANGE', '+4.2%'), ('EXAMPLE ITEMS', '24')]):
                        x = 38 + j * 300
                        d.rounded_rectangle((x, 270, x + 282, 382), radius=10, fill=SOFT)
                        d.text((x + 18, 289), label, font=font('manrope-700.ttf', 16), fill=GRAY)
                        d.text((x + 18, 323), value, font=font('manrope-800.ttf', 30), fill=color)
                    d.text((38, 425), 'Sample result complete', font=font('manrope-700.ttf', 25), fill=color)
                else:
                    d.text((38, 288), 'Preparing dashboard…', font=font('sometype-mono-600.ttf', 28), fill=color)
                    for j in range(3):
                        d.rounded_rectangle((38, 355 + j * 30, 640 + j * 70, 369 + j * 30), radius=6, fill=SOFT)
                proc.stdin.write(canvas.tobytes())
            proc.stdin.close()
            if proc.wait():
                raise RuntimeError('Example encoder failed')
        except Exception:
            proc.terminate()
            proc.wait()
            raise
        print(path)


if __name__ == '__main__':
    main()
