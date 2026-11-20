'use strict';
/* ── THE RACE, RENDERED IN A LAMBDA ──────────────────────────────────────────
   One window of a race film. The page is the race's own built page (fonts,
   sheet, engine and timeline inline - build.py's output, shipped in the
   payload), and the driver is the same loop race/agent-film.mjs runs locally:
   seek each frame time, screenshot when the signature changed, fold holds.
   The window is encoded CONSTANT-RATE so n windows join with `-c copy`
   (the concat demuxer carries no per-frame timing across pieces, so pieces
   are CFR or the join drifts).

   job.json: { work, page, from, to, fps, scale, W, H, url, out, relaunchEvery }
   Chrome is DEMOKIT_CHROME (what the handler acquired), puppeteer-core is
   DEMOKIT_PPTR, ffmpeg is on PATH. */
const fs = require('fs'), path = require('path');
const { execFileSync } = require('child_process');

const job = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const { work, from, to, fps, scale, W, H, out } = job;
const RELAUNCH = job.relaunchEvery || 250;

(async () => {
  const pptr = require(process.env.DEMOKIT_PPTR || 'puppeteer-core');
  const ARGS = ['--allow-file-access-from-files', '--disable-gpu', '--disable-software-rasterizer',
    '--hide-scrollbars', '--font-render-hinting=none', '--disable-font-subpixel-positioning',
    '--disable-lcd-text', '--force-color-profile=srgb', '--no-first-run', '--mute-audio',
    '--no-sandbox', '--disable-setuid-sandbox', '--no-zygote'];
  let browser = null, pg = null, since = 0;
  const T0 = Date.now();
  const mark = s => console.log(`  [race] ${s} +${((Date.now() - T0) / 1000).toFixed(1)}s`);
  async function launch() {
    if (browser) { try { await browser.close(); } catch {} }
    browser = await pptr.launch({ executablePath: process.env.DEMOKIT_CHROME, headless: 'new', protocolTimeout: 120000, args: ARGS });
    pg = await browser.newPage();
    await pg.setViewport({ width: W, height: H, deviceScaleFactor: scale });
    await pg.goto('file://' + path.join(work, 'page.html') + job.url, { waitUntil: 'load' });
    await pg.evaluate(() => document.fonts.ready.then(() => undefined));
    since = 0;
  }
  await launch();
  mark('page up');
  const seek = async ms => {
    try { return await pg.evaluate(t => window.__demo.seek(t), ms); }
    catch (e) { await launch(); return pg.evaluate(t => window.__demo.seek(t), ms); }
  };
  const dir = path.join(work, 'frames'); fs.mkdirSync(dir, { recursive: true });
  const step = 1000 / fps;
  const names = [], durs = [];
  let lastSig = null, n = 0, shot = 0;
  for (let t = from; t < to - 1e-6; t += step) {
    const sig = await seek(t);
    if (sig === lastSig) { durs[durs.length - 1] += 1; }
    else {
      if (since >= RELAUNCH) { await launch(); await seek(t); mark('relaunched'); }
      const f = path.join(dir, `f${String(shot++).padStart(5, '0')}.png`);
      await pg.screenshot({ path: f, type: 'png' }); since++;
      names.push(f); durs.push(1); lastSig = sig;
    }
    n++;
  }
  mark(`captured ${n} frames, ${shot} distinct`);
  await browser.close();
  /* CFR: every captured frame held for its count of frame slots, at exactly fps */
  const list = path.join(work, 'list.ffconcat');
  fs.writeFileSync(list, 'ffconcat version 1.0\n' + names.map((f, i) => `file '${f}'\nduration ${(durs[i] / fps).toFixed(6)}\n`).join('') + `file '${names[names.length - 1]}'\n`);
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list,
    '-vf', `fps=${fps},format=yuv420p`, '-r', String(fps), '-fps_mode', 'cfr', '-frames:v', String(n),
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-bf', '0', '-g', String(fps), '-movflags', '+faststart', out]);
  mark(`encoded ${n} frames at ${fps}fps`);
})().catch(e => { console.error(e && e.stack || e); process.exit(1); });
