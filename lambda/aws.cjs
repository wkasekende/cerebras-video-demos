'use strict';
/* SigV4 Lambda invoke over https - node's own crypto, no CLI, no SDK dep on
   the caller's side. Factored out of invoke.cjs when the gate orchestrator
   became its second consumer. */
const crypto = require('crypto'), https = require('https');
function invokeLambda(fn, region, body) {
  const creds = { id: process.env.AWS_ACCESS_KEY_ID, secret: process.env.AWS_SECRET_ACCESS_KEY,
    token: process.env.AWS_SESSION_TOKEN };
  if (!creds.id || !creds.secret) throw new Error('AWS credentials missing from the environment');
  const host = `lambda.${region}.amazonaws.com`;
  const uri = `/2015-03-31/functions/${encodeURIComponent(fn)}/invocations`;
  const now = new Date().toISOString().replace(/[-:]|\.\d{3}/g, '');
  const date = now.slice(0, 8);
  const sha = b => crypto.createHash('sha256').update(b).digest('hex');
  const hmac = (k, d) => crypto.createHmac('sha256', k).update(d).digest();
  const headers = { 'content-type': 'application/json', host,
    'x-amz-date': now, 'x-amz-log-type': 'Tail',
    ...(creds.token ? { 'x-amz-security-token': creds.token } : {}) };
  const names = Object.keys(headers).sort();
  const canon = ['POST', uri, '', ...names.map(n => `${n}:${headers[n]}`), '',
    names.join(';'), sha(body)].join('\n');
  const scope = `${date}/${region}/lambda/aws4_request`;
  const toSign = ['AWS4-HMAC-SHA256', now, scope, sha(canon)].join('\n');
  const key = hmac(hmac(hmac(hmac('AWS4' + creds.secret, date), region), 'lambda'), 'aws4_request');
  headers.authorization = `AWS4-HMAC-SHA256 Credential=${creds.id}/${scope}, ` +
    `SignedHeaders=${names.join(';')}, Signature=${crypto.createHmac('sha256', key).update(toSign).digest('hex')}`;
  return new Promise((resolve, reject) => {
    const req = https.request({ host, path: uri, method: 'POST', headers, timeout: 300000 }, res => {
      const chunks = [];
      res.on('data', c => chunks.push(c));
      res.on('end', () => resolve({
        status: res.statusCode,
        fnError: res.headers['x-amz-function-error'] || null,
        logTail: res.headers['x-amz-log-result'] || '',
        body: Buffer.concat(chunks).toString('utf8') }));
    });
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('invoke timed out')));
    req.end(body);
  });
}
module.exports = { invokeLambda };
