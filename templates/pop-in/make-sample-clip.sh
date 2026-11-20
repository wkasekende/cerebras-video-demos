#!/usr/bin/env bash
# A 12-second 16:9 stand-in clip so the pop-in template runs without a video of your own: a calm, brand-free, slowly moving gradient (swap in your own recording later).
set -e
cd "$(dirname "$0")"
ffmpeg -v error -y -f lavfi -i "gradients=size=1280x720:rate=30:speed=0.012:nb_colors=3:c0=0xe9e6e1:c1=0xd3ccc2:c2=0xf5f3ef" -t 12 -pix_fmt yuv420p sample.mp4
test -s sample.mp4 || { echo "could not make sample.mp4 (is ffmpeg installed?)"; exit 1; }
echo "wrote $(pwd)/sample.mp4"
