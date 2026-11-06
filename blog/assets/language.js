(() => {
  const switches = document.querySelectorAll('[data-language-switch]');
  function syncSection() {
    switches.forEach(link => { link.hash = window.location.hash; });
  }
  syncSection();
  window.addEventListener('hashchange', syncSection);
})();
