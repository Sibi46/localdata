/* Progressive enhancement: the first banner and search work without JavaScript. */
(() => {
  'use strict';
  const banner = document.querySelector('.market-promotion');
  if (!banner) return;
  const t = text => window.LocalfromProductLanguage?.t(text) || text;
  const slides = [
    ['Good things.', 'Close to you.', 'Discover shops, products & everyday offers.', 'Explore nearby', '/products/'],
    ['Your town.', 'Your shops.', 'Find local businesses and see what they have in store.', 'Explore nearby', '/businesses/'],
    ['Local finds.', 'Lovely prices.', 'Browse deals and updates shared by nearby shops.', 'Offers around you', '/advertise/']
  ];
  let current = 0;
  const controls = document.createElement('div');
  controls.className = 'market-promo-controls';
  controls.setAttribute('role', 'group');
  controls.setAttribute('aria-label', t('Promotion slides'));
  function draw(index) {
    current = (index + slides.length) % slides.length;
    const [first, second, description, label, href] = slides[current];
    const heading = banner.querySelector('h1');
    heading.replaceChildren(document.createTextNode(t(first)), document.createElement('br'), document.createTextNode(t(second)));
    banner.querySelector('.market-promotion-copy>p:not(.eyebrow)').textContent = t(description);
    const link = banner.querySelector('.banner-link');
    link.replaceChildren(document.createTextNode(t(label) + ' '));
    const arrow = document.createElement('i');
    arrow.className = 'fas fa-arrow-right'; arrow.setAttribute('aria-hidden', 'true'); link.append(arrow);
    link.href = href;
    controls.querySelectorAll('[data-slide]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.slide) === current)));
  }
  function addButton(label, action, slide) {
    const button = document.createElement('button'); button.type = 'button';
    button.setAttribute('aria-label', t(label));
    if (slide !== undefined) { button.dataset.slide = slide; button.append(document.createElement('span')); }
    else button.textContent = action === -1 ? '❮' : '❯';
    button.addEventListener('click', () => draw(slide === undefined ? current + action : slide));
    controls.append(button);
  }
  addButton('Previous promotion', -1);
  slides.forEach((_, index) => addButton('Promotion ' + (index + 1), 0, index));
  addButton('Next promotion', 1);
  banner.after(controls); draw(0);
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const timer = window.setInterval(() => {
    if (!reduced.matches && !document.hidden && !banner.matches(':hover, :focus-within') && !controls.matches(':focus-within') && !document.querySelector('dialog[open]')) draw(current + 1);
  }, 5000);
  window.addEventListener('pagehide', () => window.clearInterval(timer), {once: true});
  document.addEventListener('product-language-change', () => draw(current));

  const mic = document.querySelector('[data-market-mic]');
  const input = document.getElementById('business-search');
  const status = document.querySelector('[data-market-voice-status]');
  mic?.addEventListener('click', () => window.LocalfromProductVoice?.start({
    input, button: mic, lang: window.LocalfromProductLanguage?.language === 'ta' ? 'ta-IN' : 'en-IN',
    onStatus: message => {
      if (message === 'Listening. Say the product name clearly.') message = 'Listening. Say a product or shop name.';
      if (message === 'Product name entered. Check it before publishing.') message = 'Search text entered. Check it and tap search.';
      status.textContent = t(message);
    },
    onText: () => {}
  }));
})();
