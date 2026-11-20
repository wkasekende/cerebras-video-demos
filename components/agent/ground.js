/* ── THE GROUND SHADER ─────────────────────────────────────────────────────────
   A graph-paper grid pushed through SVG turbulence: the one thing the reference
   video's ground does that a plain CSS grid does not (its lines are speckled with
   grain, and can be warped). Written as an SVG filter (feTurbulence +
   feDisplacementMap + an alpha mask), not WebGL: the repo's
   render Chrome runs without a GPU and has no WebGL, and a filter is drawn by
   the same software path in a film render, a page, and an artifact.

   It is FROZEN BY CONSTRUCTION: no time input, so one parameter set is one
   picture. `seed` picks which picture; a film holds the frame you chose.

   AgGround.apply(el, params|presetName) draws into a `.ag-ground` element;
   AgGround.PRESETS are the video's two grounds; every key is a slider in the lab. */
(function (root) {
  var n = 0;
  var PRESETS = {
    /* the typing / window beats, chosen in the lab (2026-11-18, the user's final): octaves 0 means no warp, so the lines stay straight and the grain does the work */
    bright: { pitch: 38, line: 1.6, opacity: .38, soft: .75, warp: 6, warpFreq: .0005, octaves: 0, grain: 1, grainFreq: 2, seed: 0, rotate: 1 },
    /* the lockup: the bright ground's pitch, angle and softness, then fainter by eye (.28, .22, .2), then .17 (the mean brightness that matches the video's lockup), then .12 by eye (-5 points) */
    dim: { pitch: 38, line: 1.6, opacity: .12, soft: .75, warp: 6, warpFreq: .0005, octaves: 0, grain: 1, grainFreq: 2, seed: 0, rotate: 1 }
  };
  var KEYS = Object.keys(PRESETS.bright);

  function build(el) {
    var id = 'agt' + (++n);
    el.innerHTML =
      '<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><filter id="' + id + '" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">' +
      '<feGaussianBlur class="b" in="SourceGraphic" stdDeviation="0.6" result="bl"/>' +
      '<feTurbulence class="w" type="fractalNoise" result="wn"/>' +
      '<feDisplacementMap class="d" in="bl" in2="wn" xChannelSelector="R" yChannelSelector="G" result="wp"/>' +
      '<feTurbulence class="g" type="fractalNoise" numOctaves="1" result="gn"/>' +
      '<feColorMatrix class="gm" in="gn" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1" result="ga"/>' +
      '<feComposite in="wp" in2="ga" operator="in"/></filter></svg>' +
      '<div class="ag-grid" style="filter:url(#' + id + ')"><div class="ag-grid-in"></div></div>';
    el.classList.add('ag-ground-js');
  }

  function apply(el, p) {
    if (typeof p === 'string') p = PRESETS[p];
    p = Object.assign({}, PRESETS.bright, p || {});
    if (!el.querySelector('filter')) build(el);
    var q = function (c) { return el.querySelector('.' + c); };
    q('w').setAttribute('baseFrequency', p.warpFreq); q('w').setAttribute('numOctaves', Math.max(1, Math.round(p.octaves))); q('w').setAttribute('seed', p.seed);
    /* octaves 0 is "no turbulence": the spec makes a zero-octave primitive transparent black, which would shove the whole grid by half the scale, so the warp is switched off instead */
    q('d').setAttribute('scale', Math.round(p.octaves) > 0 ? p.warp : 0);
    /* soften: the displacement map moves whole pixels, so a 1.6 px line steps; a little blur first keeps it smooth */
    q('b').setAttribute('stdDeviation', p.soft);
    q('g').setAttribute('baseFrequency', p.grainFreq); q('g').setAttribute('seed', p.seed + 3);
    /* alpha = 1 + g * (2.5 R - 1.25): the dark half of the noise punches speckles out of the lines, the rest leaves them whole */
    q('gm').setAttribute('values', '0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 ' + (2.5 * p.grain) + ' 0 0 0 ' + (1 - 1.25 * p.grain));
    var g = q('ag-grid-in');
    g.style.setProperty('--g-pitch', p.pitch + 'px'); g.style.setProperty('--g-w', p.line + 'px'); g.style.setProperty('--g-a', p.opacity);
    /* ROTATE: the grid lines turn about the stage's centre; the noise does not (it is the filter's, on the unrotated box), so the grain stays crisp at any angle */
    var D = Math.ceil(Math.hypot(el.clientWidth || 2400, el.clientHeight || 2400)) + 120;
    g.style.width = g.style.height = D + 'px'; g.style.marginLeft = g.style.marginTop = (-D / 2) + 'px';
    g.style.transform = 'rotate(' + (p.rotate || 0) + 'deg)';
    el.__agParams = p;
    return p;
  }

  /* ── GLOW GRAIN: the glow ground is a plain LIGHT-TO-DARK GRADIENT (CSS; `from` / `to` are where it leaves the light colour and reaches the dark one,
     `angle` its direction), with RED SPECKLE on top. The speckle is a seeded random mask (below); a fade along the same diagonal (`redFrom`, `redTo`)
     runs its strength out where the gradient should show. Frozen like the shader: no time input. ── */
  var SPECK = { light: '#ef9a30', dark: '#0a0000', red: '#bd2417', from: 0, to: 100, angle: 145, redAmount: 1, redFrom: 100, redTo: 100, redFloor: 0, darkAmount: 0, dark2: '#2a0705', darkDensity: .4, liteAmount: 0, liteColor: '#f0a030', liteMid: 0, liteEdgeA: .97, liteEdgeB: 0, clusterFollow: 0, cluster: 0, clusterEdgeB: null, darkEdgeA: null, darkEdgeB: null, clusterEdge: .85, clusterMid: .12, clusterReach: 45, clusterGamma: 1.2,
    size: 1, density: .88, contrast: 24.5, seed: 0, variety: .21, coarse: 9.5, blur: 1.5, blend: 'normal' };
  /* size: a speck's width in px (1 = every pixel on its own). variety: how much of a COARSER noise (size x coarse) is mixed into the fine one.
     blur: px, after the noise mask. redFrom / redTo: along the diagonal (%), where the red starts to fade and where it is gone (100 and 100 = no fade). */
  var WINDOW = Object.assign({}, SPECK, { light: '#db571f', dark: '#1c0303', red: '#a21d0b', from: 30, to: 57, angle: 130, redAmount: 1, redFrom: 56, redTo: 80, redFloor: 0, size: 1, density: .69, contrast: 4, variety: .52, coarse: 5.5, blur: 2 });
  var GLOW = {
    /* THE USER'S SETTINGS (2026-11-19, from the lab, after the layers were reversed): a gradient from #db571f to #1c0303 across a 130-degree diagonal, leaving the
       light colour at 30% and reaching the dark at 57%, with #a21d0b speckle at full strength from the light end to 56% of the way and gone by 80%. */
    window: WINDOW,                                                                                          /* typing, window */
    /* the claim and the lockup keep their own dark CSS bases (the video's are not this gradient) but take the same tuned GRAIN: red, density, edge, variety, blur;
       no fade along the diagonal, and a faint strength, because the speckle is the only thing on a near-black ground */
    /* THE USER'S TYPING GROUND (2026-11-19, from the lab): the gradient #db571f to #1c0303 across 130 degrees (30% to 57%); red speckle flat across the page at .86 (corners
       .69); a light speckle (#f0a030, .9) clustered to 1.0 at the top-left; a dark one (#120202, .9) clustered to 1.0 at the bottom-right; each cluster fades over its own 45%
       of the diagonal (follow 0); blur 1.5. In the pages artifact every page that shows the gradient ground uses it. */
    typing: Object.assign({}, WINDOW, { light:'#db571f', dark:'#1c0303', red:'#a21d0b', from:30, to:57, angle:116, redAmount:1, redFrom:100, redTo:100, redFloor:0,
      darkAmount:.9, dark2:'#120202', darkDensity:0, darkEdgeA:0, darkEdgeB:1,
      liteAmount:.8, liteColor:'#f0a030', liteMid:0, liteEdgeA:1, liteEdgeB:0,
      clusterFollow:0, cluster:1, clusterEdge:.69, clusterEdgeB:.69, clusterMid:.86, clusterReach:45, clusterGamma:1.2,
      size:1, density:.69, contrast:4, seed:0, variety:.52, coarse:5.5, blur:1.5, blend:'normal', shift:15, clusterAngle:116 }),
    claim: Object.assign({}, WINDOW, { redAmount: .15, redFrom: 100, redTo: 100 }),                           /* near-black claim ground (its base is CSS) */
    lockup: Object.assign({}, WINDOW, { redAmount: .25, redFrom: 100, redTo: 100 })                           /* "powered by" ground (its base is CSS) */
  };
  /* EVERY glow ground uses the user's typing preset (2026-11-19, 'apply to all'): the window beats, the claim and the lockup. The claim and the lockup keep their own dark CSS bases beneath it. */
  GLOW.window = Object.assign({}, GLOW.typing); GLOW.claim = Object.assign({}, GLOW.typing); GLOW.lockup = Object.assign({}, GLOW.typing);

  /* THE SPECK MASK. Not SVG turbulence: thresholded Perlin noise is a maze of one feature size on a visible lattice, and film grain is not.
     Here the field is SEEDED WHITE NOISE (mulberry32), every cell independent; a coarser layer of the same, bilinearly smoothed, is mixed in
     for variety; the sum is thresholded (density) and sharpened (contrast) into an alpha mask. Drawn once per parameter set in a 2D canvas
     (no GPU), cached, and installed as one CSS class, so a page of grounds shares one image. */
  var TILE = 768, masks = {}, sheet = null;
  function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  function layer(cell, rnd, WW, HH) {   /* WW x HH floats in [0,1] (default TILE x TILE): white noise at `cell` px, bilinear between cells, wrapping so the tile repeats seamlessly */
    WW = WW || TILE; HH = HH || TILE;
    var out = new Float32Array(WW * HH), G = Math.max(2, Math.round(Math.max(WW, HH) / cell)), grid = new Float32Array(G * G), i, x, y;
    for (i = 0; i < grid.length; i++) grid[i] = rnd();
    if (cell <= 1.01) { for (i = 0; i < out.length; i++) out[i] = rnd(); return out; }
    var k = G / Math.max(WW, HH);
    for (y = 0; y < HH; y++) {
      var fy = y * k, y0 = fy | 0, ty = fy - y0, y1 = (y0 + 1) % G;
      for (x = 0; x < WW; x++) {
        var fx = x * k, x0 = fx | 0, tx = fx - x0, x1 = (x0 + 1) % G;
        var a = grid[y0 * G + x0], b = grid[y0 * G + x1], c = grid[y1 * G + x0], d = grid[y1 * G + x1];
        out[y * WW + x] = (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty;
      }
    }
    return out;
  }
  function maskClass(p, seed) {
    var v = Math.max(0, Math.min(1, +p.variety || 0)), key = [p.size, p.density, p.contrast, seed, v, p.coarse].join('|');
    if (masks[key]) return masks[key];
    var rnd = mulberry32(+seed * 7919 + 17), fine = layer(Math.max(1, +p.size), rnd), coarse = v > 0 ? layer(Math.max(1, +p.size * +p.coarse), rnd) : null;
    var cv = document.createElement('canvas'); cv.width = cv.height = TILE;
    var cx = cv.getContext('2d'), im = cx.createImageData(TILE, TILE), d = im.data, thr = 1 - +p.density, c = +p.contrast, i, n, a;
    for (i = 0; i < fine.length; i++) {
      n = coarse ? fine[i] * (1 - v / 2) + coarse[i] * (v / 2) : fine[i];
      /* a mix of two uniforms is bunched toward .5; stretch it about the middle so density keeps meaning what it says */
      if (coarse) n = 0.5 + (n - 0.5) * (1 + v * 1.2);
      a = c * (n - thr) + 0.5; a = a < 0 ? 0 : a > 1 ? 1 : a;
      d[i * 4 + 3] = a * 255 + 0.5 | 0;
    }
    cx.putImageData(im, 0, 0);
    var cls = 'agm' + Object.keys(masks).length;
    if (!sheet) { sheet = document.createElement('style'); document.head.appendChild(sheet); }
    sheet.appendChild(document.createTextNode('.' + cls + '{--sp-noise:url("' + cv.toDataURL('image/png') + '")}'));
    return (masks[key] = cls);
  }
  /* A CLUSTERED mask: one image the size of the whole ground, whose DENSITY varies along the diagonal: densest at both ends (the top-left and bottom-right corners),
     thinning to `clusterMid` toward the middle. An opacity fade only makes specks fainter; this makes them sparser, which is what a cluster is. Same noise as above
     (seeded white noise plus the coarse layer), thresholded per pixel by the density at that pixel's place along the diagonal. */
  function maskFull(p, seed, WW, HH, prof) {   /* prof: { mid, edgeA (top-left end), edgeB (bottom-right end) }: the density in the middle and at each end of the diagonal */
    var key = ['full', WW, HH, p.size, p.contrast, seed, p.variety, p.coarse, (p.clusterAngle == null ? p.angle : p.clusterAngle), prof.mid, prof.edgeA, prof.edgeB, p.clusterReach, p.clusterGamma, p.clusterFollow, p.from, p.to, p.shift].join('|');
    if (masks[key]) return masks[key];
    var v = Math.max(0, Math.min(1, +p.variety || 0)), rnd = mulberry32(+seed * 7919 + 17);
    var fine = layer(Math.max(1, +p.size), rnd, WW, HH), coarse = v > 0 ? layer(Math.max(1, +p.size * +p.coarse), rnd, WW, HH) : null;
    var th = (+(p.clusterAngle == null ? p.angle : p.clusterAngle)) * Math.PI / 180, sx = Math.sin(th), sy = -Math.cos(th), Lg = Math.abs(WW * sx) + Math.abs(HH * sy);
    var eA = +prof.edgeA, eB = +prof.edgeB, mid = +prof.mid, reach = Math.max(.01, +p.clusterReach / 100), gam = +p.clusterGamma || 1, c = +p.contrast;
    var sh = (+p.shift || 0) / 100, follow = +p.clusterFollow > 0, gf = (+p.from) / 100, gt = (+p.to) / 100, fA, fB, sm;
    var cv = document.createElement('canvas'); cv.width = WW; cv.height = HH;
    var cx = cv.getContext('2d'), im = cx.createImageData(WW, HH), d = im.data, x, y, i, n, a, t, f, dens;
    for (y = 0; y < HH; y++) for (x = 0; x < WW; x++) {
      i = y * WW + x;
      t = ((x - WW / 2) * sx + (y - HH / 2) * sy) / Lg + 0.5;
      t = sh ? (t < .5 ? t * (.5 + sh) / .5 : .5 + sh + (t - .5) * (.5 - sh) / .5) : t;   /* SHIFT: the middle slides along the axis, the two ends stay put, so the corners keep their full density */                 /* 0 at the light end of the diagonal, 1 at the dark end */
      if (follow) { sm = (t - gf) / Math.max(.01, gt - gf); sm = sm < 0 ? 0 : sm > 1 ? 1 : sm; sm = sm * sm * (3 - 2 * sm); fA = 1 - sm; fB = sm; }   /* follow the GRADIENT: one end full until it starts to leave its colour (from), gone where the gradient has reached the other (to), and the other end the reverse: they cross-fade where the colours do */
      else { fA = Math.pow(Math.max(1 - t / reach, 0), gam); fB = Math.pow(Math.max(1 - (1 - t) / reach, 0), gam); }   /* or each end rises over its own `reach` */
      dens = mid + (eA - mid) * fA + (eB - mid) * fB;
      dens = dens < 0 ? 0 : dens > 1 ? 1 : dens;
      n = coarse ? fine[i] * (1 - v / 2) + coarse[i] * (v / 2) : fine[i];
      if (coarse) { n = 0.5 + (n - 0.5) * (1 + v * 1.2); n = n < 0 ? 0 : n > 1 ? 1 : n; }   /* the stretch can leave [0,1]; clamp it, or the strongest values slip past a zero-density threshold */
      /* density 0 must be NO specks and density 1 ALL of them: with a threshold of (1 - density) the strongest few percent of the noise still got through at 0, so a layer never
         reached zero and the light speckle leaked into the dark corner (and the dark into the light one). This threshold puts 0 above any noise value and 1 below. */
      a = c * (n - ((1 + 1 / c) * (1 - dens) - 0.5 / c)) + 0.5; a = a < 0 ? 0 : a > 1 ? 1 : a;
      d[i * 4 + 3] = a * 255 + 0.5 | 0;
    }
    cx.putImageData(im, 0, 0);
    var cls = 'agm' + Object.keys(masks).length;
    if (!sheet) { sheet = document.createElement('style'); document.head.appendChild(sheet); }
    /* a ground-sized mask is megabytes as a data URL, and a declaration that large is silently dropped: serve it as a blob URL, and keep the layer hidden
       until the blob exists (a layer with no mask is a solid colour). AgGround.pending counts the blobs still being made. */
    pending++; waiters[cls] = [];
    cv.toBlob(function (blob) {
      sheet.appendChild(document.createTextNode('.' + cls + '{--sp-noise:url("' + URL.createObjectURL(blob) + '")}'));
      ready[cls] = true; (waiters[cls] || []).forEach(function (el) { el.classList.add('agm-ok'); }); delete waiters[cls]; pending--;
    }, 'image/png');
    return (masks[key] = cls);
  }
  var pending = 0, ready = {}, waiters = {};
  function show(el, cls) {   /* the layer shows once its mask is ready; the small data-URL masks are ready at once */
    el.classList.remove('agm-ok');
    if (ready[cls] !== false && !waiters[cls]) { el.classList.add('agm-ok'); } else (waiters[cls] = waiters[cls] || []).push(el);
  }
  function applyGlow(el, p) {
    if (typeof p === 'string') p = GLOW[p];
    p = Object.assign({}, GLOW.window, p || {});
    if (!el.querySelector('.ag-sp')) {
      el.insertAdjacentHTML('beforeend', '<div class="ag-sp"><div class="ag-blurbox"><div class="ag-speck"></div></div></div>');
    }
    var L = el.querySelector('.ag-sp');
    if (L.agMask) L.classList.remove(L.agMask);
    var WW = el.offsetWidth || parseInt(el.style.width, 10) || 1920, HH = el.offsetHeight || parseInt(el.style.height, 10) || 1080, clustered = +p.cluster > 0;
    var eB = p.clusterEdgeB == null ? p.clusterEdge : p.clusterEdgeB;
    L.agMask = clustered ? maskFull(p, +p.seed, WW, HH, { mid: p.clusterMid, edgeA: p.clusterEdge, edgeB: eB }) : maskClass(p, +p.seed); L.classList.add(L.agMask); show(L, L.agMask);
    el.style.setProperty('--speck-tw', clustered ? WW + 'px' : ''); el.style.setProperty('--speck-th', clustered ? HH + 'px' : '');
    if (+p.darkAmount > 0) {   /* the optional darker speckle: its own noise (another seed, its own density) */
      var B = el.querySelector('.ag-sp-b');
      if (!B) { el.insertAdjacentHTML('beforeend', '<div class="ag-sp ag-sp-b"><div class="ag-blurbox"><div class="ag-speck"></div></div></div>'); B = el.querySelector('.ag-sp-b'); }
      if (B.agMask) B.classList.remove(B.agMask);
      B.agMask = clustered ? maskFull(p, +p.seed + 2, WW, HH, { mid: p.darkDensity, edgeA: p.darkEdgeA == null ? p.darkDensity : p.darkEdgeA, edgeB: p.darkEdgeB == null ? p.darkDensity : p.darkEdgeB })
                           : maskClass(Object.assign({}, p, { density: p.darkDensity }), +p.seed + 2);
      B.classList.add(B.agMask); show(B, B.agMask);
    }
    if (+p.liteAmount > 0) {   /* the LIGHT colour's own speckle layer, clustered at the top-left (the dark one clusters at the bottom-right): each corner nearly full of its own colour */
      var C = el.querySelector('.ag-sp-c');
      if (!C) { el.insertAdjacentHTML('beforeend', '<div class="ag-sp ag-sp-c"><div class="ag-blurbox"><div class="ag-speck"></div></div></div>'); C = el.querySelector('.ag-sp-c'); }
      if (C.agMask) C.classList.remove(C.agMask);
      C.agMask = clustered ? maskFull(p, +p.seed + 5, WW, HH, { mid: p.liteMid, edgeA: p.liteEdgeA, edgeB: p.liteEdgeB }) : maskClass(Object.assign({}, p, { density: p.liteMid }), +p.seed + 5);
      C.classList.add(C.agMask); show(C, C.agMask);
    }
    el.style.setProperty('--lite-amount', +p.liteAmount || 0); el.style.setProperty('--speck-lite', p.liteColor);
    el.style.setProperty('--dark-amount', +p.darkAmount || 0); el.style.setProperty('--speck-dark2', p.dark2); el.style.setProperty('--red-floor', p.redFloor);
    var set = function (k, v) { el.style.setProperty(k, v); };
    set('--glow-light', p.light); set('--glow-dark', p.dark); set('--glow-from', (+p.from + (+p.shift || 0)) + '%'); set('--glow-to', (+p.to + (+p.shift || 0)) + '%');
    set('--speck-red', p.red); set('--red-amount', p.redAmount); set('--red-from', p.redFrom + '%'); set('--red-to', p.redTo + '%'); set('--red-floor', p.redFloor);
    set('--grain-blend', p.blend); set('--speck-tile', TILE + 'px'); set('--speck-angle', p.angle + 'deg');
    set('--speck-blur', (+p.blur || 0) + 'px'); set('--speck-pad', Math.ceil((+p.blur || 0) * 3) + 'px');
    el.classList.add('ag-glow-js');
    el.__agGlow = p;
    return p;
  }
  /* BLOOM: the fourth video's ground, drawn once per preset into an offscreen canvas (bloom.js) and copied into each ground element's own canvas */
  var bloomCache = {};
  function bloomGround(el, which) {
    if (!root.AgBloom) return;
    var WW = el.offsetWidth || 1920, HH = el.offsetHeight || 1080, key = which + WW + 'x' + HH;
    if (!bloomCache[key]) { var oc = document.createElement('canvas'); oc.width = WW; oc.height = HH; root.AgBloom.draw(oc, root.AgBloom[which]); bloomCache[key] = oc; }
    var cv = el.querySelector('canvas');
    if (!cv) { cv = document.createElement('canvas'); el.appendChild(cv); }
    cv.width = WW; cv.height = HH; cv.getContext('2d').drawImage(bloomCache[key], 0, 0);
  }
  function mount1(el) {
    /* the shader is the ember theme's ground; paper (dots) and glow (gradient) draw theirs in CSS */
    var th = el.closest('.ag');
    if (th && th.dataset.theme === 'glow') { applyGlow(el, (el.dataset.glow && GLOW[el.dataset.glow]) ? el.dataset.glow : th.dataset.kind === 'claim' ? 'claim' : th.dataset.kind === 'lockup' ? 'lockup' : 'window'); return; }
    if (th && th.dataset.theme === 'bloom') { bloomGround(el, th.dataset.kind === 'claim' || th.dataset.kind === 'lockup' ? 'DIM' : 'PRESET'); return; }
    if (th && th.dataset.theme === 'tile') { bloomGround(el, 'TILE'); return; }
    if (th && th.dataset.theme !== 'ember') return;
    apply(el, el.dataset.ground);
  }
  /* ONLY WHERE IT IS SEEN: a ground builds its masks / shader the first time it comes within 300 px of the viewport, and while it is off screen its heavy layers
     (the speckle layers with their blur, the shader's filtered grid) are display:none (.ag-off, in agent.css), so a page of thirty grounds paints the two or three in view. */
  var io = ('IntersectionObserver' in root) ? new IntersectionObserver(function (es) {
    es.forEach(function (e) {
      var el = e.target;
      if (e.isIntersecting) { if (!el.__agMounted) { el.__agMounted = 1; mount1(el); } el.classList.remove('ag-off'); }
      else el.classList.add('ag-off');
    });
  }, { rootMargin: '300px' }) : null;
  function mountAll(scope) {
    (scope || document).querySelectorAll('.ag-ground[data-ground]').forEach(function (el) {
      if (!io) { mount1(el); return; }
      if (el.__agWatched) return; el.__agWatched = 1; el.classList.add('ag-off'); io.observe(el);
    });
  }
  root.AgGround = { get pending() { return pending; }, PRESETS: PRESETS, KEYS: KEYS, apply: apply, GLOW: GLOW, applyGlow: applyGlow, mountAll: mountAll };
})(window);
