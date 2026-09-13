const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../apps/public/consumer.js'), 'utf8');
const routes = {
  '/discover-assets/assets/media/manifest.json': {assets: [], policy: {}},
  '/v1/public/videos': {videos: []},
  '/v1/public/feed': {cards: []},
  '/v1/audience/preview': {cards: []},
};
const tick = () => new Promise(resolve => setImmediate(resolve));

async function fixture({search = '', responses = {}, postOK = true, rejectPost = false} = {}) {
  const status = {textContent: ''};
  function element() {
    return {
      innerHTML: '', textContent: '', listeners: {}, open: false,
      addEventListener(kind, handler) { this.listeners[kind] = handler; },
      querySelector() { return status; },
      showModal() { this.open = true; }, close() { this.open = false; },
    };
  }
  const elements = Object.fromEntries(['#feed', '#panel', '#panelContent', '#closePanel', '#aboutButton', '#openSources'].map(key => [key, element()]));
  const requests = [];
  const context = vm.createContext({
    document: {querySelector: key => elements[key]},
    location: {hostname: 'production.example', search},
    URLSearchParams, AbortController, setTimeout, clearTimeout,
    crypto: {randomUUID: () => 'fixture-session'}, sessionStorage: {},
    console: {info() {}, warn() {}, error() {}},
    fetch: async (url, options = {}) => {
      requests.push({url, options});
      if (options.method === 'POST') {
        if (rejectPost) throw new Error('transport unavailable');
        return {ok: postOK, status: postOK ? 202 : 503};
      }
      const value = Object.hasOwn(responses, url) ? responses[url] : routes[url];
      if (value instanceof Error) throw value;
      return {ok: value !== null, status: value === null ? 503 : 200, json: async () => value};
    },
  });
  vm.runInContext(source, context);
  await tick();
  return {context, elements, requests, status};
}

test('public empty feed does not send readers to administration', async () => {
  const {elements, requests} = await fixture();
  assert.match(elements['#feed'].innerHTML, /First stories are on the way/);
  assert.doesNotMatch(elements['#feed'].innerHTML, /PRIVATE PREVIEW|content studio|admin workspace/i);
  assert.ok(requests.some(request => request.url === '/v1/public/feed'));
  assert.ok(!requests.some(request => request.url === '/v1/audience/preview'));
});

test('explicit preview keeps the operator next step separate', async () => {
  const {elements, requests} = await fixture({search: '?preview=1'});
  assert.match(elements['#feed'].innerHTML, /PRIVATE PREVIEW/);
  assert.match(elements['#feed'].innerHTML, /\/operator#generate/);
  assert.ok(requests.some(request => request.url === '/v1/audience/preview'));
});

test('unavailable feed is not presented as empty or as a local restart request', async () => {
  const {elements} = await fixture({responses: {'/v1/public/feed': null}});
  assert.match(elements['#feed'].innerHTML, /Stories are temporarily unavailable/);
  assert.match(elements['#feed'].innerHTML, /data-retry-feed/);
  assert.doesNotMatch(elements['#feed'].innerHTML, /503|LOCAL PREVIEW|content studio|First stories are on the way/);
});

test('valid owned videos still render when optional card and image requests fail', async () => {
  const {elements} = await fixture({responses: {
    '/v1/public/videos': {videos: [{package_id: 'video-1', title: 'A useful story', summary: 'Evidence', video_url: '/owned/video.mp4', poster_url: ''}]},
    '/v1/public/feed': null,
    '/discover-assets/assets/media/manifest.json': null,
  }});
  assert.match(elements['#feed'].innerHTML, /<video/);
  assert.match(elements['#feed'].innerHTML, /A useful story/);
});

test('valid cards still render when the video service is unavailable', async () => {
  const {elements} = await fixture({responses: {
    '/v1/public/videos': null,
    '/v1/public/feed': {cards: [{card_id: 'card-1', title: 'A clear comparison', claims: []}]},
  }});
  assert.match(elements['#feed'].innerHTML.replace(/<[^>]*>/g, ''), /A clear comparison/);
});

test('malformed response is unavailable, not a fabricated empty success', async () => {
  const {elements} = await fixture({responses: {'/v1/public/feed': {cards: 'wrong type'}}});
  assert.match(elements['#feed'].innerHTML, /Stories are temporarily unavailable/);
});

test('failed feedback response is not accepted as success', async () => {
  const {context, requests} = await fixture({postOK: false});
  const result = await context.interaction({card_id: 'card-1'}, 'comment', 'Please add a source.');
  assert.equal(result.ok, false);
  assert.equal(requests.filter(request => request.options.method === 'POST').length, 1);
});

test('network failure is not retried or reported as accepted', async () => {
  const {context, requests} = await fixture({rejectPost: true});
  const result = await context.videoInteraction({package_id: 'video-1'}, 'like');
  assert.equal(result.ok, false);
  assert.equal(requests.filter(request => request.options.method === 'POST').length, 1);
});

test('comment stays editable when acceptance cannot be confirmed', async () => {
  const {context, elements, status} = await fixture({postOK: false});
  vm.runInContext('cards = [{card_id: "card-1"}]', context);
  const input = {value: 'Please retain this correction.'};
  const button = {disabled: false};
  await elements['#panel'].listeners.submit({preventDefault() {}, target: {
    elements: {comment: input}, dataset: {commentCard: 'card-1'}, querySelector: () => button,
  }});
  assert.equal(input.value, 'Please retain this correction.');
  assert.match(status.textContent, /Could not confirm/);
  assert.equal(button.disabled, false);
});

test('successful comment receives moderation acknowledgement only after acceptance', async () => {
  const {context, elements, status, requests} = await fixture();
  vm.runInContext('cards = [{card_id: "card-1"}]', context);
  const input = {value: 'A useful question'};
  const button = {disabled: false};
  await elements['#panel'].listeners.submit({preventDefault() {}, target: {
    elements: {comment: input}, dataset: {commentCard: 'card-1'}, querySelector: () => button,
  }});
  assert.equal(input.value, '');
  assert.match(status.textContent, /Submitted for moderation/);
  const body = JSON.parse(requests.find(request => request.options.method === 'POST').options.body);
  assert.equal(body.card_id, 'card-1');
  assert.equal(body.text, 'A useful question');
});
