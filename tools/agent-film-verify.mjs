#!/usr/bin/env node
/* ── DETERMINISTIC CHECKS FOR A BUILT AGENT FILM ──────────────────────────────────────────────────────────────────
     node tools/agent-film-verify.mjs out/agent-film/<slug>/film.html

   No eye involved: every rule is a number or an equality, and any failure exits non-zero. The checks, in order:
     1  the page's scenes are film.json's scenes, in order, with the same times
     2  every scene change is one the state machine allows and is drawn the way it declares (film.json "transitions")
     3  DETERMINISM: a moment painted, then another, then the first again, gives byte-identical screenshots (the page reads no clock)
     4  at the middle of every scene exactly that scene is visible
     5  ONE LOADER: at every sampled moment at most one spinner is on screen (exactly one in a `turn` scene, none elsewhere)
     6  NO LOGO SPINS: nothing inside a Cerebras mark or a brand logo is animated
     7  NO AUDIO STATES: no microphone icon anywhere in the film (the film has no audio)
     8  DIALS: every counting number reads 0 as it appears and its final text once it has finished
     9  MORPH: at its start the card is the composer's rectangle, at its end the target's, and in between it is monotone in size
    10  STREAMED TEXT: each element is hidden before its start, shows a never-shrinking number of words, and shows all of them when its time is up
    11  THREADS: the conversation's scroll never moves back, and at the end the newest message is inside the view
    16  THE MOUSE AND THE BUTTONS: the disabled-then-active send button, the pointer's glide to the click, the press, the caret that stops, the ticking counters, the optional timer and attachment
    15  THE MATHS: a lane's time is tokens / tps to the ms, the token count and the rendered words follow it, the pill reads it, the lanes' times are in the ratio of their rates
    14  TRANSITIONS: a morph shows none of the target's contents (the title bar lights first) until the card has landed; the DONE cards leave on a fixed schedule
    13  PROGRESSIVE: nothing takes room before it begins (a message, a bullet and its marker, a footer); a streamed box is short at its first word, grows, and never shrinks
    12  VERSUS: the Cerebras lane is at least 1,000 tokens a second, finishes before the GPU lane, has counted every token and says Done when it does
   Exit 0 = every check held. */
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { launch } from './chrome.mjs';

const page = process.argv[2];
if (!page) { console.error('usage: agent-film-verify.mjs <film.html>'); process.exit(2); }
const dir = path.dirname(path.resolve(page));
const meta = JSON.parse(fs.readFileSync(path.join(dir, 'film.json'), 'utf8'));
const fails = []; let checks = 0;
const ok = (cond, msg) => { checks++; if (!cond) fails.push(msg); };
const sha = b => crypto.createHash('sha256').update(b).digest('hex').slice(0, 16);

const browser = await launch();
const p = await browser.newPage();
p.on('pageerror', e => fails.push('page error: ' + e.message));
await p.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
await p.goto('file://' + path.resolve(page));
await p.waitForFunction('window.AgentFilm', { timeout: 60000 });
await p.evaluate(() => window.AgentFilm.ready);
const seek = t => p.evaluate(t => window.AgentFilm.seek(t), t);

/* 1 */
const sc = await p.evaluate(() => window.AgentFilm.scenes);
ok(sc.length === meta.scenes.length, `1: the page has ${sc.length} scenes, film.json ${meta.scenes.length}`);
meta.scenes.forEach((m, i) => ok(sc[i] && sc[i].kind === m.scene && sc[i].start === m.start && sc[i].ms === m.ms, `1: scene ${i} differs between the page and film.json`));
ok(meta.scenes.reduce((a, s) => a + s.ms, 0) === meta.duration, '1: the scenes do not add up to the duration');

/* 2: the transitions film.json declares are exactly what the page draws */
const MORPH_FROM = ['typing'], MORPH_TO = ['welcome', 'turn', 'answer', 'thread', 'versus', 'popin'];
const morphs = await p.evaluate(() => [...document.querySelectorAll('.scene')].map(s => s.hasAttribute('data-morph')));
const cuts = await p.evaluate(() => [...document.querySelectorAll('.scene')].map(s => s.hasAttribute('data-cut')));
meta.transitions.forEach((t, k) => {
  const i = k + 1, want = MORPH_FROM.includes(t.from) && MORPH_TO.includes(t.to) ? 'morph' : cuts[i] ? 'cut' : 'crossfade';
  ok(t.how === want, `2: transition ${t.from} -> ${t.to} is declared ${t.how}, the rule says ${want}`);
  ok(morphs[i] === (t.how === 'morph'), `2: scene ${i} (${t.to}) is ${morphs[i] ? '' : 'not '}marked to morph, film.json says ${t.how}`);
  ok(t.at === meta.scenes[i].start, `2: transition ${i} is at ${t.at}, the scene starts at ${meta.scenes[i].start}`);
});

/* 3: determinism. (a) the page's STATE is a pure function of the time: every element's inline style, every counting or typed text, every animation's clock and the morph card, serialised, are identical
   whichever moment was painted before. (b) the PIXELS agree: headless Chrome's text anti-aliasing can flip a few dozen pixels between two paints of identical state (seen 2026-11-19: 28 to 30 px of
   one footer chip), so the screenshots may differ, by more than PIXEL_NOISE levels, in at most AA_PIXELS pixels, each by at most AA_DELTA; anything more is a real difference. */
const AA_PIXELS = 80, AA_DELTA = 90, PIXEL_NOISE = 3;   /* a difference of 3 levels of 255 or less is rasterisation noise (seen in the ember theme: 156 pixels off by 1 or 2 where a perspective-transformed card is drawn) and is not counted */
const moments = new Set();
meta.scenes.forEach(s => { moments.add(s.start + Math.round(s.ms / 2)); moments.add(s.start + 200); });
meta.transitions.forEach(t => { moments.add(t.at - 100); moments.add(t.at + 300); moments.add(t.at + 650); });
const ts = [...moments].filter(t => t >= 0 && t < meta.duration).sort((a, b) => a - b);
const stateSig = () => p.evaluate(() => {
  const parts = [];
  document.querySelectorAll('.scene').forEach((sc, i) => { parts.push(i + ':' + sc.style.opacity); sc.querySelectorAll('*').forEach(e => { if (e.style && e.style.cssText) parts.push(e.style.cssText.split(';').map(x => x.trim()).filter(Boolean).sort().join(';'));   /* cssText, not the attribute: setting a property and resetting it re-serialises the attribute without changing the style */ if (e.hasAttribute && (e.hasAttribute('data-count') || e.hasAttribute('data-type'))) parts.push(e.textContent); if (e.hasAttribute && e.hasAttribute('data-popin')) parts.push(e.getAttribute('src')); }); });
  parts.push(document.getAnimations().map(a => a.animationName + '@' + Math.round(a.currentTime * 1000) / 1000).sort().join('|'));   /* sorted: the list's order depends on history, the set does not */
  parts.push(window.AgentFilm.morph.card.style.cssText.split(';').map(x => x.trim()).filter(Boolean).sort().join(';'));
  return parts;
});
const pixelDiff = async (a, b) => p.evaluate(async (a, b, noise) => {
  const load = src => new Promise(r => { const i = new Image(); i.onload = () => r(i); i.src = 'data:image/png;base64,' + src; });
  const [ia, ib] = await Promise.all([load(a), load(b)]); const c = document.createElement('canvas'); c.width = ia.width; c.height = ia.height; const x = c.getContext('2d');
  x.drawImage(ia, 0, 0); const da = x.getImageData(0, 0, c.width, c.height).data; x.clearRect(0, 0, c.width, c.height); x.drawImage(ib, 0, 0); const db = x.getImageData(0, 0, c.width, c.height).data;
  let n = 0, mx = 0; for (let k = 0; k < da.length; k += 4) { const d = Math.max(Math.abs(da[k] - db[k]), Math.abs(da[k + 1] - db[k + 1]), Math.abs(da[k + 2] - db[k + 2])); if (d > noise) { n++; if (d > mx) mx = d; } } return { n, mx };
}, a, b, PIXEL_NOISE);
const snap = async t => { await seek(t); return { parts: await stateSig(), png: (await p.screenshot({ type: 'png' })).toString('base64') }; };
const first = {};
for (const t of ts) first[t] = await snap(t);
await seek(0);
for (const t of [...ts].reverse()) {
  const again = await snap(t);
  { const A = first[t].parts, B = again.parts, k = A.findIndex((x, i) => x !== B[i]); ok(k < 0 && A.length === B.length, `3a: the page's state at ${t} ms depends on what was painted before it: entry ${k} was [${String(A[k]).slice(0, 90)}] then [${String(B[k]).slice(0, 90)}]`); }
  if (again.png !== first[t].png) { const d = await pixelDiff(first[t].png, again.png); ok(d.n <= AA_PIXELS && d.mx <= AA_DELTA, `3b: ${t} ms painted two frames that differ in ${d.n} pixels (by up to ${d.mx}); the anti-aliasing allowance is ${AA_PIXELS} px by ${AA_DELTA}`); }
}

/* 4 + 5 + 6 + 7 over the sampled moments */
const visibleScenes = () => p.evaluate(() => window.AgentFilm.opacities());
const loaders = () => p.evaluate(() => {
  const vis = e => { for (let n = e; n && n !== document.body; n = n.parentElement) { const cs = getComputedStyle(n); if (+cs.opacity === 0 || cs.display === 'none' || cs.visibility === 'hidden') return false; } return true; };
  return [...document.querySelectorAll('.ag-spin')].filter(vis).length;
});
for (const s of meta.scenes) {
  const mid = s.start + Math.round(s.ms / 2);
  await seek(mid);
  const ops = await visibleScenes(), idx = meta.scenes.indexOf(s);
  ops.forEach((o, i) => ok((i === idx) === (o > 0), `4: at ${mid} ms (middle of scene ${idx}, ${s.scene}) scene ${i} has opacity ${o}`));
  const n = await loaders();
  ok(s.scene === 'turn' ? n === 1 : ['ask', 'second-turn'].includes(s.scene) ? n <= 1 : n === 0, `5: ${n} spinner(s) on screen in a ${s.scene} scene (a turn has exactly one, an ask or a second turn at most one, every other scene none)`);
}
for (const t of ts) { await seek(t); const n = await loaders(); ok(n <= 1, `5: ${n} spinners on screen at ${t} ms`); }
const bad = await p.evaluate(() => {
  const out = [];
  document.getAnimations().forEach(a => { const el = a.effect && a.effect.target; if (el && el.closest && el.closest('.ag-mark, .ag-logo')) out.push(el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className); });
  document.querySelectorAll('.ag-spin').forEach(e => { if (e.querySelector('.ag-mark, .ag-logo')) out.push('a spinner wraps a logo'); });
  return out;
});
ok(bad.length === 0, `6: ${bad.length} animated logo element(s): ${bad.slice(0, 3).join(', ')}`);
const mics = await p.evaluate(() => [...document.querySelectorAll('svg')].filter(s => (s.innerHTML || '').includes('M5 11a7 7 0 0014 0')).length);
ok(mics === 0, `7: ${mics} microphone icon(s) in a film with no audio`);

/* 8: dials */
const dials = await p.evaluate(() => [...document.querySelectorAll('[data-count]')].map(e => ({ i: [...document.querySelectorAll('.scene')].indexOf(e.closest('.scene')), finalText: e.textContent, count: +e.getAttribute('data-count'), dec: +(e.getAttribute('data-dec') || 0), delay: +(e.getAttribute('data-delay') || 350), dur: +(e.getAttribute('data-dur') || 1500), k: [...document.querySelectorAll('[data-count]')].indexOf(e) })));
ok(dials.length > 0, '8: there are no counting numbers in this film');
for (const d of dials) {
  const s = meta.scenes[d.i]; if (!s) continue;
  await seek(s.start + Math.max(0, d.delay - 20));
  const at0 = await p.evaluate(k => document.querySelectorAll('[data-count]')[k].textContent, d.k);
  ok(+at0.replace(/,/g, '') === 0, `8: a number in scene ${d.i} reads ${at0} just before it starts to count (should be 0)`);
  await seek(Math.min(meta.duration - 1, s.start + d.delay + d.dur + 60));
  const end = await p.evaluate(k => document.querySelectorAll('[data-count]')[k].textContent, d.k);
  const want = d.count.toLocaleString('en-US', { minimumFractionDigits: d.dec, maximumFractionDigits: d.dec });
  ok(end === want || s.start + d.delay + d.dur + 60 >= s.start + s.ms, `8: a number in scene ${d.i} ends at ${end}, expected ${want}`);
}

/* 9: morph geometry */
const geo = await p.evaluate(() => {
  const m = window.AgentFilm.morph, out = [];
  window.AgentFilm.scenes.forEach((s, i) => { const el = document.querySelectorAll('.scene')[i]; if (!el.hasAttribute('data-morph')) return; out.push({ i, start: s.start, src: i - 1 }); });
  return { ms: m.ms, pre: m.pre, land: m.land, exit: m.exit, list: out };
});
for (const g of geo.list) {
  const rects = async t => { await seek(t); return p.evaluate(({ i, src }) => {
    const sc = document.querySelectorAll('.scene'), a = sc[src].querySelector('.ag-composer').getBoundingClientRect(), b = sc[i].querySelector('.ag-window, .popin-card').getBoundingClientRect(), c = window.AgentFilm.morph.card;
    const r = c.getBoundingClientRect(); return { a: [a.left, a.top, a.width, a.height], b: [b.left, b.top, b.width, b.height], c: [r.left, r.top, r.width, r.height], on: c.style.display !== 'none' };
  }, g); };
  const t0 = g.start - geo.pre, near = (x, y, tol) => x.every((v, k) => Math.abs(v - y[k]) <= tol);
  const r0 = await rects(t0 + 12), r1 = await rects(t0 + geo.ms - 12), rm = await rects(t0 + geo.ms / 2);
  ok(r0.on && near(r0.c, r0.a, 3), `9: at the start of the morph into scene ${g.i} the card is [${r0.c.map(Math.round)}], the composer [${r0.a.map(Math.round)}]`);
  ok(r1.on && near(r1.c, r1.b, 3), `9: at the end of the morph into scene ${g.i} the card is [${r1.c.map(Math.round)}], the target [${r1.b.map(Math.round)}]`);
  ok(rm.c[2] > r0.c[2] && rm.c[2] < r1.c[2] || rm.c[2] > r1.c[2] && rm.c[2] < r0.c[2] || Math.abs(r0.c[2] - r1.c[2]) < 4, `9: the card's width is not between its start and end in the middle of the morph into scene ${g.i}`);
  await seek(t0 - 20); const opsBefore = await visibleScenes();
  ok(opsBefore[g.i] === 0, `9: scene ${g.i} is already visible (opacity ${opsBefore[g.i]}) before its morph starts: a morph scene must not fade in`);
  const after = await rects(t0 + geo.ms + 40);
  ok(!after.on, `9: the morph card is still on screen after the morph into scene ${g.i}`);
}

/* 14: TRANSITIONS ARE CONTRACTS, NOT TIMING LUCK. (a) In a morph the target's contents (its title bar and the three lights above all) are fully invisible until the card has LANDED on the target's rectangle, and none is visible while the card is more than 3 px from it. (b) A scene's overlays leave on schedule: the DONE cards are fully up until the crossfade out of their scene begins and fully gone EXIT ms into it */
const MORPH_LAND = geo.land ?? 0.8;
for (const g of geo.list) {
  const t0 = g.start - geo.pre;
  for (let q = 1; q <= 24; q++) {
    const pq = q / 25; await seek(t0 + pq * geo.ms);
    const r = await p.evaluate(({ i }) => { const dst = document.querySelectorAll('.scene')[i].querySelector('.ag-window, .popin-card'), c = window.AgentFilm.morph.card.getBoundingClientRect(), b = dst.getBoundingClientRect();
      const kids = [...dst.children].map(k => +getComputedStyle(k).opacity), lights = dst.querySelector('.ag-lights'); let lo = 1, e = lights; while (e && e !== dst.parentNode) { lo = Math.min(lo, +getComputedStyle(e).opacity); e = e.parentElement; }
      return { vis: Math.max(0, ...kids), lights: lights ? Math.min(lo, 1) : 0, off: Math.max(Math.abs(c.left - b.left), Math.abs(c.top - b.top), Math.abs(c.width - b.width), Math.abs(c.height - b.height)) }; }, g);
    if (pq < MORPH_LAND - 0.02) ok(r.vis === 0, `14: scene ${g.i}: ${r.vis.toFixed(2)} of the target's contents is visible at ${Math.round(pq * 100)}% of the morph, before the card has landed (${MORPH_LAND * 100}%)`);
    if (r.vis > 0.02) ok(r.off <= 3, `14: scene ${g.i}: the target's contents show (${r.vis.toFixed(2)}) while the card is ${Math.round(r.off)} px from the target's rectangle at ${Math.round(pq * 100)}%`);
  }
}
const FADE = meta.fade_ms ?? 450, EXIT = geo.exit ?? 150;
for (const [i, m] of meta.scenes.entries()) {
  if (m.scene !== 'versus' || i === meta.scenes.length - 1) continue;
  const doneOps = async t => { await seek(t); return p.evaluate(i => [...document.querySelectorAll('.scene')[i].querySelectorAll('.versus-done')].map(e => e.style.visibility === 'hidden' ? 0 : +e.style.opacity), i); };
  const up = await doneOps(m.start + m.ms - FADE - 5), gone = await doneOps(m.start + m.ms - FADE + EXIT + 5);
  ok(up.every(v => v === 1), `14: scene ${i}: the DONE cards are ${up} just before the crossfade out begins (all fully up)`);
  ok(gone.every(v => v === 0), `14: scene ${i}: the DONE cards are ${gone} ${EXIT} ms into the crossfade out (all gone)`);
}

const ft = (o, t) => o.ff && t > o.ffAt ? Math.round(o.ffAt + (t - o.ffAt) / o.ff) : t;   /* a fast-forwarded lane's own clock to film time */
/* 16: THE MOUSE, THE CLICK AND THE BUTTONS: the same for every theme and every storyboard. In each typing scene the send button is the disabled grey until the first character; the pointer is not there before its start, is ON the send button at the click, the button is pressed (scale .86) for exactly the press and not before or after, the caret stops at the click, and the pointer has gone shortly after. "Preparing this turn" ticks (1s, then 3s two and a half seconds on). The optional timer counts and then stops; the optional attachment slides in and then rides in the bubble */
const PRESS = 140;
for (const [i, m] of meta.scenes.entries()) {
  const st = m.start;
  if (m.scene === 'typing') {
    const click = m.ms - 300, from = click - 700;
    const q = async t => { await seek(st + t); return p.evaluate(i => { const sc = document.querySelectorAll('.scene')[i], ptr = sc.querySelector('.ag-pointer'), snd = sc.querySelector('[data-send]'), car = sc.querySelector('[data-caret-until]'), pr = ptr.getBoundingClientRect(), sr = snd.getBoundingClientRect();
      return { pd: ptr.style.display, po: +ptr.style.opacity, tipx: pr.left + 2.6, tipy: pr.top + 2, tx: sr.left + sr.width * 0.78, ty: sr.top + sr.height * 0.62, off: snd.classList.contains('off'), tf: snd.style.transform, caret: car.style.visibility }; }, i); };
    const a = await q(200), b = await q(from - 1), c = await q(click - 1), d = await q(click + 10), e = await q(click + PRESS + 20), f = await q(click + PRESS + 400), g = await q(Math.round((250 + from) / 2));
    ok(a.off && !g.off, `16: scene ${i}: the send button is the disabled grey before the first character (${a.off}) and active while typing (${!g.off})`);
    ok(b.pd === 'none' || b.po === 0, `16: scene ${i}: the pointer is already on screen at ${from - 1} ms, before its start`);
    ok(c.po > 0.99 && Math.abs(c.tipx - c.tx) <= 4 && Math.abs(c.tipy - c.ty) <= 4, `16: scene ${i}: at the click the pointer's tip is ${Math.round(c.tipx - c.tx)}, ${Math.round(c.tipy - c.ty)} px from the send button's target (opacity ${c.po})`);
    ok(c.tf === 'scale(1)' && d.tf === 'scale(0.86)' && e.tf === 'scale(1)', `16: scene ${i}: the press is ${c.tf} before the click, ${d.tf} at it, ${e.tf} ${PRESS + 20} ms after`);
    ok(c.caret === '' && d.caret === 'hidden', `16: scene ${i}: the caret stops at the click (before: "${c.caret}", after: "${d.caret}")`);
    ok(f.po === 0 || f.pd === 'none', `16: scene ${i}: the pointer is still there ${PRESS + 400} ms after the click`);
  }
  const el = await p.evaluate(i => document.querySelectorAll('.scene')[i].querySelectorAll('[data-elapsed]').length, i);
  if (el) { const fr = await p.evaluate(i => +(document.querySelectorAll('.scene')[i].querySelector('[data-elapsed]').dataset.from || 0), i); await seek(st + fr + 5); const t0 = await p.evaluate(i => document.querySelectorAll('.scene')[i].querySelector('[data-elapsed]').textContent, i); await seek(Math.min(meta.duration - 1, st + fr + 2500)); const t1 = await p.evaluate(i => document.querySelectorAll('.scene')[i].querySelector('[data-elapsed]').textContent, i);
    ok(t0 === '1s' && t1 === '3s', `16: scene ${i}: the elapsed counter reads ${t0} then ${t1} (1s then 3s)`); }
}
const tm = await p.evaluate(() => { const e = document.querySelector('[data-timer]'); return e ? { f: +e.dataset.from, st: +e.dataset.stop } : null; });
if (tm) {
  const read = async t => { await seek(t); return p.evaluate(() => [...document.querySelectorAll('[data-timer]')].map(e => e.textContent)); };
  const r0 = await read(tm.f), r1 = await read(tm.f + 2000), r2 = await read(tm.st), r3 = await read(Math.min(meta.duration - 1, tm.st + 600));
  ok(r0.every(x => x === '0.0s') && r1.every(x => x === '2.0s'), `16: the timer pill reads ${r0[0]} at the first turn and ${r1[0]} two seconds on`);
  ok(r2.every(x => x === ((tm.st - tm.f) / 1000).toFixed(1) + 's') && r3.every(x => x === r2[0]), `16: the timer stops at ${((tm.st - tm.f) / 1000).toFixed(1)}s where the answer begins (${r2[0]}, then ${r3[0]})`);
}
const att = await p.evaluate(() => ({ stack: [...document.querySelectorAll('.att-stack')].map(e => ({ i: [...document.querySelectorAll('.scene')].indexOf(e.closest('.scene')), from: +e.dataset.slideFrom, ms: +e.dataset.slideMs })), cards: document.querySelectorAll('.att-card').length }));
for (const a of att.stack) {
  const m = meta.scenes[a.i];
  await seek(m.start + a.from - 1); const o0 = await p.evaluate(i => +document.querySelectorAll('.scene')[i].querySelector('.att-stack').style.opacity, a.i);
  await seek(m.start + a.from + a.ms + 20); const o1 = await p.evaluate(i => ({ o: +document.querySelectorAll('.scene')[i].querySelector('.att-stack').style.opacity, t: document.querySelectorAll('.scene')[i].querySelector('.att-stack').style.transform }), a.i);
  ok(o0 === 0 && o1.o === 1 && /translateX\(0px\) rotate\(0deg\)/.test(o1.t), `16: the attachment stack is hidden before it slides (${o0}) and in place after (${o1.o}, ${o1.t})`);
}
ok(att.stack.length === 0 || att.cards > 0, '16: an attachment is in the typing scene but never reaches the conversation (no card)');
ok(att.stack.length > 0 || att.cards === 0, '16: an attachment card is drawn although the storyboard has no attachment (it is optional: absent, nothing is drawn)');

/* 10: streamed text */
const reveals = await p.evaluate(() => [...document.querySelectorAll('[data-reveal]')].map((e, k) => ({ k, i: [...document.querySelectorAll('.scene')].indexOf(e.closest('.scene')), delay: +e.getAttribute('data-reveal-delay'), dur: +e.getAttribute('data-reveal-ms'), n: e.querySelectorAll('.w').length, ff: +((e.closest('[data-ff]') || {dataset:{}}).dataset.ff || 0), ffAt: +((e.closest('[data-ff]') || {dataset:{}}).dataset.ffAt || 0) })));
const wordsShown = k => p.evaluate(k => { const e = document.querySelectorAll('[data-reveal]')[k]; return { hidden: e.classList.contains('rv-off') || !!e.closest('.rv-off'), shown: [...e.querySelectorAll('.w')].filter(w => !w.classList.contains('rv-off')).length }; }, k);
for (const r of reveals) {
  const s = meta.scenes[r.i];
  await seek(s.start + Math.max(0, ft(r, r.delay) - 1));
  const a = await wordsShown(r.k);
  ok(r.delay === 0 || (a.hidden && a.shown === 0), `10: streamed text ${r.k} (scene ${r.i}) is visible (${a.shown} words) before its start at ${r.delay} ms`);
  let last = -1;
  for (let f = 0; f <= 4; f++) { await seek(s.start + ft(r, r.delay + Math.round(r.dur * f / 4))); const w = await wordsShown(r.k); ok(w.shown >= last, `10: streamed text ${r.k} lost words (${last} then ${w.shown})`); last = w.shown; }
  await seek(Math.min(meta.duration - 1, s.start + ft(r, r.delay + r.dur + 40)));
  const z = await wordsShown(r.k);
  ok(z.shown === r.n || s.start + ft(r, r.delay + r.dur + 40) >= s.start + s.ms, `10: streamed text ${r.k} shows ${z.shown} of its ${r.n} words when its time is up`);
}

/* 13: PROGRESSIVE COMPONENTS. Nothing is drawn empty and waiting for its text: a component (a message, a bullet with its marker, a footer) takes no room before it begins; a streamed box is as tall as the words RENDERED so far, so one word in it is far shorter than all of them; and its height never shrinks while it streams */
const apps = await p.evaluate(() => [...document.querySelectorAll('[data-appear]')].map((e, k) => ({ k, i: [...document.querySelectorAll('.scene')].indexOf(e.closest('.scene')), at: +e.getAttribute('data-appear'), ff: +((e.closest('[data-ff]') || {dataset:{}}).dataset.ff || 0), ffAt: +((e.closest('[data-ff]') || {dataset:{}}).dataset.ffAt || 0) })));
for (const a of apps) {
  const s = meta.scenes[a.i];
  await seek(s.start + Math.max(0, ft(a, a.at) - 1));
  const before = await p.evaluate(k => { const e = document.querySelectorAll('[data-appear]')[k]; return e.getBoundingClientRect().height; }, a.k);
  ok(a.at === 0 || before === 0, `13: component ${a.k} (scene ${a.i}) takes ${before} px of room before it begins at ${a.at} ms`);
  await seek(Math.min(meta.duration - 1, s.start + ft(a, a.at + 5)));
  const after = await p.evaluate(k => { const e = document.querySelectorAll('[data-appear]')[k]; return e.getBoundingClientRect().height; }, a.k);
  ok(after > 0 || s.start + a.at + 5 >= s.start + s.ms, `13: component ${a.k} (scene ${a.i}) has no height once it has begun`);
}
const boxes = await p.evaluate(() => [...document.querySelectorAll('[data-reveal]')].map((e, k) => { const box = e.closest('.ag-order, .ag-bubble') || e; return { k, i: [...document.querySelectorAll('.scene')].indexOf(e.closest('.scene')), delay: +e.getAttribute('data-reveal-delay'), dur: +e.getAttribute('data-reveal-ms'), n: e.querySelectorAll('.w').length, ff: +((e.closest('[data-ff]') || {dataset:{}}).dataset.ff || 0), ffAt: +((e.closest('[data-ff]') || {dataset:{}}).dataset.ffAt || 0) }; }));
const isFirst = k => p.evaluate(k => { const e = document.querySelectorAll('[data-reveal]')[k], box = e.closest('.ag-order') || e; return box.querySelector('[data-reveal]') === e; }, k);
const boxH = k => p.evaluate(k => { const e = document.querySelectorAll('[data-reveal]')[k], box = e.closest('.ag-order') || e; return box.getBoundingClientRect().height; }, k);
for (const b of boxes.filter(b => b.n >= 40 && b.dur > 20)) {
  const s = meta.scenes[b.i];
  await seek(s.start + ft(b, b.delay + 1)); const first = await boxH(b.k);
  let last = first;
  for (let f = 1; f <= 6; f++) { await seek(Math.min(meta.duration - 1, s.start + ft(b, b.delay + Math.round(b.dur * f / 6)))); const h = await boxH(b.k); ok(h >= last - 0.5, `13: streamed box ${b.k} shrank from ${last} to ${h} px while streaming`); last = h; }
  ok(await isFirst(b.k) ? first < 0.6 * last : first < last, `13: streamed box ${b.k} (scene ${b.i}) is ${first} px tall at its first word and ${last} px when done: it must grow with its text, not start at full size (a first text in its box: under 60% of the final height; a later one, e.g. a bullet in an answer card: taller when done)`);
}

/* 11: threads */
const threads = await p.evaluate(() => [...document.querySelectorAll('.thread-in')].map((t, k) => ({ k, i: [...document.querySelectorAll('.scene')].indexOf(t.closest('.scene')), view: +t.getAttribute('data-view') })));
for (const th of threads) {
  const s = meta.scenes[th.i]; let prev = -1;
  for (let f = 0; f <= 16; f++) {
    await seek(s.start + Math.round((s.ms - 1) * f / 16));
    const off = await p.evaluate(k => -parseFloat(document.querySelectorAll('.thread-in')[k].style.transform.replace(/translateY\(|px\)/g, '')), th.k);
    ok(off >= prev - 0.01, `11: thread ${th.k} scrolled back (${prev} then ${off}) at ${Math.round((s.ms - 1) * f / 16)} ms into its scene`); prev = off;
  }
  const end = await p.evaluate(k => { const t = document.querySelectorAll('.thread-in')[k], last = t.lastElementChild, off = -parseFloat(t.style.transform.replace(/translateY\(|px\)/g, '')); return { bottom: last.offsetTop + last.offsetHeight - off, top: last.offsetTop - off }; }, th.k);
  ok(end.bottom <= th.view + 2 && end.top >= -2, `11: at the end of thread ${th.k} the newest message spans ${Math.round(end.top)} to ${Math.round(end.bottom)} in a view ${th.view} px tall`);
}

/* 12: versus. The Cerebras lane is never slower than 1,000 tokens a second, finishes before the GPU lane, and at the end of its scene has counted every token and says Done */
const MIN_TPS = 1000;
const lanes = await p.evaluate(() => [...document.querySelectorAll('.thread-in[data-lane]')].map(t => ({ lane: t.dataset.lane, tps: +t.dataset.tps, end: +t.dataset.end, filmEnd: +t.dataset.filmEnd, total: +t.dataset.total, i: [...document.querySelectorAll('.scene')].indexOf(t.closest('.scene')) })));
for (const L of lanes.filter(l => l.lane === 'cerebras')) {
  const G = lanes.find(l => l.lane === 'gpu' && l.i === L.i);
  ok(L.tps >= MIN_TPS, `12: scene ${L.i}: the Cerebras lane streams at ${L.tps} tokens a second (at least ${MIN_TPS})`);
  ok(G && G.tps < L.tps && L.filmEnd < G.filmEnd, `12: scene ${L.i}: Cerebras finishes at ${L.filmEnd} ms, the GPU lane at ${G && G.filmEnd} ms`);
  await seek(meta.scenes[L.i].start + L.end + 500);
  const got = await p.evaluate(i => { const sce = document.querySelectorAll('.scene')[i], tk = [...sce.querySelectorAll('[data-tokens]')].map(e => e.textContent.replace(/,/g, '')), dn = [...sce.querySelectorAll('.versus-done')].map(e => e.style.visibility === 'hidden' ? 0 : +e.style.opacity); return { tk, dn }; }, L.i);
  ok(+got.tk[0] === L.total, `12: scene ${L.i}: the Cerebras count is ${got.tk[0]} of ${L.total} tokens when it finishes`);
  ok(got.dn[0] > 0.9 && got.dn[1] === 0, `12: scene ${L.i}: the DONE card is up on the Cerebras lane (opacity ${got.dn[0]}) and not yet on the GPU lane (${got.dn[1]})`);
  const conf = await p.evaluate(i => document.querySelectorAll('.scene')[i].querySelector('.versus-conf').children.length, L.i);
  ok(conf > 20, `12: scene ${L.i}: ${conf} confetti pieces in the air 500 ms after Cerebras finishes`);
  await seek(meta.scenes[L.i].start + L.end + 2500);
  const gone = await p.evaluate(i => document.querySelectorAll('.scene')[i].querySelector('.versus-conf').children.length, L.i);
  ok(gone === 0, `12: scene ${L.i}: the confetti is gone after 1.7 s (${gone} left)`);
  const last = meta.scenes[L.i].start + meta.scenes[L.i].ms - FADE - 5;   /* the moment before the crossfade out, when the DONE cards begin to leave */
  await seek(last);
  const both = await p.evaluate(i => [...document.querySelectorAll('.scene')[i].querySelectorAll('.versus-done')].map(e => e.style.visibility === 'hidden' ? 0 : +e.style.opacity), L.i);
  ok(both[0] === 1 && both[1] === 1, `12: scene ${L.i}: just before the crossfade out both DONE cards are fully up (${both}); the Cerebras one never leaves while the GPU one arrives`);
  ok(meta.scenes[L.i].ms - G.filmEnd >= 3000, `12: scene ${L.i}: both DONE cards stay at least 3 s (the scene holds ${meta.scenes[L.i].ms - G.filmEnd} ms after the GPU lane finishes)`);
  const sat = await p.evaluate(i => { const lane = document.querySelectorAll('.scene')[i].querySelector('[data-lane-box=gpu]'), g = lane.querySelector('.versus-grey');
    const stray = [...lane.querySelectorAll('.ag-chip, .ag-bubble, svg, .ag-order')].filter(e => !e.closest('.versus-grey') && !e.closest('.versus-ff'));
    return { filter: g ? getComputedStyle(g).filter : 'none', stray: stray.length, n: lane.querySelectorAll('.ag-chip, .ag-bubble, svg').length }; }, L.i);
  ok(/grayscale\(1\)/.test(sat.filter) && sat.stray === 0 && sat.n > 0, `12: scene ${L.i}: the GPU lane is DESATURATED as a whole in any theme (filter "${sat.filter}", ${sat.stray} of its ${sat.n} marks, chips and bubbles outside it)`);
  const pills = await p.evaluate(i => { const lum = c => { const v = (c.match(/[\d.]+/g) || []).slice(0, 3).map(x => { x = +x / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
    return [...document.querySelectorAll('.scene')[i].querySelectorAll('[data-clock]')].map(e => { const pill = e.closest('.ag-chip'), a = lum(getComputedStyle(pill).backgroundColor), b = lum(getComputedStyle(e).color); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); }); }, L.i);
  ok(pills.every(c => c >= 3), `12: scene ${L.i}: the clock pills' text has a contrast of ${pills.map(c => c.toFixed(1)).join(' and ')} against their background (at least 3, the minimum for a UI component: the house accent with white text is 3.9; the light-on-light pill this check was written for was 1.1), in this theme`);
  const brand = await p.evaluate(i => { const sce = document.querySelectorAll('.scene')[i], gpu = sce.querySelector('[data-lane-box=gpu]'), cer = sce.querySelector('[data-lane-box=cerebras]'), sig = cer.querySelector('.ag-mark svg') ? cer.querySelector('.ag-mark svg').innerHTML : '';
    return { marks: gpu.querySelectorAll('.ag-mark, .ag-mark-d, .ag-mark-l').length, sigInGpu: sig.length > 50 && gpu.innerHTML.includes(sig.slice(0, 120)), sigInCer: sig.length > 50 }; }, L.i);
  ok(brand.sigInCer, `12: scene ${L.i}: the Cerebras lane shows the Cerebras mark (the check can see it)`);
  ok(brand.marks === 0 && !brand.sigInGpu, `12: scene ${L.i}: HARD RULE: the GPU lane has no Cerebras mark, grey or otherwise (${brand.marks} mark elements, markup present: ${brand.sigInGpu})`);
}
/* 15: THE MATHS MATCHES EXACTLY. For each versus scene and each lane: the lane's time is tokens / tokens-a-second to the millisecond, the live token count follows tps x time (to within one token), the words rendered follow the tokens (three quarters of a word per token, to within a word per message), the DONE pill reads that time, and the two lanes' times are in the ratio of their rates */
const FIRST = 700;
const laneMath = await p.evaluate(() => [...document.querySelectorAll('.scene')].map((sce, i) => ({ i, lanes: [...sce.querySelectorAll('.thread-in[data-lane]')].map(t => ({ lane: t.dataset.lane, tps: +t.dataset.tps, end: +t.dataset.end, filmEnd: +t.dataset.filmEnd, ffAt: +(t.closest('[data-lane-box]').dataset.ffAt || 0), ff: +(t.closest('[data-lane-box]').dataset.ff || 0), total: +t.dataset.total, msgs: t.children.length, words: [...t.querySelectorAll('.w')].length })) })).filter(x => x.lanes.length));
for (const sc of laneMath) {
  const byLane = Object.fromEntries(sc.lanes.map(l => [l.lane, l]));
  for (const l of sc.lanes) ok(l.end - FIRST === Math.round(l.total * 1000 / l.tps), `15: scene ${sc.i} ${l.lane}: the lane runs ${l.end - FIRST} ms for ${l.total} tokens at ${l.tps} a second (exactly ${Math.round(l.total * 1000 / l.tps)} ms)`);
  const ratio = (byLane.gpu.end - FIRST) / (byLane.cerebras.end - FIRST), want = byLane.cerebras.tps / byLane.gpu.tps;
  ok(Math.abs(ratio / want - 1) < 0.01, `15: scene ${sc.i}: the lanes' times are in the ratio ${ratio.toFixed(2)}, their rates ${want.toFixed(2)}`);
  for (const [k, l] of sc.lanes.entries()) {
    for (const f of [0.25, 0.5, 0.75, 1]) {
      const t = FIRST + f * (l.end - FIRST), ft = l.ff && t > l.ffAt ? l.ffAt + (t - l.ffAt) / l.ff : t; await seek(meta.scenes[sc.i].start + Math.round(ft));
      const got = await p.evaluate(({ i, k }) => { const sce = document.querySelectorAll('.scene')[i], lane = sce.querySelectorAll('.thread-in[data-lane]')[k], card = lane.closest('[data-lane-box]');
        return { tokens: +card.querySelector('[data-tokens]').textContent.replace(/,/g, ''), words: [...lane.querySelectorAll('.w')].filter(w => !w.classList.contains('rv-off') && !w.closest('.ag-bubble')).length }; }, { i: sc.i, k });
      const wantTok = Math.min(l.total, Math.floor(l.tps * (t - FIRST) / 1000 + 1e-6));
      ok(Math.abs(got.tokens - wantTok) <= Math.ceil(l.tps / 1000) + 1, `15: scene ${sc.i} ${l.lane} at ${Math.round(f * 100)}% of its run: the token count reads ${got.tokens}, tokens a second x time is ${wantTok} (to within the tokens of one millisecond, the clock's resolution)`);
      const userWords = await p.evaluate(({ i, k }) => [...document.querySelectorAll('.scene')[i].querySelectorAll('.thread-in[data-lane]')[k].querySelectorAll('.ag-bubble .w')].length, { i: sc.i, k });
      const sayWords = l.words - userWords, wantWords = sayWords * wantTok / l.total;
      ok(Math.abs(got.words - wantWords) <= l.msgs + 2, `15: scene ${sc.i} ${l.lane} at ${Math.round(f * 100)}%: ${got.words} words are rendered, the tokens say ${wantWords.toFixed(1)} (to within a word a message)`);
    }
    await seek(meta.scenes[sc.i].start + l.filmEnd + 600);
    const pill = await p.evaluate(({ i, k }) => document.querySelectorAll('.scene')[i].querySelectorAll('.versus-done')[k].querySelector('span').textContent, { i: sc.i, k });
    ok((pill.match(/^[\d.]+/) || [''])[0] === ((l.end - FIRST) / 1000).toFixed(2), `15: scene ${sc.i} ${l.lane}: the DONE pill reads "${pill}", the lane's time is ${((l.end - FIRST) / 1000).toFixed(2)} (the number is compared; the unit word may be translated with words.sec)`);
  }
}

for (const t of meta.scenes.filter(x => x.scene === 'thread')) ok((t.tps ?? meta.tps ?? MIN_TPS) >= MIN_TPS, `12: thread scene at ${t.start} streams at ${t.tps ?? meta.tps} tokens a second`);
await browser.close();

console.log(`${checks} checks, ${fails.length} failed`);
fails.forEach(f => console.log('  FAIL ' + f));
process.exit(fails.length ? 1 : 0);
