document.addEventListener('submit', async event => {
  const form = event.target.closest('.business-follow-form');
  if (!form) return;
  event.preventDefault();
  const endpoint = form.getAttribute('action');
  const forms = [...document.querySelectorAll('.business-follow-form')].filter(item => item.getAttribute('action') === endpoint);
  const buttons = forms.map(item => item.querySelector('button[name=action]'));
  const button = form.querySelector('button[name=action]');
  const data = new FormData(form);
  data.set('action', button.value);
  buttons.forEach(item => { item.disabled = true; });
  try {
    const response = await fetch(endpoint, {method:'POST', body:data, credentials:'same-origin', headers:{'X-Requested-With':'XMLHttpRequest'}});
    if (response.redirected) { location.assign(response.url); return; }
    if (!response.ok) throw new Error('Could not update follow');
    const result = await response.json();
    buttons.forEach(item => {
      item.value = result.following ? 'unfollow' : 'follow';
      item.setAttribute('aria-pressed', String(result.following));
      item.textContent = result.following ? 'Following' : '+ Follow';
    });
    document.querySelectorAll('[data-business-followers]').forEach(element => {
      if (element.dataset.businessFollowers === endpoint) element.textContent = result.followers;
    });
  } catch (_) { alert('Could not update your follow. Please try again.'); }
  finally { buttons.forEach(item => { item.disabled = false; }); }
}, true);
