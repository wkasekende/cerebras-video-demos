/* ── ONE PLACE THE BROWSER IS FOUND ───────────────────────────────────────────
   agent-film.mjs and check.mjs both drive a real Chrome through puppeteer-core.
   Where each comes from, in order:

     puppeteer        this folder's node_modules (`npm install` brings
                      `puppeteer`, which also downloads a Chrome for
                      Testing), then $DEMOKIT_PUPPETEER_DIR
     Chrome           $DEMOKIT_CHROME, then the Chrome puppeteer installed,
                      then the newest build under ~/.cache/puppeteer/chrome,
                      then a system chrome

   THE FLAGS ARE A SET. `--single-process --disable-gpu
   --disable-software-rasterizer` is what makes capture work under WSL2
   (Chrome's multi-process pipeline wedges there); they are harmless
   elsewhere, so they are always on. The raster flags keep typography
   identical from run to run. */
import fs from 'fs';
import os from 'os';
import path from 'path';
import { createRequire } from 'module';

export function loadPuppeteer() {
  const tries = [createRequire(import.meta.url)];
  const d = process.env.DEMOKIT_PUPPETEER_DIR;
  if (d && fs.existsSync(d)) tries.push(createRequire(path.join(d, 'package.json')));
  for (const r of tries) for (const name of ['puppeteer', 'puppeteer-core']) { try { return r(name); } catch {} }
  throw new Error('puppeteer not found: run `npm install` here, or set DEMOKIT_PUPPETEER_DIR to a folder that has it');
}

export function findChrome() {
  if (process.env.DEMOKIT_CHROME) return process.env.DEMOKIT_CHROME;
  try { const p = loadPuppeteer(); if (typeof p.executablePath === 'function') { const e = p.executablePath(); if (typeof e === 'string' && fs.existsSync(e)) return e; } } catch {}   /* newer puppeteers return a promise here; the cache scan below finds the same Chrome */
  const cache = path.join(os.homedir(), '.cache', 'puppeteer', 'chrome');
  if (fs.existsSync(cache)) {
    const builds = fs.readdirSync(cache).filter(n => /^(linux|mac|win)/.test(n)).sort().reverse();
    for (const b of builds) {
      for (const rel of ['chrome-linux64/chrome', 'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing', 'chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing', 'chrome-win64/chrome.exe']) {
        const p = path.join(cache, b, rel); if (fs.existsSync(p)) return p;
      }
    }
  }
  for (const p of ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']) if (fs.existsSync(p)) return p;
  throw new Error('no Chrome found: set DEMOKIT_CHROME, or run `npx puppeteer browsers install chrome`');
}

export const CHROME_ARGS = ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
  '--single-process', '--disable-gpu', '--disable-software-rasterizer',
  '--font-render-hinting=none', '--disable-font-subpixel-positioning', '--disable-lcd-text',
  '--force-color-profile=srgb', '--hide-scrollbars'];

export async function launch(extra) {
  const puppeteer = loadPuppeteer();
  return puppeteer.launch(Object.assign({ executablePath: findChrome(), headless: true, protocolTimeout: 60000, args: CHROME_ARGS }, extra || {}));
}
