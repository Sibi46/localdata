(() => {
  const indicator = document.querySelector('[data-error-indicator]');
  if (!indicator) return;
  async function refresh() {
    if (document.hidden) return;
    try {
      const response = await fetch(indicator.dataset.feed, {credentials: 'same-origin', headers: {'Accept': 'application/json'}});
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error();
      const data = await response.json();
      if (!Number.isInteger(data.open_count)) throw new Error();
      indicator.textContent = data.open_count ? `Site errors: ${data.open_count} unresolved` : 'Site errors: all clear';
      indicator.classList.toggle('has-errors', data.open_count > 0);
    } catch (_) {
      indicator.textContent = 'Site errors: status unavailable';
    }
  }
  setInterval(refresh, 30000);
  document.addEventListener('visibilitychange', refresh);
})();
