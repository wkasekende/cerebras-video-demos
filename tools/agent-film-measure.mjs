#!/usr/bin/env node
/* ── THE MEASURE PASS ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
     node tools/agent-film-measure.mjs out/agent-film/<slug>/film.html      prints JSON on stdout

   Layout is DERIVED, not typed in: artifact/agent_film.py builds the page, this tool loads it in a real Chrome and MEASURES what the layout depends on, and the builder builds again with the numbers
   (agent_film.py main(): build, measure, build, measure, and it refuses unless the two measurements agree). What is measured, per scene index i (all in the pointer's own container's pixels):
     typing:i       text_h (the typed prompt's full height, so the composer can be as tall as its text needs), tx, ty (the send button's click target)
     second-turn:i  tx, ty (the docked composer's send button)
     browse:i:j     tx, ty (page j's button, in flow after its lines, wherever they wrap)
     answer:i       bottom (the answer card's last line), comp_top (the docked composer's top): the card must end above the composer
   The click target is the button's own rectangle at 78% across and 62% down, as the comparison layout's engine measures its send button. */
import path from 'path';
import { launch } from './chrome.mjs';

const page = process.argv[2];
if (!page) { console.error('usage: agent-film-measure.mjs <film.html>'); process.exit(2); }
const browser = await launch();
const p = await browser.newPage();
await p.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
await p.goto('file://' + path.resolve(page));
await p.waitForFunction('window.AgentFilm', { timeout: 60000 });
await p.evaluate(() => window.AgentFilm.ready);
const seek = t => p.evaluate(t => window.AgentFilm.seek(t), t);
const scenes = await p.evaluate(() => window.AgentFilm.scenes.map((s, i) => ({ i, kind: document.querySelectorAll('.scene')[i].dataset.kind, start: s.start, ms: s.ms })));
const out = {};
const r1 = v => Math.round(v * 10) / 10;
const target = (sel, scope) => `(() => { const sc = ${scope}, send = sc.querySelector('${sel}'), ptr = (send.closest('[data-show-from], .scene')).querySelector('.ag-pointer'), par = ptr.parentElement.getBoundingClientRect(), sr = send.getBoundingClientRect(); return { tx: sr.left - par.left + sr.width * 0.78, ty: sr.top - par.top + sr.height * 0.62 }; })()`;
for (const s of scenes) {
  if (s.kind === 'typing' || s.kind === 'second-turn') {
    const tm = await p.evaluate(i => +document.querySelectorAll('.scene')[i].querySelector('[data-type]').dataset.typeMs, s.i);
    await seek(s.start + 250 + tm + 20);
    const m = await p.evaluate(i => { const sc = document.querySelectorAll('.scene')[i], send = sc.querySelector('[data-send]'), ptr = sc.querySelector('.ag-pointer'), par = ptr.parentElement.getBoundingClientRect(), sr = send.getBoundingClientRect(), txt = sc.querySelector('.ag-text');
      return { text_h: txt.scrollHeight, tx: sr.left - par.left + sr.width * 0.78, ty: sr.top - par.top + sr.height * 0.62 }; }, s.i);
    out[`${s.kind}:${s.i}`] = { text_h: m.text_h, tx: r1(m.tx), ty: r1(m.ty) };
  }
  if (s.kind === 'browse') {
    const pages = await p.evaluate(i => [...document.querySelectorAll('.scene')[i].querySelectorAll('[data-show-from]')].map((e, j) => ({ j, from: +e.dataset.showFrom, to: +e.dataset.showTo, has: !!e.querySelector('.ag-pointer') })).filter(x => x.has), s.i);
    for (const pg of pages) {
      await seek(s.start + pg.from + 30);
      const m = await p.evaluate(({ i, from }) => { const w = [...document.querySelectorAll('.scene')[i].querySelectorAll('[data-show-from]')].find(e => +e.dataset.showFrom === from && e.querySelector('.ag-pointer')), send = w.querySelector('[data-send]'), ptr = w.querySelector('.ag-pointer'), par = ptr.parentElement.getBoundingClientRect(), sr = send.getBoundingClientRect();
        return { tx: sr.left - par.left + sr.width * 0.78, ty: sr.top - par.top + sr.height * 0.62 }; }, { i: s.i, from: pg.from });
      out[`browse:${s.i}:${pg.from}`] = { tx: r1(m.tx), ty: r1(m.ty) };
    }
  }
  if (s.kind === 'intro') {
    await seek(s.start + s.ms - 300);
    const m = await p.evaluate(i => { const sc = document.querySelectorAll('.scene')[i], vis = [...sc.querySelectorAll('.ag-claim-f, .ag-claim-h, [data-reveal]')].filter(e => !e.classList.contains('rv-off') && !e.closest('.rv-off')); return { bottom: Math.max(0, ...vis.map(e => e.getBoundingClientRect().bottom)), width: Math.max(0, ...vis.map(e => e.getBoundingClientRect().width)) }; }, s.i);
    out[`intro:${s.i}`] = { bottom: r1(m.bottom), width: r1(m.width) };
  }
  if (s.kind === 'claim') {
    await seek(s.start + s.ms - 300);
    const m = await p.evaluate(i => { const sc = document.querySelectorAll('.scene')[i], hs = [...sc.querySelectorAll('.ag-claim-h, .ag-claim-l, .ag-claim-f')], tw = e => { const r = document.createRange(); r.selectNodeContents(e); return r.getBoundingClientRect().width; }; return { width: Math.max(0, ...hs.map(tw)), bottom: Math.max(0, ...hs.map(e => e.getBoundingClientRect().bottom)) }; }, s.i);   /* the width of the TEXT (the elements are full-width boxes) */
    out[`claim:${s.i}`] = { width: r1(m.width), bottom: r1(m.bottom) };
  }
  if (s.kind === 'answer') {
    await seek(s.start + s.ms - 700);
    const m = await p.evaluate(i => { const sc = document.querySelectorAll('.scene')[i], foots = [...sc.querySelectorAll('.ag-foot')].filter(e => !e.classList.contains('rv-off')), last = foots[foots.length - 1] || sc.querySelector('.ag-order'), comp = sc.querySelector('.ag-composer');
      return { bottom: last.getBoundingClientRect().bottom, comp_top: comp.getBoundingClientRect().top }; }, s.i);
    out[`answer:${s.i}`] = { bottom: r1(m.bottom), comp_top: r1(m.comp_top) };
  }
}
await browser.close();
console.log(JSON.stringify(out));
