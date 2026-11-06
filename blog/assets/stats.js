(() => {
  const counters = [...document.querySelectorAll('[data-blog-views]')];
  const totals = [...document.querySelectorAll('[data-blog-total]')];
  if (!counters.length || document.documentElement.dataset.blogStatsLoaded) return;
  document.documentElement.dataset.blogStatsLoaded = 'true';

  // Current endpoint used by https://busuanzi.9420.ltd/js.
  // API contract: https://github.com/soxft/busuanzi/wiki/API
  const api = 'https://bsz.iirose.cn/api';
  const origin = 'https://tianxingchen.github.io';
  const article = document.body.dataset.blogArticle;
  const ids = [...new Set(counters.map(node => node.dataset.blogViews))]
    .filter(id => /^[a-zA-Z0-9][a-zA-Z0-9-]*$/.test(id));

  function show(nodes, value) {
    for (const node of nodes) {
      const english = node.closest('[lang]')?.lang === 'en';
      node.textContent = value === null ? '—' : value.toLocaleString(english ? 'en-US' : 'zh-CN');
      node.title = value === null
        ? (english ? 'View count temporarily unavailable' : '访问量暂不可用')
        : (english ? 'Page views since tracking began; both languages combined' : '自统计启用起累计，中英文合并计数');
      node.removeAttribute('aria-label');
    }
  }

  async function request(id, method) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(api, {
        method,
        headers: { 'x-bsz-referer': `${origin}/blog/${id}.html` },
        credentials: 'omit',
        referrerPolicy: 'no-referrer',
        cache: 'no-store',
        signal: controller.signal,
      });
      if (!response.ok) throw new Error('Counter request failed');
      const result = await response.json();
      const count = result?.data?.page_pv;
      if (result.success !== true || !Number.isSafeInteger(count) || count < 0) {
        throw new Error('Invalid counter response');
      }
      return count;
    } finally {
      clearTimeout(timeout);
    }
  }

  async function load() {
    // Lists and local previews only read counts. Each live article load records
    // one PV, with the Chinese canonical URL also used by its translation.
    const live = location.origin === origin;
    const results = await Promise.all(ids.map(async id => {
      const nodes = counters.filter(node => node.dataset.blogViews === id);
      const method = live && article === id ? 'POST' : 'GET';
      try {
        let count;
        try {
          count = await request(id, method);
        } catch (error) {
          // Never retry a write: the server may already have counted it.
          if (method !== 'POST') throw error;
          count = await request(id, 'GET');
        }
        show(nodes, count);
        return count;
      } catch {
        show(nodes, null);
        return null;
      }
    }));
    // Sum only articles, excluding the homepage and blog listing. Never show
    // a misleading partial total when an individual count is unavailable.
    show(totals, results.every(value => value !== null)
      ? results.reduce((sum, value) => sum + value, 0) : null);
  }

  function startWhenVisible() {
    if (document.visibilityState === 'hidden') {
      const onVisible = () => {
        if (document.visibilityState !== 'hidden') {
          document.removeEventListener('visibilitychange', onVisible);
          startWhenVisible();
        }
      };
      document.addEventListener('visibilitychange', onVisible);
      return;
    }
    const homepageSection = document.getElementById('blog');
    if (!article && homepageSection && 'IntersectionObserver' in window) {
      const observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) {
          observer.disconnect();
          load();
        }
      }, { rootMargin: '200px' });
      observer.observe(homepageSection);
    } else {
      load();
    }
  }
  startWhenVisible();
})();
