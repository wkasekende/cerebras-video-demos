#!/usr/bin/env node
/* ── A STAND-IN SCREEN RECORDING, MADE BY CODE ───────────────────────────────────────────────────────────────────
     node tools/standin-clip.mjs --kind docs|dashboard|code [--seconds 24] [--fps 24] [--out file.mp4]

   For trying the pop-in template without a recording of your own: a generic, brand-free web page (an API reference that scrolls and highlights, a support dashboard whose bars and numbers move, a code review
   whose diff scrolls and whose tests stream) is drawn by a real Chrome frame by frame, as a pure function of the time, and encoded 1280 x 720 (16:9). Nothing in them is a real company's page. */
import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';
import { launch } from './chrome.mjs';

const argv = process.argv.slice(2);
const opt = (n, d) => { const i = argv.indexOf('--' + n); return i >= 0 ? argv[i + 1] : d; };
const kind = opt('kind', 'docs'), seconds = +opt('seconds', 24), fps = +opt('fps', 24), out = path.resolve(opt('out', `out/standin-${kind}.mp4`));
if (!['docs', 'dashboard', 'code'].includes(kind)) { console.error('--kind docs|dashboard|code'); process.exit(2); }

const css = `*{box-sizing:border-box}html,body{margin:0;width:1280px;height:720px;overflow:hidden;font-family:Inter,'Helvetica Neue',Arial,sans-serif;color:#1f2933;background:#f6f7f9}
.bar{height:44px;background:#fff;border-bottom:1px solid #e3e6ea;display:flex;align-items:center;padding:0 22px;gap:14px;font-size:14px;color:#52606d}.bar b{color:#1f2933}
.dot{width:10px;height:10px;border-radius:50%;background:#d0d5db}.cur{position:absolute;width:16px;height:16px;border-radius:50%;background:rgba(32,96,224,.35);border:2px solid #2060e0;z-index:9}
.side{position:absolute;left:0;top:44px;width:240px;bottom:0;background:#fff;border-right:1px solid #e3e6ea;padding:22px 20px;font-size:14px;line-height:2.1;color:#52606d}.side div.on{color:#2060e0;font-weight:600}
.main{position:absolute;left:240px;right:0;top:44px;bottom:0;overflow:hidden}.in{padding:34px 56px;max-width:900px}
h1{font-size:30px;margin:0 0 6px}h2{font-size:21px;margin:34px 0 8px}p{font-size:15.5px;line-height:1.65;margin:0 0 12px;color:#3e4c59}code{background:#e9edf2;padding:1px 6px;border-radius:4px;font-size:13.5px}
.hl{background:linear-gradient(transparent 55%,#fff1a8 55%)}table{border-collapse:collapse;width:100%;font-size:14px;margin:10px 0 18px}td,th{text-align:left;padding:8px 12px;border-bottom:1px solid #e3e6ea}th{color:#7b8794;font-weight:600;font-size:12px;text-transform:uppercase}
.card{background:#fff;border:1px solid #e3e6ea;border-radius:12px;padding:18px 22px}.kpi{font-size:34px;font-weight:700}.sub{font-size:13px;color:#7b8794}.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:12px;background:#e6f6ed;color:#13804a}.pill.r{background:#fdecea;color:#c0392b}
pre{margin:0;font:13px/1.65 'SFMono-Regular',Menlo,Consolas,monospace}.add{background:#e6ffed}.del{background:#ffeef0}.ln{color:#9aa5b1;display:inline-block;width:40px;text-align:right;margin-right:14px}`;

const docsBody = () => {
  const sec = (title, text, rows) => `<h2>${title}</h2><p>${text}</p>` + (rows ? `<table><tr><th>Plan</th><th>Requests / min</th><th>Burst</th></tr>${rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join('')}</table>` : '');
  return `<h1>Rate limits</h1><p>How requests are counted, what happens at the limit, and how to retry. Last updated this week.</p>`
    + sec('How requests are counted', 'Every request to <code>/v1/*</code> is counted against your <span class="hl" id="a">workspace, not the key</span>, in one-minute windows. Batch calls count once per batch, not once per item.', [['Starter', '60', '10'], ['Team', '600', '100'], ['Scale', '6,000', '1,000']])
    + sec('When you reach the limit', 'The API answers <code>429</code> with a <code>Retry-After</code> header in seconds. <span class="hl" id="b">Requests are never silently dropped</span>; they are refused, and the refusal is not billed.')
    + sec('Retrying safely', 'Use exponential backoff with jitter, starting at the <code>Retry-After</code> value. Idempotent calls carry an <code>Idempotency-Key</code> header, so a retry after a timeout cannot run twice. <span class="hl" id="c">Keys are remembered for 24 hours.</span>')
    + sec('Limits that are not per minute', 'File uploads are limited to 200 MB each and 2 GB a day. <span class="hl" id="d">Long-running jobs count once when they start.</span> Webhooks retry for up to three days with growing gaps.', [['Uploads / day', '2 GB', '200 MB each'], ['Jobs in flight', '20', '5 starting at once']])
    + sec('Asking for more', 'Limits are raised on request for workspaces with a track record. Include the workspace id and a week of peak traffic. We answer within a business day.')
    + sec('Status and history', 'Every change to these numbers is written to the changelog with its date. Nothing here changes without notice.');
};
const codeBody = () => {
  const L = (n, t, c = '') => `<div class="${c}"><span class="ln">${n}</span>${t}</div>`;
  const lines = [
    L(41, 'def charge(customer, amount_cents, key):'), L(42, '    if amount_cents &lt;= 0:'), L(43, '        raise ValueError("amount must be positive")'),
    L(44, '-   return gateway.create(customer, amount_cents)', 'del'), L(45, '+   existing = ledger.find(customer, key)', 'add'), L(46, '+   if existing:', 'add'), L(47, '+       return existing', 'add'),
    L(48, '+   charge = gateway.create(customer, amount_cents, idempotency_key=key)', 'add'), L(49, '+   ledger.record(customer, key, charge)', 'add'), L(50, '+   return charge', 'add'), L(51, ''),
    L(52, 'def refund(customer, charge_id):'), L(53, '    charge = ledger.get(charge_id)'), L(54, '-   gateway.refund(charge.id)', 'del'), L(55, '+   gateway.refund(charge.id, reason="requested_by_customer")', 'add'), L(56, '+   ledger.mark_refunded(charge.id)', 'add'),
    L(57, ''), L(58, 'def webhook(event):'), L(59, '    if event.type == "charge.failed":'), L(60, '-       notify(event.customer)', 'del'), L(61, '+       notify(event.customer, retry_after=event.retry_after)', 'add'),
    L(62, ''), L(63, 'def sweep():'), L(64, '    for c in ledger.pending():'), L(65, '        charge(c.customer, c.amount, c.key)'), L(66, ''), L(67, '# runs hourly'), L(68, 'if __name__ == "__main__":'), L(69, '    sweep()')];
  return `<div class="card" style="margin:22px 28px;padding:0;overflow:hidden"><div style="padding:12px 20px;border-bottom:1px solid #e3e6ea;font-size:14px"><b>billing/charges.py</b> <span class="sub">&nbsp; +9 &minus;3</span></div><div style="height:430px;overflow:hidden;position:relative"><pre id="diff" style="position:absolute;left:0;right:0">${lines.join('')}</pre></div></div>
  <div class="card" style="margin:0 28px;padding:14px 20px"><div class="sub" style="margin-bottom:6px">Tests</div><pre id="tests" style="height:96px;overflow:hidden"></pre></div>`;
};
const dashBody = () => `<div style="padding:26px 34px"><div style="display:flex;gap:18px;margin-bottom:18px">
  <div class="card" style="flex:1"><div class="sub">Open tickets</div><div class="kpi" id="k1">0</div><span class="pill r" id="p1">+0 today</span></div>
  <div class="card" style="flex:1"><div class="sub">Median first reply</div><div class="kpi" id="k2">0 min</div><span class="pill" id="p2">on target</span></div>
  <div class="card" style="flex:1"><div class="sub">Resolved this week</div><div class="kpi" id="k3">0</div><span class="pill">+12%</span></div></div>
  <div style="display:flex;gap:18px"><div class="card" style="flex:1.4;height:330px"><div class="sub">Tickets by day</div><div id="bars" style="display:flex;align-items:flex-end;gap:16px;height:270px;padding-top:12px"></div></div>
  <div class="card" style="flex:1;height:330px;overflow:hidden"><div class="sub" style="margin-bottom:8px">Newest</div><div id="rows"></div></div></div></div>`;

const html = `<!doctype html><meta charset=utf-8><style>${css}</style><div class="bar"><span class="dot"></span><span class="dot"></span><span class="dot"></span><span style="margin-left:14px"><b>${kind === 'docs' ? 'Acme API' : kind === 'code' ? 'Review' : 'Support'}</b> &nbsp;/&nbsp; ${kind === 'docs' ? 'Reference' : kind === 'code' ? 'billing/charges.py' : 'Queue'}</span></div>
${kind === 'docs' ? '<div class="side"><div>Overview</div><div>Authentication</div><div class="on">Rate limits</div><div>Errors</div><div>Webhooks</div><div>Idempotency</div><div>Changelog</div></div>' : ''}
<div class="main" style="${kind === 'docs' ? '' : 'left:0'}"><div class="in" id="in" style="${kind === 'docs' ? '' : 'max-width:none;padding:0'}">${kind === 'docs' ? docsBody() : kind === 'code' ? codeBody() : dashBody()}</div></div><div class="cur" id="cur"></div>
<script>
const KIND=${JSON.stringify(kind)}, D=${seconds * 1000}, ease=t=>t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2, clamp=v=>Math.max(0,Math.min(1,v));
const inEl=document.getElementById('in'), cur=document.getElementById('cur');
const tests=['collecting 14 items','test_charge_positive ........ ok','test_charge_idempotent ...... ok','test_charge_duplicate_key ... ok','test_refund_marks_ledger .... ok','test_webhook_retry_after .... ok','test_sweep_hourly ........... ok','14 passed in 2.31s'];
const days=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], vals=[62,71,58,88,76,34,41];
const names=['Billing: double charge','Login: SSO loop','Export: CSV timeout','Invite: link expired','API: 429 on batch','Billing: invoice copy','Mobile: crash on open','Docs: broken link'];
window.render=function(ms){
  const t=clamp(ms/D);
  if(KIND==='docs'){ const max=inEl.scrollHeight-640; inEl.style.transform='translateY('+(-ease(t)*max)+'px)';
    ['a','b','c','d'].forEach((id,i)=>{const e=document.getElementById(id), p=clamp((t-.12-i*.2)/.1); e.style.backgroundSize='100% '+(p*100)+'%'; e.style.background='linear-gradient(transparent 55%,#fff1a8 55%) no-repeat 0 0 / '+(p*100)+'% 100%';});
    cur.style.left=(300+300*Math.sin(t*9))+'px'; cur.style.top=(260+160*Math.cos(t*7))+'px'; }
  if(KIND==='code'){ const el=document.getElementById('diff'); el.style.transform='translateY('+(-ease(clamp(t*1.4))*140)+'px)';
    const n=Math.floor(clamp((t-.35)/.5)*tests.length); document.getElementById('tests').textContent=tests.slice(0,n).join('\\n');
    cur.style.left=(180+700*clamp(t*1.6))+'px'; cur.style.top=(150+90*Math.sin(t*8))+'px'; }
  if(KIND==='dash'||KIND==='dashboard'){ const e=ease(clamp(t*1.6));
    document.getElementById('k1').textContent=Math.round(184*e); document.getElementById('p1').textContent='+'+Math.round(23*e)+' today'; document.getElementById('k2').textContent=Math.max(12.4,142-129.6*e).toFixed(1)+' min'; document.getElementById('k3').textContent=Math.round(1312*e).toLocaleString('en-US');
    document.getElementById('bars').innerHTML=days.map((d,i)=>{const p=clamp((t*1.6-i*.07)/.4);return '<div style="flex:1;text-align:center"><div style="height:'+(vals[i]*2.6*ease(p))+'px;background:#2060e0;border-radius:6px 6px 0 0"></div><div class="sub" style="margin-top:6px">'+d+'</div></div>'}).join('');
    const k=Math.floor(clamp((t-.15)/.7)*names.length); document.getElementById('rows').innerHTML=names.slice(0,k).reverse().map((n,i)=>'<div style="padding:9px 0;border-bottom:1px solid #e3e6ea;font-size:14px">'+n+' <span class="sub" style="float:right">'+(i+1)+'m</span></div>').join('');
    cur.style.left=(400+400*Math.sin(t*6))+'px'; cur.style.top=(200+200*Math.cos(t*5))+'px'; }
};
</script>`;

fs.mkdirSync(path.dirname(out), { recursive: true });
const tmp = fs.mkdtempSync(path.join(process.env.TMPDIR || '/tmp', 'standin-'));
fs.writeFileSync(path.join(tmp, 'p.html'), html);
const browser = await launch(); const pg = await browser.newPage(); await pg.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
await pg.goto('file://' + path.join(tmp, 'p.html')); await new Promise(r => setTimeout(r, 400));
const n = Math.round(seconds * fps);
for (let i = 0; i < n; i++) { await pg.evaluate(t => window.render(t), i * 1000 / fps); await pg.screenshot({ path: path.join(tmp, String(i + 1).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 92 }); }
await browser.close();
const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-framerate', String(fps), '-i', path.join(tmp, '%05d.jpg'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', out], { stdio: 'inherit' });
fs.rmSync(tmp, { recursive: true, force: true });
if (r.status !== 0) process.exit(1);
console.log(`wrote ${out} (${kind}, ${seconds} s, ${fps} fps)`);
