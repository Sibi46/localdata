(function () {
  'use strict';
  const pending = new Map();
  function lookup(pin) {
    if (!pending.has(pin)) {
      pending.set(pin, fetch('/api/pincode/' + pin + '/', {credentials: 'same-origin'})
        .then(response => response.ok ? response.json() : null)
        .then(data => data && data.success ? data : null)
        .catch(() => null));
    }
    return pending.get(pin);
  }
  function label(data) {
    return [...new Set([data.area, data.district, data.state].filter(Boolean))].join(', ');
  }
  document.querySelectorAll('[data-area-name]').forEach(async node => {
    const pin = node.dataset.areaName;
    if (!/^[1-9][0-9]{5}$/.test(pin)) return;
    const data = await lookup(pin);
    if (data) node.textContent = node.hasAttribute('data-area-compact')
      ? (data.city || data.area || data.district) + ' \u00b7 ' + pin
      : label(data) + ' (' + pin + ')';
  });
  document.querySelectorAll('[data-area-lookup]').forEach(input => {
    const hint = document.createElement('small');
    hint.id = input.id + '-area-name';
    hint.setAttribute('role', 'status');
    hint.style.cssText = 'display:block;flex-basis:100%;margin:6px 0;line-height:1.5';
    input.insertAdjacentElement('afterend', hint);
    input.setAttribute('aria-describedby', hint.id);
    async function update() {
      const pin = input.value.trim();
      hint.textContent = '';
      if (!/^[1-9][0-9]{5}$/.test(pin)) return;
      hint.textContent = 'Finding your area…';
      const data = await lookup(pin);
      if (input.value.trim() !== pin) return;
      hint.textContent = data ? label(data) : 'Area name unavailable. You can still explore using this pincode.';
    }
    input.addEventListener('input', update);
    update();
  });
})();
