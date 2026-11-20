#!/usr/bin/env node
/* ── PHOTOGRAPH AN AGENT FILM ────────────────────────────────────────────────────────────────────────────────
     python3 artifact/agent_film.py templates/agent-film/storyboard.json     # builds out/agent-film/<slug>/film.html
     node tools/agent-film.mjs out/agent-film/<slug>/film.html               # -> out/agent-film/<slug>/<slug>.mp4
       --fps n          frames a second (default: the storyboard's, 30)
       --out path       where the mp4 goes
       --png-at ms      one still at that time instead of the film
       --contact        also a contact sheet, one frame a second
       --engine lambda  render in the cloud: the function lambda/deploy.sh deploys (DEMOKIT_LAMBDA_FN, DEMOKIT_LAMBDA_REGION; AWS credentials in the environment).
                        The self-contained film.cloud.html is the payload, the film is cut into --segments n windows (default: one per ~90 frames) rendered at once, and the pieces join with -c copy.

   The page is deterministic in time: AgentFilm.seek(ms) paints one instant and resolves once it has. This drives a real Chrome (tools/chrome.mjs) through each frame time,
   photographs the page, and encodes the frames with ffmpeg (H.264, yuv420p, constant frame rate). */
import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';
import zlib from 'zlib';
import { createRequire } from 'module';
import { launch } from './chrome.mjs';

const argv = process.argv.slice(2);
const opt = (n, d) => { const i = argv.indexOf('--' + n); return i >= 0 && !String(argv[i + 1] || '').startsWith('--') ? argv[i + 1] : (i >= 0 ? true : d); };
const page = argv.find(a => !a.startsWith('--') && a.endsWith('.html'));
if (!page) { console.error('usage: agent-film.mjs <film.html> [--fps n] [--out x.mp4] [--png-at ms] [--contact]'); process.exit(2); }
const dir = path.dirname(path.resolve(page));
const meta = JSON.parse(fs.readFileSync(path.join(dir, 'film.json'), 'utf8'));
const fps = +opt('fps', meta.fps || 30);
const T0 = Date.now(); const log = s => console.error(`  [${((Date.now() - T0) / 1000).toFixed(1)}s] ${s}`);

if (opt('engine') === 'lambda') {
  const { invokeLambda } = createRequire(import.meta.url)('../lambda/aws.cjs');
  const FN = process.env.DEMOKIT_LAMBDA_FN || 'demokit-render', REGION = process.env.DEMOKIT_LAMBDA_REGION || 'us-east-1';
  /* a film with a pop-in clip: its frames (about 1608 x 905, one per frame) are far past the 6 MB invoke payload, so they are tarred, put in the deploy bucket under assets/, and fetched by each window;
     the page then references them by relative path, exactly as the local film does (film.html, not film.cloud.html) */
  let assets = null;
  if (meta.popin) {
    const crypto = await import('crypto');
    const tgz = path.join(dir, 'popin.tar.gz');
    const t = spawnSync('tar', ['-czf', tgz, '-C', dir, 'popin'], { stdio: 'inherit' });
    if (t.status !== 0) { console.error('agent-film: tar failed (a pop-in film needs `tar` and the aws CLI to render in the cloud)'); process.exit(1); }
    const sha = crypto.createHash('sha256').update(fs.readFileSync(tgz)).digest('hex').slice(0, 12);
    const acct = spawnSync('aws', ['sts', 'get-caller-identity', '--query', 'Account', '--output', 'text'], { encoding: 'utf8' }).stdout.trim();
    const bucket = process.env.DEMOKIT_LAMBDA_BUCKET || `demokit-render-deploy-${acct}`;
    const key = `assets/${meta.slug}-${sha}.tar.gz`;
    const up = spawnSync('aws', ['s3', 'cp', tgz, `s3://${bucket}/${key}`, '--region', REGION, '--no-progress'], { stdio: ['ignore', 'ignore', 'inherit'] });
    if (up.status !== 0) { console.error('agent-film: could not upload the clip frames to s3://' + bucket + ' (is the aws CLI configured, and is the function deployed with bash lambda/deploy.sh?)'); process.exit(1); }
    assets = { s3: `s3://${bucket}/${key}` };
    log(`uploaded the clip's frames to s3://${bucket}/${key}`);
  }
  const pageGz = zlib.gzipSync(fs.readFileSync(path.join(dir, meta.popin ? 'film.html' : 'film.cloud.html')), { level: 9 });
  const n = Math.ceil(meta.duration / 1000 * fps), step = 1000 / fps;
  const segN = Math.max(1, Math.min(16, +opt('segments', Math.ceil(n / 90)) || 1)), per = Math.ceil(n / segN);
  const jobs = [];
  for (let k = 0; k < segN; k++) { const f0 = k * per, f1 = Math.min(n, (k + 1) * per); if (f0 < f1) jobs.push({ from: f0 * step, to: f1 * step }); }
  const pageB64 = pageGz.toString('base64');
  if (pageB64.length > 5.8 * 1024 * 1024) { console.error(`agent-film: the cloud page is ${(pageB64.length / 1048576).toFixed(1)} MB, over the 6 MB invoke limit (a long pop-in clip is the usual cause): shorten the clip, or render locally`); process.exit(1); }
  log(`[lambda] ${FN}@${REGION}: ${jobs.length} window(s), ${n} frames at ${fps} fps (payload ${Math.round(pageB64.length / 1024)} KB)`);
  const tmp = fs.mkdtempSync(path.join(process.env.DEMOKIT_TMP || (await import('os')).tmpdir(), 'agent-film-lambda-'));
  const one = async (j, i) => {
    const body = JSON.stringify({ demokit: { page: pageB64, ...(assets ? { assets } : {}), job: { from: j.from, to: j.to, fps, scale: 1, W: 1920, H: 1080, url: '', relaunchEvery: 200 } } });
    let real = 0, throttled = 0;   // a 429 (the account's concurrent-invocation limit, shared by every film rendering at once) is waited out with a growing pause and does not count as a failure; any other failure gets two tries
    for (;;) {
      const r = await invokeLambda(FN, REGION, body);
      let reply = null; try { reply = JSON.parse(r.body); } catch {}
      if (r.status === 200 && !r.fnError && reply && reply.mp4) { const f = path.join(tmp, `seg${String(i).padStart(2, '0')}.mp4`); fs.writeFileSync(f, Buffer.from(reply.mp4, 'base64')); log(`window ${i + 1}/${jobs.length} done`); return f; }
      if (r.status === 429 && ++throttled <= 12) { const w = Math.min(60, 4 * throttled) + Math.random() * 5; log(`window ${i + 1} throttled (concurrency limit), waiting ${w.toFixed(0)} s`); await new Promise(res => setTimeout(res, w * 1000)); continue; }
      log(`window ${i + 1} attempt ${++real} failed: ${(r.fnError || r.status)} ${String(r.body).slice(0, 300)}`);
      if (real >= 2) break;
    }
    throw new Error(`window ${i + 1} failed twice`);
  };
  const maxPar = Math.max(1, +opt('max-parallel', 24) || 24), files = new Array(jobs.length);   // at most this many windows in flight from this process (default 24)
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(maxPar, jobs.length) }, async () => { for (;;) { const k = next++; if (k >= jobs.length) return; files[k] = await one(jobs[k], k); } }));
  const out = typeof opt('out') === 'string' ? opt('out') : path.join(dir, meta.slug + '.cloud.mp4');
  fs.writeFileSync(path.join(tmp, 'list.txt'), files.map(f => `file '${f}'`).join('\n'));
  const j = spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'list.txt'), '-c', 'copy', '-movflags', '+faststart', out], { stdio: 'inherit' });
  if (j.status !== 0) { console.error('ffmpeg join failed'); process.exit(1); }
  log(`wrote ${out} (cloud, ${jobs.length} window(s))`); process.exit(0);
}


const browser = await launch();
const p = await browser.newPage();
p.on('pageerror', e => console.error('PAGEERR', e.message));
await p.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
await p.goto('file://' + path.resolve(page));
await p.waitForFunction('window.AgentFilm', { timeout: 60000 });
await p.evaluate(() => window.AgentFilm.ready);
log('ready');

const shot = async (ms, file, type = 'jpeg') => {
  await p.evaluate(t => window.AgentFilm.seek(t), ms);
  await p.screenshot({ path: file, type, ...(type === 'jpeg' ? { quality: 93 } : {}) });
};

const pngAt = opt('png-at');
if (pngAt !== undefined) {
  const out = typeof opt('out') === 'string' ? opt('out') : path.join(dir, `still-${pngAt}.png`);
  await shot(+pngAt, out, 'png'); log('still ' + out); await browser.close(); process.exit(0);
}

const frames = path.join(dir, 'frames'); fs.rmSync(frames, { recursive: true, force: true }); fs.mkdirSync(frames, { recursive: true });
const n = Math.ceil(meta.duration / 1000 * fps);
for (let i = 0; i < n; i++) {
  await shot(Math.min(meta.duration - 1, Math.round(i * 1000 / fps)), path.join(frames, String(i + 1).padStart(5, '0') + '.jpg'));
  if (i % 60 === 0) log(`frame ${i + 1}/${n}`);
}
if (argv.includes('--contact')) {
  for (let s = 0; s * 1000 < meta.duration; s++) await shot(s * 1000, path.join(frames, `c${String(s).padStart(3, '0')}.jpg`));
}
await browser.close();

const out = typeof opt('out') === 'string' ? opt('out') : path.join(dir, meta.slug + '.mp4');
const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-framerate', String(fps), '-i', path.join(frames, '%05d.jpg'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', out], { stdio: 'inherit' });
if (r.status !== 0) { console.error('ffmpeg failed'); process.exit(1); }
if (argv.includes('--contact')) {
  const cs = spawnSync('ffmpeg', ['-v', 'error', '-y', '-framerate', '1', '-i', path.join(frames, 'c%03d.jpg'), '-vf', 'scale=480:-1,tile=4x' + Math.ceil(meta.duration / 4000), '-frames:v', '1', path.join(dir, 'contact.jpg')], { stdio: 'inherit' });
}
log(`wrote ${out} (${n} frames at ${fps} fps, ${(meta.duration / 1000).toFixed(1)} s)`);
