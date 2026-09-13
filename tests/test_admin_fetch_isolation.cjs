const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../apps/operator/admin-auth.js'), 'utf8');
const origin = 'https://application.example';
const tick = () => new Promise(resolve => setImmediate(resolve));

function fixture({authenticated = false} = {}) {
  const calls = [];
  const current = {email: 'admin@example.invalid', getIdToken: async () => 'fixture-id-token'};
  const nativeFetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url || input.href;
    calls.push({url, init});
    if (url === '/v1/admin-auth/config') {
      if (!authenticated) return new Promise(() => {});
      return {ok: true, json: async () => ({required: true, configured: true, firebase: {}})};
    }
    return {ok: true, json: async () => ({})};
  };
  const auth = {
    onAuthStateChanged(callback) { Promise.resolve().then(() => callback(current)); },
    signOut: async () => {},
  };
  const window = {fetch: nativeFetch};
  const context = vm.createContext({
    window, URL, Headers, Request,
    location: {origin, href: origin + '/operator#domain'},
    document: {
      querySelector: () => null,
      createElement: () => ({}),
      head: {appendChild(script) { script.onload(); }},
    },
    firebase: {apps: [{}], auth: () => auth},
    navigator: {},
  });
  vm.runInContext(source, context);
  return {window, calls};
}

async function promptly(promise) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('Request incorrectly waited for app authentication')), 200);
    })]);
  } finally { clearTimeout(timer); }
}

test('Google authentication request does not wait for application login', async () => {
  const {window, calls} = fixture();
  await promptly(window.fetch('https://identitytoolkit.googleapis.com/v1/accounts:signInWithIdp', {method: 'POST'}));
  assert.equal(calls.length, 2);
  assert.equal(calls[1].init.headers, undefined);
});

test('external Request and URL inputs retain native fetch behavior', async () => {
  const {window, calls} = fixture();
  await promptly(window.fetch(new Request('https://provider.example/v1/resource')));
  await promptly(window.fetch(new URL('https://provider.example/v1/resource')));
  assert.equal(calls.length, 3);
});

test('application API stays gated until authentication is ready', async () => {
  const {window, calls} = fixture();
  window.fetch('/v1/objects').catch(() => {});
  await tick();
  assert.equal(calls.length, 1);
});

test('asset query containing an API substring is not an API request', async () => {
  const {window, calls} = fixture();
  await promptly(window.fetch('/operator/app.js?next=/v1/objects'));
  assert.equal(calls.length, 2);
});

test('exact public configuration endpoint remains available', async () => {
  const {window, calls} = fixture();
  await promptly(window.fetch(origin + '/v1/admin-auth/config?fresh=1'));
  assert.equal(calls.length, 2);
});

test('configuration substring does not exempt a protected path', async () => {
  const {window, calls} = fixture();
  window.fetch('/v1/objects?next=/v1/admin-auth/config').catch(() => {});
  await tick();
  assert.equal(calls.length, 1);
});

test('authenticated application request receives token and retains its headers', async () => {
  const {window, calls} = fixture({authenticated: true});
  await tick();
  await promptly(window.fetch('/v1/objects', {headers: {'x-workspace-action': '1'}}));
  const headers = calls.at(-1).init.headers;
  assert.equal(headers.get('Authorization'), 'Bearer fixture-id-token');
  assert.equal(headers.get('x-workspace-action'), '1');
});

test('authenticated session does not inject app token into a foreign request', async () => {
  const {window, calls} = fixture({authenticated: true});
  await tick();
  await promptly(window.fetch('https://provider.example/v1/resource'));
  assert.equal(calls.at(-1).init.headers, undefined);
});
