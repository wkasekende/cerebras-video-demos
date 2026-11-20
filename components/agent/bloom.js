/* BLOOM: the fourth reference's ground (a reference video): a near-black field with a few soft, blurred shapes drawn on it, and film grain.
   Not a gradient between two corners: ochre glows rise from the bottom-left, a crimson one from the left edge, and a big BLURRED BLACK BLOB hangs from the top
   right (a drawn ellipse, then blurred), with a dark maroon halo round it. Drawn in a canvas so the lab can difference it against the video's frame in the browser.

   AgBloom.draw(canvas, p)          paint the ground at the canvas's size (the numbers are fractions of the frame, so any size)
   p.speckle (default AgBloom.SPECKLE)  the speckle recipe; the shapes below are its density MAP (a layer may also carry `lum`: lo, hi, power, invert, to follow the ground's own lightness)
   p.dither (default 2.6 levels)        noise laid under the speckle so the soft shapes do not band
   AgBloom.PRESET, AgBloom.DIM      the fitted parameters: the bright ground (typing, window) and the dim one (claim, lockup)
   AgBloom.fit(refImageData, mask, start, rounds)   coordinate descent against a reference picture (the lab and tools/fit-bloom.mjs use it)
*/
(function (root) {
  'use strict';
  /* FITTED by tools/fit-bloom.mjs against frames of the video (f001 for the bright ground, f073 for the dim one the claim and lockup sit on), at 240 x 135, composer and text masked */
  var PRESET = {"base": "#040a0f", "glows": [{"x": 0.092, "y": 0.89, "rx": 0.565, "ry": 0.642, "c": "#733e11", "a": 0.877, "mid": 0.712}, {"x": 0.082, "y": 0.352, "rx": 0.82, "ry": 0.561, "c": "#6b0011", "a": 0.773, "mid": 0.405}, {"x": 0.589, "y": 0.96, "rx": 0.628, "ry": 0.743, "c": "#820c1a", "a": 0.561, "mid": 0.451}], "halo": {"scale": 1, "c": "#3d303d", "a": 1, "blur": 180.71}, "blob": {"x": 0.751, "y": -0.041, "rx": 0.42, "ry": 0.454, "c": "#020202", "a": 0.754, "blur": 168.268}, "grain": 0, "grainSeed": 3};
  var DIM = {"base": "#010501", "glows": [{"x": -0.09, "y": 1.087, "rx": 0.49, "ry": 0.47, "c": "#734608", "a": 0.809, "mid": 0.545}, {"x": -0.054, "y": 0.494, "rx": 0.79, "ry": 0.615, "c": "#57070f", "a": 0.773, "mid": 0.369}, {"x": 0.504, "y": 1.041, "rx": 0.6, "ry": 0.688, "c": "#5f1114", "a": 0.546, "mid": 0.396}], "halo": {"scale": 1, "c": "#1d0421", "a": 0.878, "blur": 295.831}, "blob": {"x": 0.878, "y": -0.086, "rx": 0.572, "ry": 0.512, "c": "#020202", "a": 0.841, "blur": 133.317}, "grain": 0, "grainSeed": 3};
  /* THE GOLDEN TILE ground (a reference video): the same drawn shapes, a vignette, and a tiled floor of hairlines with a disc at each crossing; fitted by tools/fit-bloom.mjs
     against the texture zoomed to 1920 wide (START=<preset> picks the starting point) */
  var TILE = {"base": "#67451f", "glows": [{"x": 0.717, "y": 0.514, "rx": 0.814, "ry": 1.03, "c": "#c89638", "a": 0.996, "mid": 0.79}, {"x": 0.165, "y": 0.4, "rx": 0.416, "ry": 0.711, "c": "#834417", "a": 0.441, "mid": 0.542}, {"x": 0.773, "y": 0.558, "rx": 0.464, "ry": 0.881, "c": "#977c27", "a": 0.551, "mid": 0.696}], "halo": {"scale": 1.326, "c": "#50382c", "a": 0.642, "blur": 271.012}, "blob": {"x": -0.22, "y": 0.293, "rx": 0.254, "ry": 0.748, "c": "#1c1008", "a": 0.632, "blur": 246.404}, "grain": 0.05, "grainSeed": 3, "dither": 2, "speckle": {"size": 1.6, "variety": 0.3, "coarse": 4, "contrast": 4, "blur": 0.5, "layers": [{"name": "gold shimmer", "glow": 0, "mul": [1.25, 1.2, 1.12], "k": 1, "amount": 0.34, "gain": 1.0, "seed": 5, "lum": {"lo": 0.36, "hi": 0.56, "power": 1.4, "invert": 0}}, {"name": "orange shimmer", "glow": 1, "mul": [1.2, 1.15, 1.0], "k": 1, "amount": 0.16, "gain": 0.6, "seed": 0, "lum": {"lo": 0.2, "hi": 0.46, "power": 1.2, "invert": 0}}, {"name": "dark flecks", "blob": 1, "mul": [0.75, 0.75, 0.75], "k": 1, "amount": 0.24, "gain": 1.0, "seed": 2, "lum": {"lo": 0.14, "hi": 0.4, "power": 1.0, "invert": 1}}]}, "vignette": {"a": 0.338, "power": 1.393, "c": "#140a02"}, "tiles": {"pitchX": 160.0, "pitchY": 224.9, "offX": 0, "offY": 33, "line": 2.75, "dot": 8.4, "c": "#3a2208", "opacity": 0.3}};
  function rgb(h) { h = h.replace('#', ''); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; }
  function hex(a) { return '#' + a.map(function (v) { v = Math.max(0, Math.min(255, Math.round(v))); return (v < 16 ? '0' : '') + v.toString(16); }).join(''); }
  function rgba(h, a) { var c = rgb(h); return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; }
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  /* THE SPECKLE, the glow ground's recipe (a reference video): seeded white noise plus a coarser bilinear layer for variety, thresholded by a DENSITY and sharpened by
     a contrast into specks of one colour, then blurred a little. What is new here is only where the density comes from: the bloom's own shapes are the MAP. The ochre speckle is
     densest where the ochre glow is, the crimson where the crimson glow is, and the black where the blob is (and, fainter, its halo). Nothing is speckled where the map is empty. */
  /* size and blur were chosen (the video's grain is coarser than a pixel); the strengths are fitted by tools/fit-speckle.py so the local grain matches the video's */
  var SPECKLE = {
    size: 1.6, variety: 0.2, coarse: 4, contrast: 4, blur: 0.5,
    layers: [   /* a speck is the ground's own colour at that place, made lighter or darker or redder: `mul` is its colour multiplier, `k` how far to push it (1 = as written) */
      { name: 'ochre', glow: 0, mul: [1.55, 1.45, 1.15], k: 1, amount: 1.0, gain: 1.0, seed: 5 },
      { name: 'crimson', glow: 1, mul: [1.3, 0.75, 0.8], k: 1.5, amount: 1.0, gain: 0.9, seed: 0 },
      { name: 'dark', blob: 1, mul: [0.4, 0.4, 0.4], k: 1.2, amount: 1.0, gain: 1.4, seed: 2 }
    ]
  };
  var DIM_SPECKLE = JSON.parse(JSON.stringify(SPECKLE));   /* the dim ground (f073) has about 0.4 x the grain: fitted the same way */
  DIM_SPECKLE.layers[0].k = 0.4; DIM_SPECKLE.layers[1].k = 0.5; DIM_SPECKLE.layers[2].k = 0.8;
  DIM.speckle = DIM_SPECKLE;
  function noise(cell, rnd, W, H) {   /* floats in [0,1]: white noise at `cell` px, bilinear between cells */
    var out = new Float32Array(W * H), i, x, y;
    if (cell <= 1.01) { for (i = 0; i < out.length; i++) out[i] = rnd(); return out; }
    var G = Math.max(2, Math.round(Math.max(W, H) / cell)), grid = new Float32Array(G * G), k = G / Math.max(W, H);
    for (i = 0; i < grid.length; i++) grid[i] = rnd();
    for (y = 0; y < H; y++) {
      var fy = y * k, y0 = fy | 0, ty = fy - y0, y1 = (y0 + 1) % G;
      for (x = 0; x < W; x++) {
        var fx = x * k, x0 = fx | 0, tx = fx - x0, x1 = (x0 + 1) % G;
        out[y * W + x] = (grid[y0 * G + x0] * (1 - tx) + grid[y0 * G + x1] * tx) * (1 - ty) + (grid[y1 * G + x0] * (1 - tx) + grid[y1 * G + x1] * tx) * ty;
      }
    }
    return out;
  }
  function glowField(g, u, v) {
    var r = Math.sqrt(((u - g.x) / g.rx) * ((u - g.x) / g.rx) + ((v - g.y) / g.ry) * ((v - g.y) / g.ry));
    if (r >= 1) return 0;
    return r < 0.5 ? g.a * (1 - (1 - g.mid) * (r / 0.5)) : g.a * g.mid * (1 - (r - 0.5) / 0.5);
  }
  function blobField(p, u, v) {
    var b = p.blob, h = p.halo;
    function soft(scale, blur) {
      var d = Math.sqrt(((u - b.x) / (b.rx * scale)) * ((u - b.x) / (b.rx * scale)) + ((v - b.y) / (b.ry * scale)) * ((v - b.y) / (b.ry * scale)));
      var w = Math.max(0.03, blur / (b.rx * scale * 1920));
      return 1 / (1 + Math.exp((d - 1) / (w * 0.45)));
    }
    return Math.max(b.a * soft(1, b.blur), 0.5 * h.a * soft(h.scale, h.blur));
  }
  function speckle(ctx, W, H, p, S) {
    var k = W / 1920, i, x, y, L, li, B = ctx.getImageData(0, 0, W, H).data;
    for (li = 0; li < S.layers.length; li++) {
      L = S.layers[li];
      var rnd = mulberry32((L.seed | 0) * 7919 + 17), v = Math.max(0, Math.min(1, +S.variety || 0)), c = +S.contrast || 4;
      var fine = noise(Math.max(1, S.size * k), rnd, W, H), coarse = v > 0 ? noise(Math.max(1, S.size * S.coarse * k), rnd, W, H) : null;
      var cv = document.createElement('canvas'); cv.width = W; cv.height = H;
      var cx = cv.getContext('2d'), im = cx.createImageData(W, H), d = im.data, kk = L.k == null ? 1 : L.k, m0 = 1 + (L.mul[0] - 1) * kk, m1 = 1 + (L.mul[1] - 1) * kk, m2 = 1 + (L.mul[2] - 1) * kk, dens, n, a, g = L.glow != null ? p.glows[L.glow] : null;
      for (y = 0; y < H; y++) for (x = 0; x < W; x++) {
        i = y * W + x;
        dens = (g ? glowField(g, x / W, y / H) : blobField(p, x / W, y / H)) * L.gain;
        if (L.lum) {   /* the density also follows how light the ground is HERE: a ramp from `lo` to `hi` (luminance 0-1) raised to `power`; `invert` makes it strongest in the DARK */
          var lu = (0.3 * B[i * 4] + 0.59 * B[i * 4 + 1] + 0.11 * B[i * 4 + 2]) / 255, tt = (lu - L.lum.lo) / Math.max(0.01, L.lum.hi - L.lum.lo);
          tt = tt < 0 ? 0 : tt > 1 ? 1 : tt; tt = Math.pow(tt, L.lum.power || 1); dens *= L.lum.invert ? 1 - tt : tt;
        }
        dens = dens < 0 ? 0 : dens > 1 ? 1 : dens;
        if (dens <= 0.002) continue;
        n = coarse ? fine[i] * (1 - v / 2) + coarse[i] * (v / 2) : fine[i];
        if (coarse) { n = 0.5 + (n - 0.5) * (1 + v * 1.2); n = n < 0 ? 0 : n > 1 ? 1 : n; }
        a = c * (n - ((1 + 1 / c) * (1 - dens) - 0.5 / c)) + 0.5; a = a < 0 ? 0 : a > 1 ? 1 : a;
        d[i * 4] = Math.max(0, Math.min(255, B[i * 4] * m0)); d[i * 4 + 1] = Math.max(0, Math.min(255, B[i * 4 + 1] * m1)); d[i * 4 + 2] = Math.max(0, Math.min(255, B[i * 4 + 2] * m2)); d[i * 4 + 3] = a * 255 + 0.5 | 0;
      }
      cx.putImageData(im, 0, 0);
      ctx.save(); ctx.filter = 'blur(' + ((+S.blur || 0) * k).toFixed(2) + 'px)'; ctx.globalAlpha = L.amount; ctx.drawImage(cv, 0, 0); ctx.restore();
    }
  }

  function draw(canvas, p, opts) {
    p = p || PRESET; opts = opts || {};
    var W = canvas.width, H = canvas.height, ctx = canvas.getContext('2d'), k = W / 1920;   /* blur radii are in 1920-wide pixels */
    ctx.save(); ctx.filter = 'none'; ctx.globalAlpha = 1; ctx.fillStyle = p.base; ctx.fillRect(0, 0, W, H);
    p.glows.forEach(function (g) {
      ctx.save(); ctx.translate(g.x * W, g.y * H); ctx.scale(g.rx * W, g.ry * H);
      var gr = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
      gr.addColorStop(0, rgba(g.c, g.a)); gr.addColorStop(0.5, rgba(g.c, g.a * g.mid)); gr.addColorStop(1, rgba(g.c, 0));
      ctx.fillStyle = gr; ctx.fillRect(-2, -2, 4, 4); ctx.restore();
    });
    function ell(e, scale, c, a, blur) {
      ctx.save(); ctx.filter = 'blur(' + (blur * k).toFixed(2) + 'px)'; ctx.globalAlpha = a; ctx.fillStyle = c;
      ctx.beginPath(); ctx.ellipse(e.x * W, e.y * H, e.rx * W * scale, e.ry * H * scale, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
    }
    ell(p.blob, p.halo.scale, p.halo.c, p.halo.a, p.halo.blur);
    ell(p.blob, 1, p.blob.c, p.blob.a, p.blob.blur);
    ctx.restore();
    /* DITHER: the shapes are soft gradients over near-black, and an 8-bit canvas turns those into visible bands (a blurred blob over black has only a few dozen levels to spend).
       A little triangular noise (about +-2.6 levels, independent on each channel) before anything else is drawn breaks every band into a smooth ramp. */
    if (!opts.noDither && (p.dither == null ? 2.6 : p.dither) > 0) {
      var di = ctx.getImageData(0, 0, W, H), dd = di.data, dr = mulberry32(977), da = (p.dither == null ? 2.6 : p.dither), j;
      for (j = 0; j < dd.length; j += 4) { dd[j] += (dr() + dr() - 1) * da; dd[j + 1] += (dr() + dr() - 1) * da; dd[j + 2] += (dr() + dr() - 1) * da; }
      ctx.putImageData(di, 0, 0);
    }
    if (p.vignette && !opts.noVignette) {   /* edges darken: a radial gradient from clear in the middle to `a` of a dark colour at the corners, shaped by `power` */
      var vg = p.vignette, vgr = ctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, Math.hypot(W, H) / 2);
      vgr.addColorStop(0, rgba(vg.c || '#140a02', 0)); vgr.addColorStop(Math.pow(0.5, 1 / (vg.power || 2)), rgba(vg.c || '#140a02', vg.a * 0.25)); vgr.addColorStop(1, rgba(vg.c || '#140a02', vg.a));
      ctx.save(); ctx.fillStyle = vgr; ctx.fillRect(0, 0, W, H); ctx.restore();
    }
    if (p.tiles && !opts.noTiles) {   /* a tiled floor: solid hairlines on a pitch and a solid disc where they cross, ONE colour, drawn opaque on a layer of their own and laid over with one opacity,
                                         so where a line meets a disc they do not darken twice (the golden tile reference) */
      var T = p.tiles, kk = W / 1920, px = T.pitchX * kk, py = T.pitchY * kk, ox = T.offX * kk, oy = T.offY * kk, gx, gy;
      var tl = document.createElement('canvas'); tl.width = W; tl.height = H; var tx = tl.getContext('2d');
      tx.lineWidth = Math.max(0.5, T.line * kk); tx.strokeStyle = T.c; tx.fillStyle = T.c;
      for (gx = ox; gx < W + px; gx += px) { tx.beginPath(); tx.moveTo(Math.round(gx) + 0.5, 0); tx.lineTo(Math.round(gx) + 0.5, H); tx.stroke(); }
      for (gy = oy; gy < H + py; gy += py) { tx.beginPath(); tx.moveTo(0, Math.round(gy) + 0.5); tx.lineTo(W, Math.round(gy) + 0.5); tx.stroke(); }
      for (gx = ox; gx < W + px; gx += px) for (gy = oy; gy < H + py; gy += py) { tx.beginPath(); tx.arc(Math.round(gx) + 0.5, Math.round(gy) + 0.5, T.dot * kk, 0, Math.PI * 2); tx.fill(); }
      ctx.save(); ctx.globalAlpha = T.opacity == null ? 1 : T.opacity; ctx.drawImage(tl, 0, 0); ctx.restore();
    }
    if (!opts.noSpeckle) speckle(ctx, W, H, p, p.speckle || SPECKLE);   /* ON TOP of the shapes, the vignette and the tiles */
    if (p.grain > 0 && !opts.noGrain) {   /* film grain: strong where the ground is lit, absent in the black (a grain on black is invisible in the video too) */
      var im = ctx.getImageData(0, 0, W, H), d = im.data, rnd = mulberry32(p.grainSeed | 0), i, n, l, g = p.grain * 255;
      for (i = 0; i < d.length; i += 4) {
        l = (d[i] * 0.5 + d[i + 1] * 0.35 + d[i + 2] * 0.15) / 255;
        n = (rnd() + rnd() - 1) * g * Math.pow(l, 0.6);
        d[i] += n; d[i + 1] += n * 0.7; d[i + 2] += n * 0.35;
      }
      ctx.putImageData(im, 0, 0);
    }
  }

  /* ── the fit: coordinate descent over every number, against a reference at low resolution ───────────────────── */
  function vec(p) {
    var v = [], names = [];
    function add(n, x) { names.push(n); v.push(x); }
    p.glows.forEach(function (g, i) {
      ['x', 'y', 'rx', 'ry', 'a', 'mid'].forEach(function (f) { add('g' + i + '.' + f, g[f]); });
      rgb(g.c).forEach(function (c, j) { add('g' + i + '.c' + j, c); });
    });
    ['x', 'y', 'rx', 'ry', 'a', 'blur'].forEach(function (f) { add('b.' + f, p.blob[f]); });
    ['scale', 'a', 'blur'].forEach(function (f) { add('h.' + f, p.halo[f]); });
    rgb(p.halo.c).forEach(function (c, j) { add('h.c' + j, c); });
    rgb(p.base).forEach(function (c, j) { add('base.c' + j, c); });
    add('grain', p.grain);
    if (p.vignette) { add('vg.a', p.vignette.a); add('vg.power', p.vignette.power); }
    return { v: v, names: names };
  }
  function unvec(p0, v, names) {
    var p = JSON.parse(JSON.stringify(p0)), m = {};
    names.forEach(function (n, i) { m[n] = v[i]; });
    p.glows.forEach(function (g, i) {
      ['x', 'y', 'rx', 'ry', 'a', 'mid'].forEach(function (f) { g[f] = m['g' + i + '.' + f]; });
      g.c = hex([m['g' + i + '.c0'], m['g' + i + '.c1'], m['g' + i + '.c2']]);
    });
    ['x', 'y', 'rx', 'ry', 'a', 'blur'].forEach(function (f) { p.blob[f] = m['b.' + f]; });
    ['scale', 'a', 'blur'].forEach(function (f) { p.halo[f] = m['h.' + f]; });
    p.halo.c = hex([m['h.c0'], m['h.c1'], m['h.c2']]); p.base = hex([m['base.c0'], m['base.c1'], m['base.c2']]); p.grain = m.grain;
    if (p.vignette) { p.vignette.a = m['vg.a']; p.vignette.power = m['vg.power']; }
    return p;
  }
  function clampName(n, x) {
    if (/\.(a|mid)$/.test(n)) return Math.max(0, Math.min(1, x));
    if (/\.c\d$/.test(n)) return Math.max(0, Math.min(255, x));
    if (/\.blur$/.test(n)) return Math.max(0, Math.min(400, x));
    if (/\.(rx|ry)$/.test(n)) return Math.max(0.05, Math.min(1.5, x));
    if (/\.scale$/.test(n)) return Math.max(1, Math.min(1.8, x));
    if (n === 'grain') return Math.max(0, Math.min(0.2, x));
    if (n === 'vg.a') return Math.max(0, Math.min(1, x));
    if (n === 'vg.power') return Math.max(0.5, Math.min(5, x));
    return Math.max(-0.3, Math.min(1.3, x));
  }
  function stepFor(n) { if (n === 'vg.a') return 0.05; if (n === 'vg.power') return 0.2; return /\.c\d$/.test(n) ? 12 : /\.blur$/.test(n) ? 20 : n === 'grain' ? 0.01 : /\.scale$/.test(n) ? 0.05 : 0.04; }
  /* ref: {w, h, data: Uint8ClampedArray RGBA}; mask: Uint8Array w*h (1 = compare). Grain is not fitted (it is noise): it is switched off while fitting. */
  function fit(ref, mask, start, rounds) {
    var cv = (typeof OffscreenCanvas !== 'undefined') ? new OffscreenCanvas(ref.w, ref.h) : Object.assign(document.createElement('canvas'), { width: ref.w, height: ref.h });
    function loss(p) {
      draw(cv, p, { noGrain: true, noDither: true, noTiles: true });   /* the speckle is IN the fit: its mean effect (coverage x multiplier) is what the shapes have to absorb */
      var d = cv.getContext('2d').getImageData(0, 0, ref.w, ref.h).data, s = 0, n = 0, i;
      for (i = 0; i < mask.length; i++) if (mask[i]) { s += Math.abs(d[i * 4] - ref.data[i * 4]) + Math.abs(d[i * 4 + 1] - ref.data[i * 4 + 1]) + Math.abs(d[i * 4 + 2] - ref.data[i * 4 + 2]); n++; }
      return s / (3 * Math.max(1, n));
    }
    var st = vec(start), best = loss(start), r, i, dir, trial, v, scale = 1;
    for (r = 0; r < rounds; r++) {
      for (i = 0; i < st.v.length; i++) {
        if (st.names[i] === 'grain') continue;
        for (dir = -1; dir <= 1; dir += 2) {
          v = st.v.slice(); v[i] = clampName(st.names[i], v[i] + dir * stepFor(st.names[i]) * scale);
          trial = loss(unvec(start, v, st.names));
          if (trial < best - 1e-4) { best = trial; st.v = v; break; }
        }
      }
      scale *= 0.8;
    }
    var out = unvec(start, st.v, st.names); out.grain = start.grain;
    return { p: out, loss: best };
  }
  root.AgBloom = { PRESET: PRESET, DIM: DIM, TILE: TILE, SPECKLE: SPECKLE, draw: draw, fit: fit, rgb: rgb, hex: hex };
})(window);
