/* Progressive enhancement: the first banner and search work without JavaScript. */
(() => {
  'use strict';
  const banner = document.querySelector('.market-promotion');
  const t = text => window.LocalfromProductLanguage?.t(text) || text;
  if (banner) {
  const slides = [...banner.querySelectorAll('[data-product-photo]')];
  let current = 0;
  const controls = document.createElement('div');
  controls.className = 'market-promo-controls market-photo-controls';
  controls.setAttribute('role', 'group');
  controls.setAttribute('aria-label', t('Promotion slides'));
  const caption = banner.querySelector('[data-photo-caption]');
  const counter = document.createElement('span');
  counter.className = 'market-photo-count';
  counter.setAttribute('aria-hidden', 'true');
  function draw(index) {
    current = (index + slides.length) % slides.length;
    slides.forEach((image, position) => { image.hidden = position !== current; });
    caption.textContent = t(slides[current].dataset.photoLabel);
    counter.textContent = `${current + 1} / ${slides.length}`;
  }
  function addButton(label, action) {
    const button = document.createElement('button'); button.type = 'button';
    button.setAttribute('aria-label', t(label));
    button.textContent = action === -1 ? '❮' : '❯';
    button.addEventListener('click', () => draw(current + action));
    controls.append(button);
  }
  addButton('Previous promotion', -1);
  controls.append(counter);
  addButton('Next promotion', 1);
  banner.after(controls); draw(0);
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const timer = window.setInterval(() => {
    const next = slides[(current + 1) % slides.length];
    if (!reduced.matches && !document.hidden && !controls.matches(':focus-within') && !document.querySelector('dialog[open]') && next.complete && next.naturalWidth > 0) draw(current + 1);
  }, 1000);
  window.addEventListener('pagehide', () => window.clearInterval(timer), {once: true});
  document.addEventListener('product-language-change', () => draw(current));

  }
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
