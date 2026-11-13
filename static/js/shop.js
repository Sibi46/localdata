(() => {
  document.querySelectorAll('input[type="file"][multiple]').forEach(input => {
    const count = document.createElement('p');
    count.className = 'upload-image-status';
    count.setAttribute('aria-live', 'polite');
    input.insertAdjacentElement('afterend', count);
    const updateCount = () => {
      const total = input.files.length;
      count.textContent = `${total} image${total === 1 ? '' : 's'} selected`;
    };
    input.addEventListener('change', updateCount);
    updateCount();
  });
  const dashboard = document.querySelector('[data-shop-dashboard]');
  if (dashboard) {
    const sections = [...dashboard.querySelectorAll('.dashboard-section')];
    const links = [...dashboard.querySelectorAll('[data-dashboard-link]')];
    let firstSelection = true;
    const selectSection = () => {
      const requested = document.getElementById(location.hash.slice(1));
      const errorSection = firstSelection ? dashboard.querySelector('.form-error-summary')?.closest('.dashboard-section') : null;
      const section = errorSection || requested?.closest('.dashboard-section') || sections[0];
      firstSelection = false;
      sections.forEach(panel => { panel.hidden = panel !== section; });
      links.forEach(link => {
        if (link.hash === `#${section.id}`) link.setAttribute('aria-current', 'true');
        else link.removeAttribute('aria-current');
      });
    };
    window.addEventListener('hashchange', selectSection);
    selectSection();
  }
  document.querySelectorAll('[data-confirm-delete]').forEach(form => {
    form.addEventListener('submit', event => {
      if (!window.confirm(form.dataset.confirmDelete)) event.preventDefault();
    });
  });
  document.querySelector('[data-catalog-sort]')?.addEventListener('change', event => event.target.form.requestSubmit());
  const price = document.getElementById('id_price');
  const discount = document.getElementById('id_discount_percent');
  const preview = document.querySelector('[data-sale-price]');
  if (price && discount && preview) {
    const updatePrice = () => {
      const regular = Number(price.value) || 0;
      const percent = Math.min(100, Math.max(0, Number(discount.value) || 0));
      preview.textContent = new Intl.NumberFormat('en-IN', {style: 'currency', currency: 'INR'}).format(regular * (100 - percent) / 100);
    };
    [price, discount].forEach(input => input.addEventListener('input', updatePrice));
    updatePrice();
  }
})();
