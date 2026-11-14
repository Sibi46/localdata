(() => {
  const orbit = document.querySelector('[data-village-orbit]');
  if (!orbit) return;
  const labels = [...orbit.querySelectorAll('[data-village-name]')];
  const villages = [
    'Vandavasi', 'Birudur', 'Thennangur', 'Mummuni', 'Sembur', 'Ponnur',
    'Pathiri', 'Kilsathamangalam', 'Athipakkam', 'Manganallur', 'Salukkai',
    'Kodanallur', 'Karanai', 'Kosapattu', 'Navalpakkam', 'Elangadu',
    'Maruthadu', 'Arasur', 'Punnai', 'Melkodungalur', 'Erumbur', 'Osur',
    'Nelliyankulam', 'Japthikaranai'
  ];
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let offset = 0;
  let visible = false;
  const observer = new IntersectionObserver(entries => {
    visible = entries.some(entry => entry.isIntersecting);
  });
  observer.observe(orbit);
  const timer = window.setInterval(() => {
    if (!visible || document.hidden || reduced.matches) return;
    offset = (offset + labels.length) % villages.length;
    labels.forEach((label, index) => {
      label.textContent = villages[(offset + index) % villages.length];
      label.classList.toggle('is-long-name', label.textContent.length > 13);
      label.classList.remove('is-changing');
    });
    // Restart the soft fade for each newly displayed group of village names.
    void orbit.offsetWidth;
    labels.forEach(label => label.classList.add('is-changing'));
  }, 1000);
  window.addEventListener('pagehide', () => {
    window.clearInterval(timer);
    observer.disconnect();
  }, {once: true});
})();
