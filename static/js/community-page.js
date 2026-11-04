(() => {
  const form = document.getElementById('communityPostForm');
  if (form) {
    form.addEventListener('submit', event => {
      const message = form.querySelector('[name=content]').value.replace(/[\s\u200b\ufeff]/g, '');
      const files = form.querySelector('[name=image]').files;
      const error = document.getElementById('communityPostError');
      error.hidden = !!(message || files.length);
      if (!error.hidden) { event.preventDefault(); form.querySelector('[name=content]').focus(); }
    });
  }
  const state = document.getElementById('communityMembershipState');
  if (!state) return;
  async function refresh() {
    if (document.hidden) return;
    try {
      const response = await fetch(state.dataset.url, {cache:'no-store', headers:{Accept:'application/json'}});
      if (!response.ok || !response.headers.get('content-type').includes('application/json')) return;
      const data = await response.json();
      document.querySelectorAll('[data-community-count]').forEach(element => { element.textContent = data.member_count; });
    } catch (error) { /* The server-rendered count remains available offline. */ }
  }
  window.addEventListener('pageshow', refresh);
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', refresh);
  refresh();
})();
