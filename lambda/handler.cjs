'use strict';
/* ── THE RACE, RENDERED IN A LAMBDA: THE FUNCTION ────────────────────────────
   build.py runs locally and is fast; the expensive half, seeking a real
   Chrome through every frame, runs here. The payload carries the whole
   built page (self-contained: fonts, sheet, engine and timeline inline,
   ~300KB gzipped) and one window of the film; the mp4 comes back inline as
   base64. No S3 in the render path.

   event: { demokit: { page: base64(gzip(html)), assets?: { s3: 's3://bucket/key.tar.gz' }, job: { from, to, fps, scale, W, H, url, relaunchEvery } } }
   reply: { mp4: base64, log, driverSha }

   Chrome is @sparticuz/chromium on x86_64 (brotli-packed in the zip, it
   self-extracts to /tmp on first use), or the tarball DEMOKIT_CHROME_S3 names
   (s3://bucket/key holding chrome-linux/chrome, its lib/, and optionally an
   ffmpeg beside it) for any other build, arm64 included. ffmpeg is a static
   binary in /var/task/bin, or the tarball's. The fetch starts at module
   load: Lambda's init phase is free and overlaps provisioning. */
const fs = require('fs'), path = require('path'), zlib = require('zlib'), crypto = require('crypto');
const { execFile } = require('child_process');

let chromePath = null;
let chromeWarmup = null;

async function chromeFromS3(uri) {
  const dst = '/tmp/chrome-pack', bin = path.join(dst, 'chrome-linux', 'chrome');
  if (fs.existsSync(bin)) return bin;
  const m = uri.match(/^s3:\/\/([^/]+)\/(.+)$/);
  if (!m) throw new Error('DEMOKIT_CHROME_S3 wants s3://bucket/key, got ' + uri);
  const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');   // the runtime's bundled SDK
  const r = await new S3Client({}).send(new GetObjectCommand({ Bucket: m[1], Key: m[2] }));
  const chunks = [];
  for await (const c of r.Body) chunks.push(c);
  untar(zlib.gunzipSync(Buffer.concat(chunks)), dst);
  return bin;
}

/* pure node: the runtime ships no tar binary. GNU long names ride 'L'
   entries; symlinks matter (chromium's .so links); pax headers skip. */
function untar(buf, dst) {
  fs.mkdirSync(dst, { recursive: true });
  let off = 0, longName = null;
  while (off + 512 <= buf.length) {
    const hdr = buf.subarray(off, off + 512); off += 512;
    if (!hdr.some(b => b)) continue;
    let name = longName || hdr.toString('utf8', 0, 100).replace(/\0.*$/, '');
    longName = null;
    const prefix = hdr.toString('utf8', 345, 500).replace(/\0.*$/, '');
    if (prefix) name = prefix + '/' + name;
    const size = parseInt(hdr.toString('utf8', 124, 136).trim(), 8) || 0;
    const type = String.fromCharCode(hdr[156]);
    const body = buf.subarray(off, off + size);
    off += Math.ceil(size / 512) * 512;
    if (type === 'L') { longName = body.toString('utf8').replace(/\0.*$/, ''); continue; }
    if (type === 'x' || type === 'g') continue;
    const p2 = path.join(dst, name);
    if (type === '5') { fs.mkdirSync(p2, { recursive: true }); continue; }
    if (type === '2') {
      fs.mkdirSync(path.dirname(p2), { recursive: true });
      try { fs.symlinkSync(hdr.toString('utf8', 157, 257).replace(/\0.*$/, ''), p2); } catch (e) { /* exists */ }
      continue;
    }
    if (type === '0' || type === '\0' || type === '') {
      fs.mkdirSync(path.dirname(p2), { recursive: true });
      fs.writeFileSync(p2, body);
      const mode = parseInt(hdr.toString('utf8', 100, 108).trim(), 8);
      if (mode) fs.chmodSync(p2, mode & 0o777);
    }
  }
}

async function fetchAssets(uri, dst) {
  const m = uri.match(/^s3:\/\/([^/]+)\/(.+)$/);
  if (!m) throw new Error('assets.s3 wants s3://bucket/key, got ' + uri);
  const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');   // the runtime's bundled SDK
  const r = await new S3Client({}).send(new GetObjectCommand({ Bucket: m[1], Key: m[2] }));
  const chunks = [];
  for await (const c of r.Body) chunks.push(c);
  untar(zlib.gunzipSync(Buffer.concat(chunks)), dst);
}

function acquireChrome() {
  return (process.env.DEMOKIT_CHROME_S3
    ? chromeFromS3(process.env.DEMOKIT_CHROME_S3)
    : require('@sparticuz/chromium').executablePath()).then(p => (chromePath = p));
}
chromeWarmup = acquireChrome();
chromeWarmup.catch(() => { chromeWarmup = null; });   /* a failed init fetch retries in the handler */

async function runRace(ev) {
  if (!chromeWarmup) chromeWarmup = acquireChrome();
  if (!chromePath) await chromeWarmup;
  const work = '/tmp/race';
  fs.rmSync(work, { recursive: true, force: true });
  fs.mkdirSync(work, { recursive: true });
  fs.writeFileSync(path.join(work, 'page.html'), zlib.gunzipSync(Buffer.from(ev.page, 'base64')));
  if (ev.assets && ev.assets.s3) await fetchAssets(ev.assets.s3, work);   /* a .tar.gz of files the page references by relative path (an agent film's pop-in frames): too big for the 6 MB invoke payload, so it rides in S3 */
  const job = { ...ev.job, work, out: path.join(work, 'seg.mp4') };
  fs.writeFileSync(path.join(work, 'job.json'), JSON.stringify(job));
  const env = { ...process.env,
    DEMOKIT_CHROME: chromePath,
    DEMOKIT_PPTR: '/var/task/node_modules/puppeteer-core',
    HOME: '/tmp',
    PATH: '/tmp/chrome-pack:/var/task/bin:' + process.env.PATH,
    ...(process.env.DEMOKIT_CHROME_S3 ? {
      LD_LIBRARY_PATH: '/tmp/chrome-pack/lib:' + (process.env.LD_LIBRARY_PATH || ''),
      FONTCONFIG_PATH: '/tmp/chrome-pack/etc' } : {}) };
  const log = await new Promise((resolve, reject) => {
    execFile('node', ['/var/task/demokit-render.cjs', path.join(work, 'job.json')],
      { env, maxBuffer: 64 * 1024 * 1024, timeout: 280000 },
      (e, so, se) => e ? reject(new Error(String(se || '') + String(so || '') + e.message))
                       : resolve(String(so) + String(se)));
  });
  const driverSha = crypto.createHash('sha256')
    .update(fs.readFileSync('/var/task/demokit-render.cjs')).digest('hex').slice(0, 16);
  return { mp4: fs.readFileSync(job.out).toString('base64'), log, driverSha };
}

exports.handler = async (event) => {
  const job = event && (event.demokit || event.race);   /* `race` was the key before the rename of 2026-09-14; a agent-film.mjs from before it still works */
  if (job) return runRace(job);
  throw new Error('payload wants { demokit: { page: base64(gzip(html)), job: { from, to, fps, scale, W, H, url } } }');
};
