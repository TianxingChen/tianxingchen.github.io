const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../blog/assets/stats.js'), 'utf8');
const flush = () => new Promise(resolve => setImmediate(resolve));

function setup({ ids = ['first', 'second'], article, live = true, language = 'zh-CN', hidden = false, homepage = false, response } = {}) {
  const calls = [];
  const node = id => ({
    dataset: { blogViews: id }, textContent: '—', title: '',
    closest: () => ({ lang: language }), removeAttribute() {},
  });
  const counters = ids.map(node);
  const total = node();
  const listeners = new Map();
  const document = {
    documentElement: { dataset: {} }, body: { dataset: { blogArticle: article } },
    visibilityState: hidden ? 'hidden' : 'visible',
    querySelectorAll: selector => selector === '[data-blog-views]' ? counters : [total],
    getElementById: () => homepage ? {} : null,
    addEventListener: (name, fn) => listeners.set(name, fn),
    removeEventListener: name => listeners.delete(name),
  };
  let intersect;
  const context = vm.createContext({
    document, window: homepage ? { IntersectionObserver: true } : {},
    location: { origin: live ? 'https://tianxingchen.github.io' : 'http://127.0.0.1:8765' },
    AbortController, setTimeout, clearTimeout,
    IntersectionObserver: class {
      constructor(callback) { intersect = callback; }
      observe() {}
      disconnect() {}
    },
    fetch: async (url, options) => {
      calls.push({ url, ...options });
      if (response) return response(options, calls.length);
      return { ok: true, json: async () => ({ success: true, data: { page_pv: 12 } }) };
    },
  });
  const run = () => vm.runInContext(source, context);
  run();
  return { calls, counters, total, document, listeners, run, intersect: () => intersect([{ isIntersecting: true }]) };
}

test('listing reads each article once and sums article views only', async () => {
  const app = setup({ ids: ['first', 'second', 'first'] });
  await flush();
  assert.deepEqual(app.calls.map(call => call.method), ['GET', 'GET']);
  assert.deepEqual(app.counters.map(node => node.textContent), ['12', '12', '12']);
  assert.equal(app.total.textContent, '24');
  app.run();
  await flush();
  assert.equal(app.calls.length, 2, 'duplicate script must not record more requests');
});

test('both language versions increment the same canonical article once', async () => {
  for (const language of ['zh-CN', 'en']) {
    const app = setup({ ids: ['eai-definition-first'], article: 'eai-definition-first', language });
    await flush();
    assert.equal(app.calls.length, 1);
    assert.equal(app.calls[0].method, 'POST');
    assert.equal(app.calls[0].headers['x-bsz-referer'], 'https://tianxingchen.github.io/blog/eai-definition-first.html');
    assert.equal(app.calls[0].credentials, 'omit');
    assert.equal(app.calls[0].referrerPolicy, 'no-referrer');
  }
});

test('local article preview never increments live counts', async () => {
  const app = setup({ ids: ['first'], article: 'first', live: false });
  await flush();
  assert.deepEqual(app.calls.map(call => call.method), ['GET']);
});

test('an uncertain write is followed only by a read, never another write', async () => {
  const app = setup({ ids: ['first'], article: 'first', response: async options => {
    if (options.method === 'POST') throw new Error('Connection lost after write');
    return { ok: true, json: async () => ({ success: true, data: { page_pv: 13 } }) };
  } });
  await flush();
  assert.deepEqual(app.calls.map(call => call.method), ['POST', 'GET']);
  assert.equal(app.counters[0].textContent, '13');
});

test('unavailable or invalid counts do not become zero or a partial total', async () => {
  for (const invalid of [-1, null, '12', 1.5]) {
    const app = setup({ response: async (_, call) => ({
      ok: true, json: async () => ({ success: true, data: { page_pv: call === 1 ? 12 : invalid } }),
    }) });
    await flush();
    assert.equal(app.counters[0].textContent, '12');
    assert.equal(app.counters[1].textContent, '—');
    assert.equal(app.total.textContent, '—');
    assert.equal(app.total.title, '访问量暂不可用');
  }
});

test('hidden pages wait for visibility and homepage waits for the Blog section', async () => {
  const hidden = setup({ hidden: true, ids: ['first'], article: 'first' });
  assert.equal(hidden.calls.length, 0);
  hidden.document.visibilityState = 'visible';
  hidden.listeners.get('visibilitychange')();
  await flush();
  assert.equal(hidden.calls.length, 1);
  const homepage = setup({ homepage: true });
  assert.equal(homepage.calls.length, 0);
  homepage.intersect();
  await flush();
  assert.deepEqual(homepage.calls.map(call => call.method), ['GET', 'GET']);
});
