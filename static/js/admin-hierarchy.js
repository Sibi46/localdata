(() => {
  const filters = document.getElementById('team-filters');
  const names = ['country', 'state', 'district', 'area'];
  if (filters) names.forEach((name, index) => {
    const field = filters.elements[name];
    if (field && name !== 'area') field.addEventListener('change', () => {
      names.slice(index + 1).forEach(child => { if (!filters.elements[child].disabled) filters.elements[child].value = ''; });
      filters.requestSubmit();
    });
  });
  const form = document.getElementById('create-admin-form');
  if (!form || form.elements.level.value !== 'it') return;
  const country = form.elements.country, state = form.elements.state;
  let serial = 0;
  country.addEventListener('change', async () => {
    const current = ++serial;
    state.replaceChildren(new Option('Loading states...', ''));
    try {
      const response = await fetch(form.dataset.statesUrl + '?country=' + encodeURIComponent(country.value));
      if (!response.ok) throw new Error('Unavailable');
      const data = await response.json();
      if (current !== serial) return;
      state.replaceChildren(new Option('Select state', ''));
      data.states.forEach(item => state.add(new Option(item.name, item.id)));
    } catch (_) { if (current === serial) state.replaceChildren(new Option('Could not load states. Select country again.', '')); }
  });
})();
