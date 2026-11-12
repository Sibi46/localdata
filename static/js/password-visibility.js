(() => {
  'use strict';
  if (window.localfromPasswordVisibilityReady) return;
  window.localfromPasswordVisibilityReady = true;
  let nextId = 0;
  const controls = [];
  function update(input, button, visible) {
    const selection = [input.selectionStart, input.selectionEnd];
    input.type = visible ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(visible));
    button.setAttribute('aria-label', visible ? 'Hide password' : 'Show password');
    button.title = visible ? 'Hide password' : 'Show password';
    button.querySelector('[data-eye-slash]').toggleAttribute('hidden', !visible);
    try { input.setSelectionRange(...selection); } catch (_) {}
  }
  function start() {
    document.querySelectorAll('input[type="password"]').forEach(input => {
      if (input.closest('.password-visibility-field')) return;
      // The older recovery screen already supplies its own eye control.
      if (input.parentElement.querySelector('[onclick*="fpToggle"]')) return;
      if (!input.id) {
        do { input.id = `localfrom-password-${++nextId}`; } while (document.querySelectorAll(`[id="${input.id}"]`).length > 1);
      }
      const old = document.querySelector(`[data-admin-password-toggle][aria-controls="${CSS.escape(input.id)}"]`);
      const button = old || document.createElement('button');
      button.removeAttribute('data-admin-password-toggle');
      button.removeAttribute('style');
      button.type = 'button';
      button.className = 'password-visibility-toggle';
      button.disabled = input.disabled;
      button.setAttribute('aria-controls', input.id);
      button.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/><path d="m3 3 18 18" data-eye-slash hidden/></svg>';
      const wrap = document.createElement('span');
      wrap.className = 'password-visibility-field';
      input.before(wrap);
      wrap.append(input, button);
      update(input, button, false);
      button.addEventListener('click', () => update(input, button, input.type === 'password'));
      controls.push({input, button});
    });
  }
  function hide() { controls.forEach(({input, button}) => update(input, button, false)); }
  document.addEventListener('submit', hide, true);
  window.addEventListener('pagehide', hide);
  document.addEventListener('visibilitychange', () => { if (document.hidden) hide(); });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})();
