(() => {
  const panel = document.querySelector('[data-shop-share]');
  if (!panel) return;
  const status = panel.querySelector('[data-share-status]');
  const translate = text => window.LocalfromProductLanguage?.t?.(text) || text;
  const input = panel.querySelector('#shop-share-link');
  panel.querySelector('[data-copy-shop]').addEventListener('click', async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error();
      await navigator.clipboard.writeText(panel.dataset.url);
      status.textContent = translate('Shop link copied.');
    } catch (_) {
      input.focus(); input.select();
      status.textContent = translate('Select and copy your shop link.');
    }
  });
  const share = panel.querySelector('[data-native-share]');
  if (navigator.share) {
    share.hidden = false;
    share.addEventListener('click', async () => {
      try {
        await navigator.share({title: panel.dataset.title, text: panel.dataset.title + ' on Local From', url: panel.dataset.url});
      } catch (error) {
        if (error.name !== 'AbortError') status.textContent = translate('Use WhatsApp or copy the shop link below.');
      }
    });
  }
})();
