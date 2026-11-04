(() => {
  'use strict';
  const comment = document.querySelector('.nd #id_text');
  const counter = document.querySelector('[data-character-count]');
  if (comment && counter) {
    const update = () => { counter.textContent = `${Array.from(comment.value).length} / 160`; };
    comment.addEventListener('input', update);
    update();
  }
  document.querySelectorAll('[data-share]').forEach(button => {
    button.addEventListener('click', async () => {
      const status = document.querySelector('.nd-share-status');
      const url = new URL(window.location.href);
      url.search = '';
      url.hash = '';
      try {
        if (navigator.share) {
          await navigator.share({title: button.dataset.title, url: url.href});
        } else if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(url.href);
          status.textContent = 'Link copied. Ready to share!';
        } else {
          status.textContent = `Copy this link to share: ${url.href}`;
        }
      } catch (error) {
        if (error.name !== 'AbortError') status.textContent = `Copy this link to share: ${url.href}`;
      }
    });
  });
})();
