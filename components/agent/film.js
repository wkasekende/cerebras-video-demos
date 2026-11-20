/* AGENT FILM ENGINE: a page of stacked scenes that paints ONE instant, deterministically.
   window.AgentFilm.ready   a Promise: the grounds are drawn and fonts are loaded
   window.AgentFilm.seek(ms) -> Promise  paint the frame at `ms`: scene opacities (a crossfade of AGENT_FILM.fade ms into each scene), the typed prompt, the claim's count-up,
                             every CSS animation (the spinning mark) set to `ms`, and the pop-in clip's frame swapped to the one for that time.
   The renderer (tools/agent-film.mjs) calls seek() for each frame time and photographs the page. Nothing here reads the clock. */
(function (root) {
  'use strict';
  var F = root.AGENT_FILM, scenes = [].slice.call(document.querySelectorAll('.scene')).map(function (el) {
    return { el: el, i: +el.dataset.i, start: +el.dataset.start, ms: +el.dataset.ms, kind: el.dataset.kind };
  });
  var back = function (t) { var c = 1.70158; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); };
  var CONFETTI = (function () { var x = 12345, cols = ['#e8442b', '#f7c948', '#3b5bff', '#2fbf71', '#ff7ab6', '#8b5cf6'], out = [], i, a, v;   /* the comparison layout's burst (layouts/comparison/engine.js), same generator, so it is the same burst */
    var rnd = function () { x = (x * 1103515245 + 12345) & 0x7fffffff; return (x >> 8) / (1 << 23); };
    for (i = 0; i < 44; i++) { a = rnd() * Math.PI * 2; v = 320 + rnd() * 520; out.push({ vx: Math.cos(a) * v, vy: Math.sin(a) * v - 220, c: cols[i % cols.length], w: 5 + rnd() * 5, h: 6 + rnd() * 7, rot: rnd() * 360, spin: (rnd() - 0.5) * 720, life: 1100 + rnd() * 500 }); }
    return out; })();
  var clamp = function (v) { return v < 0 ? 0 : v > 1 ? 1 : v; }, ease = function (t) { return 1 - Math.pow(1 - t, 3); };
  function pad(n) { n = String(n); while (n.length < 5) n = '0' + n; return n; }
  var ready = (function () {
    var go = function () {
      if (root.AgGround) root.AgGround.mountAll();
      return new Promise(function (res) {
        (function wait(n) { if ((!root.AgGround || root.AgGround.pending === 0) && n > 4) res(); else setTimeout(function () { wait(n + 1); }, 120); })(0);
      });
    };
    var fonts = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    return fonts.then(go);
  })();
  /* THE MORPH: the typing scene's composer BECOMES the white base of the next scene (the window, or the user's video). A card at the top of the stack interpolates the composer's rectangle, radius and colour
     into the target's over MORPH ms (from MORPH_PRE ms before the next scene starts); the composer's contents fade out in the first part, the target's contents fade in over the second. */
  var PRESS_MS = 140;
  /* a lane that is fast-forwarded (the slow lane, data-ff-at, data-ff) runs on its OWN clock: film time up to ff-at, then ff times faster; everything it streams (words, token count, clock, thinking row) follows that clock, never the film's */
  function lt(e, local) { var b = e.closest('[data-ff]'); if (!b) return local; var a = +b.getAttribute('data-ff-at'), n = +b.getAttribute('data-ff'); return local <= a ? local : a + (local - a) * n; }
  var TILT_DEG = 9;   /* the composer tilts in perspective as it becomes the window (reference video 1), back to flat by the time it has landed */
  var MORPH = 1000, MORPH_PRE = 300, MORPH_LAND = 0.8, EXIT_MS = 150;   /* the card travels over the first MORPH_LAND of the morph and the target's contents (the title bar and its three lights, the text) appear only after it has LANDED; a scene's overlays (the DONE cards) leave in the first EXIT_MS of the crossfade out of their scene */
  scenes.forEach(function (s, i) {
    s.cut = s.el.hasAttribute('data-cut');
    if (s.el.hasAttribute('data-morph') && i > 0) { s.morphIn = { from: scenes[i - 1], p: -1 }; scenes[i - 1].morphOut = s.morphIn; }
  });
  var CARD_BASE = 'position:absolute;pointer-events:none;z-index:50;box-sizing:border-box;', cardEl = document.createElement('div');
  cardEl.style.cssText = CARD_BASE + 'display:none;';
  document.body.appendChild(cardEl);
  function lerp(a, b, t) { return a + (b - a) * t; }
  function rgb(c) { var m = /rgba?\(([^)]+)\)/.exec(c); if (!m) return [255, 255, 255, 1]; var p = m[1].split(',').map(parseFloat); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
  var inout = function (t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; };
  function morphLayer(ms) {
    var on = false;
    scenes.forEach(function (s) {
      var mo = s.morphIn; if (!mo) return;
      var p = (ms - (s.start - MORPH_PRE)) / MORPH; mo.p = p;
      var src = mo.from.el.querySelector('.ag-composer'), dst = s.el.querySelector('.ag-window, .popin-card');
      if (!src || !dst) return;
      var kids = function (el) { return [].slice.call(el.children); };
      if (p <= 0 || p >= 1) {
        kids(src).forEach(function (k) { k.style.opacity = ''; }); kids(dst).forEach(function (k) { k.style.opacity = ''; });
        dst.style.background = ''; dst.style.boxShadow = ''; src.style.visibility = '';
        return;
      }
      on = true;
      dst.style.background = ''; dst.style.boxShadow = '';   /* read the target's REAL colours: not what an earlier frame's morph left on it */
      var cs = getComputedStyle(src), cd = getComputedStyle(dst);
      var a = src.getBoundingClientRect(), b = dst.getBoundingClientRect(), t = inout(clamp(p / MORPH_LAND));
      var ca = rgb(cs.backgroundColor), cb = rgb(dst.classList.contains('popin-card') ? cs.backgroundColor : cd.backgroundColor);
      var bg = 'rgb(' + [0, 1, 2].map(function (k) { return Math.round(lerp(ca[k], cb[k], t)); }).join(',') + ')';
      cardEl.style.cssText = CARD_BASE + 'display:block;left:' + lerp(a.left, b.left, t) + 'px;top:' + lerp(a.top, b.top, t) + 'px;width:' + lerp(a.width, b.width, t) + 'px;height:' + lerp(a.height, b.height, t) +
        'px;border-radius:' + lerp(parseFloat(cs.borderTopLeftRadius) || 0, parseFloat(cd.borderTopLeftRadius) || 0, t) + 'px;background:' + bg + ';box-shadow:' + cs.boxShadow +
        ';border:' + (parseFloat(cs.borderTopWidth) * (1 - t)) + 'px solid ' + cs.borderTopColor + ';transform-origin:50% 100%;transform:perspective(1800px) rotateX(' + (TILT_DEG * Math.sin(Math.PI * clamp(p / MORPH_LAND))) + 'deg);';
      src.style.visibility = 'hidden';
      var fadeOut = 1 - clamp(p / 0.32), fadeIn = clamp((p - MORPH_LAND) / (1 - MORPH_LAND));
      kids(src).forEach(function (k) { k.style.opacity = fadeOut; });
      dst.style.background = 'transparent'; dst.style.boxShadow = 'none';
      kids(dst).forEach(function (k) { k.style.opacity = fadeIn; });
    });
    if (!on) cardEl.style.cssText = CARD_BASE + 'display:none;';
    return cardEl;
  }
  function seek(ms) {
    var waits = [];
    var card = morphLayer(ms);
    scenes.forEach(function (s) {
      var end = s.start + s.ms, op, mo = s.morphIn, mp = mo ? mo.p : -1;
      if (mo) op = ms >= end ? 0 : (mp > 0.3 ? 1 : 0);   /* a scene entered by morph never fades in: its ground is the last scene's, and the card carries the change */
      else if (s.morphOut && s.morphOut.p >= 0 && s.morphOut.p < 1) op = 1;   /* the typing scene stays until its composer has become the window */
      else if (ms >= end || ms < s.start - (s.cut ? 0 : F.fade)) op = 0;
      else op = (s.i === 0 || s.cut) ? 1 : clamp((ms - (s.start - F.fade)) / F.fade);   /* a hard cut (data-cut) has no crossfade: it is on at its first moment */
      s.el.style.opacity = op;
      var local = ms - s.start, LOCAL = local;   /* typed text and dialled numbers are a function of the time even in a scene that is not on screen, so the page's state never depends on what was painted before */
      [].forEach.call(s.el.querySelectorAll('[data-type]'), function (e) {
        var full = e.getAttribute('data-type'), dur = +e.getAttribute('data-type-ms') || 3000, p = clamp((local - 250) / dur);
        e.textContent = full.slice(0, Math.floor(p * full.length));
        var box = e.closest('.ag-composer'), sb = box && box.querySelector('[data-send]');
        if (sb) sb.classList.toggle('off', e.textContent.length === 0);   /* the send button is the disabled grey until the first character is typed, then the accent */
      });
      [].forEach.call(s.el.querySelectorAll('[data-caret-until]'), function (e) { e.style.visibility = local < +e.getAttribute('data-caret-until') ? '' : 'hidden'; });   /* the caret stops at the click */
      [].forEach.call(s.el.querySelectorAll('[data-send][data-press]'), function (e) { var c = +e.getAttribute('data-press'); e.style.transform = (local >= c && local < c + PRESS_MS) ? 'scale(0.86)' : 'scale(1)'; });   /* the press */
      [].forEach.call(s.el.querySelectorAll('.ag-pointer'), function (e) {   /* the mouse: glides in from below, eased, and is on the send button at the click, then goes */
        var f = +e.getAttribute('data-from'), du = +e.getAttribute('data-ms'), c = +e.getAttribute('data-click'), k = inout(clamp((local - f) / du)), o = clamp((local - f) / 180) * (1 - clamp((local - c - PRESS_MS) / 260));
        var x0 = +e.getAttribute('data-x0'), y0 = +e.getAttribute('data-y0'), x1 = +e.getAttribute('data-x1'), y1 = +e.getAttribute('data-y1');
        e.style.display = o > 0 ? '' : 'none'; e.style.opacity = o; e.style.left = (x0 + (x1 - x0) * k - 2.6) + 'px'; e.style.top = (y0 + (y1 - y0) * k - 2) + 'px';
      });
      [].forEach.call(s.el.querySelectorAll('[data-elapsed]'), function (e) { e.textContent = (1 + Math.floor(Math.max(0, local - (+e.getAttribute('data-from') || 0)) / 1000)) + 's'; });   /* "Preparing this turn... 1s" ticks */
      [].forEach.call(s.el.querySelectorAll('[data-timer]'), function (e) { var f = +e.getAttribute('data-from'), st = +e.getAttribute('data-stop'); e.textContent = (Math.min(st - f, Math.max(0, ms - f)) / 1000).toFixed(1) + 's'; });   /* the optional elapsed-time pill, in film time */
      [].forEach.call(s.el.querySelectorAll('.att-stack'), function (e) { var f = +e.getAttribute('data-slide-from'), d = +e.getAttribute('data-slide-ms'), k = ease(clamp((local - f) / d)); e.style.opacity = k; e.style.transform = 'translateX(' + ((1 - k) * 220) + 'px) rotate(' + ((1 - k) * 8) + 'deg)'; });   /* the attachment slides in from the right with a slight rotation while the typing goes on */
      [].forEach.call(s.el.querySelectorAll('[data-state]'), function (e) { e.textContent = local >= +e.getAttribute('data-at') ? e.getAttribute('data-b') : e.getAttribute('data-a'); });
      [].forEach.call(s.el.querySelectorAll('.versus-ff'), function (e) { var f = +e.getAttribute('data-from'), t = +e.getAttribute('data-to'), o = clamp((local - f) / 180) * (1 - clamp((local - t) / 180)); e.style.display = o > 0 ? 'flex' : 'none'; e.style.opacity = o; });   /* the fast-forward badge */
      [].forEach.call(s.el.querySelectorAll('[data-vanish]'), function (e) { e.style.opacity = local >= +e.getAttribute('data-vanish') ? 0 : ''; });   /* gone, but its room stays, just before the crossfade out */
      [].forEach.call(s.el.querySelectorAll('[data-show-from]'), function (e) { e.classList.toggle('rv-off', !(local >= +e.getAttribute('data-show-from') && local < +e.getAttribute('data-show-to'))); });   /* a page of the browser pane, its tab label, a modal: on screen between two moments */
      [].forEach.call(s.el.querySelectorAll('[data-scroll]'), function (e) { var f = +e.getAttribute('data-scroll-from'), t = +e.getAttribute('data-scroll-to'), px = +e.getAttribute('data-scroll'); e.style.transform = 'translateY(' + (-px * clamp((local - f) / (t - f))) + 'px)'; });   /* the page scrolls, linearly, over its time on screen */
      [].forEach.call(s.el.querySelectorAll('[data-blur]'), function (e) { var f = +e.getAttribute('data-blur-from'), d = +e.getAttribute('data-blur-ms'), px = +e.getAttribute('data-blur-px'), k = ease(clamp((local - f) / d)); e.style.filter = k > 0 ? 'blur(' + (px * k) + 'px) brightness(' + (1 - 0.16 * k) + ')' : 'none'; });   /* the defocus */
      [].forEach.call(s.el.querySelectorAll('[data-grow]'), function (e) { var f = +e.getAttribute('data-from'), d = +e.getAttribute('data-ms'), k = ease(clamp((local - f) / d)); e.style.opacity = k; e.style.transform = 'translateX(' + ((1 - k) * 140) + 'px)'; });   /* the browser pane slides in */
      [].forEach.call(s.el.querySelectorAll('[data-lerp]'), function (e) { var f = +e.getAttribute('data-from'), d = +e.getAttribute('data-ms'), k = inout(clamp((local - f) / d)), l0 = +e.getAttribute('data-left0'), l1 = +e.getAttribute('data-left1'), w0 = +e.getAttribute('data-w0'), w1 = +e.getAttribute('data-w1'); e.style.left = (l0 + (l1 - l0) * k) + 'px'; e.style.width = (w0 + (w1 - w0) * k) + 'px'; });   /* the chat narrows to the left as the pane opens */
      [].forEach.call(s.el.querySelectorAll('[data-think]'), function (e) {   /* the thinking row: the next section's title and three pulsing dots, there only until the message begins (in the lane's own clock) */
        var t = lt(e, local); e.classList.toggle('rv-off', !(t >= +e.getAttribute('data-think-from') && t < +e.getAttribute('data-think-to')));
        [].forEach.call(e.querySelectorAll('[data-dots] i'), function (d, i) { var ph = (t / 1000) * 1.3 - i * 0.2; d.style.opacity = 0.25 + 0.75 * Math.pow(Math.max(0, Math.sin(2 * Math.PI * ph)), 2); });
      });
      [].forEach.call(s.el.querySelectorAll('[data-count]'), function (e) {   /* a number DIALS up to its final value when its scene appears: data-count (the target), data-dec (decimals), data-delay, data-dur (ms) */
        var target = +e.getAttribute('data-count'), dec = +(e.getAttribute('data-dec') || 0), dl = +(e.getAttribute('data-delay') || 350), du = +(e.getAttribute('data-dur') || 1500);
        var p = ease(clamp((local - dl) / du)), v = target * p;
        e.textContent = v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
      });
      [].forEach.call(s.el.querySelectorAll('[data-tokens]'), function (e) {   /* a lane's live token count: each message adds tokens at the lane's tokens a second from its start; plan = "start,tokens;..." */
        var tps = +e.getAttribute('data-tps'), v = 0, local = lt(e, LOCAL);
        e.getAttribute('data-tokens').split(';').forEach(function (q) { if (!q) return; var a = q.split(','); v += Math.min(+a[1], Math.max(0, (local - +a[0]) * tps / 1000)); });
        e.textContent = Math.floor(v + 1e-6).toLocaleString('en-US');
      });
      [].forEach.call(s.el.querySelectorAll('[data-clock]'), function (e) {   /* a lane's clock pill: tenths of a second while it runs, hundredths when the lane is done: the time is exactly the lane's tokens / tokens-a-second */
        var f = +e.getAttribute('data-from'), st = +e.getAttribute('data-stop'), t = Math.max(0, lt(e, LOCAL) - f);
        e.textContent = t >= st - f ? ((st - f) / 1000).toFixed(2) + 's' : (t / 1000).toFixed(1) + 's';
      });
      [].forEach.call(s.el.querySelectorAll('.versus-done'), function (e) {   /* the DONE card of the comparison layout: drops in with a little overshoot when its lane has finished and STAYS (the winner's never goes, the loser's arrives later and both hold) */
        var at = +e.getAttribute('data-at'), dt = local - at, kd = back(clamp(dt / 460)), gone = clamp((local - (s.ms - F.fade)) / EXIT_MS), o = dt >= 0 ? Math.min(1, dt / 160) * (1 - gone) : 0;
        e.style.visibility = o > 0 ? '' : 'hidden'; e.style.opacity = o; e.style.transform = 'translateY(' + ((1 - kd) * -46) + 'px) scale(' + (0.72 + 0.28 * kd) + ')';
      });
      [].forEach.call(s.el.querySelectorAll('.versus-conf'), function (e) {   /* the winner's confetti: the comparison layout's seeded burst, a function of the time since the lane finished */
        var dt = local - +e.getAttribute('data-at'), cx = +e.getAttribute('data-cx'), cy = +e.getAttribute('data-cy'), html = '', i, p, u, sec, drag, o;
        if (dt >= 0 && dt < 1700) for (i = 0; i < CONFETTI.length; i++) {
          p = CONFETTI[i]; u = dt / p.life; if (u >= 1) continue; sec = dt / 1000; drag = 1 - 0.55 * u; o = u < 0.6 ? 1 : 1 - (u - 0.6) / 0.4;
          html += '<i style="left:' + (cx + p.vx * sec * drag).toFixed(1) + 'px;top:' + (cy + p.vy * sec * drag + 520 * sec * sec).toFixed(1) + 'px;width:' + p.w + 'px;height:' + p.h + 'px;background:' + p.c + ';opacity:' + o.toFixed(2) + ';transform:rotate(' + (p.rot + p.spin * sec).toFixed(0) + 'deg)"></i>';
        }
        if (e.innerHTML !== html) e.innerHTML = html;
      });
      [].forEach.call(s.el.querySelectorAll('[data-appear]'), function (e) { e.classList.toggle('rv-off', lt(e, LOCAL) < +e.getAttribute('data-appear')); });   /* PROGRESSIVE: a component (a message, a bullet and its marker, a footer) takes no room until it begins */
      [].forEach.call(s.el.querySelectorAll('[data-reveal]'), function (e) {   /* streamed text: the first k words are RENDERED and the rest take no room (rv-off), so the box grows with its text; k is a function of the time (data-reveal-delay, data-reveal-ms from the scene's start), at least 1 from the moment it begins */
        var local = lt(e, LOCAL), dl = +e.getAttribute('data-reveal-delay'), du = +e.getAttribute('data-reveal-ms'), ws = e.querySelectorAll('.w'), k = Math.max(local >= dl ? 1 : 0, Math.floor(clamp((local - dl) / du) * ws.length + (local >= dl + du ? 0.5 : 0)));
        e.classList.toggle('rv-off', local < dl);
        for (var i = 0; i < ws.length; i++) ws[i].classList.toggle('rv-off', i >= k);
      });
      [].forEach.call(s.el.querySelectorAll('.thread-in'), function (t) {   /* the conversation is pinned to its bottom as it grows: the offset is whatever keeps the newest rendered text in view, so it follows the text word by word and can only increase */
        var view = +t.getAttribute('data-view'), msgs = [].slice.call(t.children), i, m, bottom = 0;
        for (i = 0; i < msgs.length; i++) { m = msgs[i]; if (m.hasAttribute('data-think')) { if (!m.classList.contains('rv-off')) bottom = m.offsetTop + m.offsetHeight + 8; continue; } if (m.classList.contains('rv-off')) break; bottom = m.offsetTop + m.offsetHeight + 8; }   /* a thinking row holds the bottom only while it is on screen */
        t.style.transform = 'translateY(' + (-Math.max(0, bottom - view)) + 'px)';
      });
      [].forEach.call(s.el.querySelectorAll('img[data-popin]'), function (img) {   /* also for a scene that is not on screen (frame 1 before it, the last frame after), so the state is a function of time; only a visible scene is waited for */
        var P = root.AGENT_POPIN; if (!P || !P.frames) return;
        var n = Math.max(1, Math.min(P.frames, Math.floor(((Math.max(0, local) + (+img.getAttribute('data-clip-from') || 0)) * (P.speed || 1) - (P.base || 0)) / 1000 * P.fps) + 1)), src = P.data ? P.data[n - 1] : P.dir + pad(n) + '.jpg';
        if (img.getAttribute('src') !== src) { img.setAttribute('src', src); if (op > 0) waits.push(img.decode ? img.decode().catch(function () {}) : Promise.resolve()); }
      });
    });
    document.getAnimations().forEach(function (a) { try { a.pause(); a.currentTime = ms; } catch (e) {} });
    return Promise.all(waits).then(function () { return new Promise(function (r) { requestAnimationFrame(function () { requestAnimationFrame(r); }); }); });
  }
  /* the cloud renderer (lambda/demokit-render.cjs) drives window.__demo.seek(ms) and folds identical consecutive signatures; every frame here is its own instant, so the signature is the time */
  root.__demo = { seek: function (ms) { return ready.then(function () { return seek(ms); }).then(function () { return 't' + ms; }); } };
  root.AgentFilm = { morph: { ms: MORPH, pre: MORPH_PRE, land: MORPH_LAND, exit: EXIT_MS, card: cardEl }, opacities: function () { return scenes.map(function (s) { return +s.el.style.opacity; }); }, ready: ready, seek: seek, duration: F.duration, fps: F.fps, scenes: scenes.map(function (s) { return { kind: s.kind, start: s.start, ms: s.ms }; }) };
})(window);
