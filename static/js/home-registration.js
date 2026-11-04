// Let visitors see the home page, then invite them to join when they explore.
(() => {
  const allowed = ['/register/', '/login/', '/super-admin/login/', '/privacy/', '/terms/'];
  function register(event, next = '/') {
    event.preventDefault();
    event.stopImmediatePropagation();
    const params = new URLSearchParams({next});
    window.location.assign('/register/?' + params);
  }
  document.addEventListener('click', event => {
    const control = event.target.closest('a, button, input[type="submit"]');
    if (!control || control.closest('.skip-link')) return;
    let next = '/';
    if (control.matches('a')) {
      const url = new URL(control.href, location.href);
      if (url.protocol === 'mailto:' || url.protocol === 'tel:') return;
      if (url.origin === 'https://www.instagram.com' && url.pathname === '/local_from97/') return;
      if (url.origin === location.origin && allowed.includes(url.pathname)) return;
      if (url.origin === location.origin) next = url.pathname + url.search;
    }
    register(event, next);
  }, true);
  document.addEventListener('submit', event => {
    const url = new URL(event.target.action, location.href);
    if (event.target.method.toLowerCase() === 'get') {
      url.search = new URLSearchParams(new FormData(event.target)).toString();
    }
    register(event, url.pathname + url.search);
  }, true);
})();
