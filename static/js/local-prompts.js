(() => {
  'use strict';
  document.querySelectorAll('.local-prompt').forEach(dialog => {
    dialog.querySelector('[data-prompt-close]')?.addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => {
      if (event.target !== dialog) return;
      const box = dialog.getBoundingClientRect();
      if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
    });
    if (dialog.hasAttribute('data-auto-open')) dialog.showModal();
  });
  const dashboard = document.querySelector('[data-shop-dashboard]');
  const dialog = document.getElementById('product-limit-dialog');
  if (!dashboard || !dialog) return;
  dashboard.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link || Number(dashboard.dataset.productCount) < Number(dashboard.dataset.productLimit)) return;
    const path = new URL(link.href, location.href).pathname;
    if (!['/shop/products/easy/', '/shop/products/add/'].includes(path)) return;
    event.preventDefault(); dialog.showModal();
  });
})();
