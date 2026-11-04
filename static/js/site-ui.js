(() => {
  function start() {
    const toggle = document.querySelector('[data-account-theme]');
    if (toggle) {
      const update = () => {
        const dark = document.documentElement.dataset.theme === 'dark';
        toggle.setAttribute('aria-pressed', String(dark));
        toggle.textContent = dark ? 'Use light mode' : 'Use dark mode';
      };
      toggle.addEventListener('click', () => {
        const theme = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.dataset.theme = theme;
        try { localStorage.setItem('opc-theme', theme); } catch (_) {}
        update();
      });
      update();
    }
    document.body.classList.toggle('opc-has-nav', !!document.querySelector('.opc-bottom-nav'));
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
