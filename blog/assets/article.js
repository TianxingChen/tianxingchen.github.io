(() => {
  const english = document.documentElement.lang === 'en';
  const sidebar = document.querySelector('.article-sidebar');
  if (!sidebar) return;

  const toggle = sidebar.querySelector('.toc-toggle');
  const links = Array.from(sidebar.querySelectorAll('.article-toc a'));
  const entries = links.map(link => ({
    link,
    target: document.getElementById(decodeURIComponent(link.hash.slice(1)))
  })).filter(entry => entry.target);
  const desktop = window.matchMedia('(min-width: 70rem)');
  toggle.hidden = false;

  function setExpanded(expanded) {
    toggle.setAttribute('aria-expanded', String(expanded));
    toggle.querySelector('span').textContent = english
      ? (expanded ? 'Collapse −' : 'Expand +')
      : (expanded ? '收起 −' : '展开 +');
  }
  toggle.addEventListener('click', () => {
    setExpanded(toggle.getAttribute('aria-expanded') !== 'true');
  });
  links.forEach(link => link.addEventListener('click', () => {
    if (!desktop.matches) setExpanded(false);
  }));

  function updateCurrent() {
    let current = entries[0];
    for (const entry of entries) {
      if (entry.target.getBoundingClientRect().top <= 128) current = entry;
    }
    if (window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 4) {
      current = entries[entries.length - 1];
    }
    for (const entry of entries) {
      if (entry === current) entry.link.setAttribute('aria-current', 'location');
      else entry.link.removeAttribute('aria-current');
    }
  }

  let scheduled = false;
  function scheduleUpdate() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      updateCurrent();
      scheduled = false;
    });
  }
  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', scheduleUpdate);
  window.addEventListener('load', scheduleUpdate);
  updateCurrent();
})();
