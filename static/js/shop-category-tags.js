(() => {
  document.querySelectorAll('[data-category-picker]').forEach(root => {
    const value = root.querySelector('[data-category-value]');
    const selected = root.querySelector('[data-category-selected]');
    const dropdown = root.querySelector('[data-category-select]');
    const options = [...dropdown.querySelectorAll('[data-category-option]')];
    const custom = root.querySelector('[data-category-custom]');
    const status = root.querySelector('[data-category-status]');
    const t = (key, params = {}) => window.LocalfromProductLanguage?.t(key, params) || key.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? `{${name}}`));
    let tags = [];
    const parse = text => text.split(/[,\n]/).map(tag => tag.trim()).filter(Boolean);
    const unique = items => items.filter((tag, index) => items.findIndex(other => other.toLowerCase() === tag.toLowerCase()) === index);
    function render() {
      selected.replaceChildren();
      tags.forEach(tag => {
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = `${t(tag)} \u00d7`;
        remove.setAttribute('aria-label', t('Remove {name}', {name:t(tag)}));
        remove.onclick = () => { tags = tags.filter(item => item !== tag); save(); };
        selected.append(remove);
      });
      options.forEach(option => {
        option.textContent = t(option.value);
        option.disabled = tags.some(tag => tag.toLowerCase() === option.value.toLowerCase());
      });
      dropdown.options[0].textContent = t('Choose a category');
      dropdown.value = '';
      dropdown.disabled = tags.length >= 5;
      status.textContent = t('{number} of 5 categories selected', {number:tags.length});
    }
    function save() {
      value.value = tags.join(', ');
      value.dispatchEvent(new Event('change', {bubbles:true}));
    }
    function add(names) {
      const next = unique([...tags, ...names]);
      if (next.length > 5 || next.join(', ').length > 100) {
        status.textContent = t('Choose up to 5 categories, within 100 characters in total.');
        return false;
      }
      tags = next; save(); return true;
    }
    value.addEventListener('change', () => { tags = unique(parse(value.value)); render(); });
    value.addEventListener('input', () => { tags = unique(parse(value.value)); render(); });
    dropdown.addEventListener('change', () => {
      if (dropdown.value) add([dropdown.value]);
      dropdown.value = '';
    });
    function addCustom() { if (add(parse(custom.value))) custom.value = ''; }
    root.querySelector('[data-category-add]').onclick = addCustom;
    custom.addEventListener('keydown', event => {
      if (event.key === 'Enter') { event.preventDefault(); addCustom(); }
    });
    custom.closest('form')?.addEventListener('submit', event => {
      if (custom.value.trim() && !add(parse(custom.value))) event.preventDefault();
    });
    const fieldLabel = value.labels?.[0];
    if (fieldLabel) fieldLabel.htmlFor = dropdown.id;
    value.classList.add('category-value-hidden'); value.tabIndex = -1;
    root.querySelector('[data-category-enhanced]').hidden = false;
    tags = unique(parse(value.value)); render();
    document.addEventListener('product-language-change', render);
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render, {once:true});
  });
})();
