/* Progressive enhancement: one visible image without JS, bounded preloading with JS. */
(() => {
  'use strict';
  const banner = document.querySelector('.market-promotion');
  const t = text => window.LocalfromProductLanguage?.t(text) || text;
  if (banner) {
    const slides = [...banner.querySelectorAll('[data-product-photo]')];
    const caption = banner.querySelector('[data-photo-caption]');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const failed = new Set();
    let current = 0;
    let requested = 0;
    const wrap = index => (index + slides.length) % slides.length;
    function available(index, direction = 1) {
      let candidate = wrap(index);
      for (let tried = 0; tried < slides.length; tried++) {
        if (!failed.has(candidate)) return candidate;
        candidate = wrap(candidate + direction);
      }
      return null;
    }
    function load(index) {
      const image = slides[index];
      if (image.dataset.photoSrc && !image.hasAttribute('src')) {
        image.src = image.dataset.photoSrc;
        delete image.dataset.photoSrc;
      }
      return image;
    }
    function prime() {
      load(current);
      if (!reduced.matches && !document.hidden) {
        for (const offset of [1, 2]) {
          const index = available(current + offset);
          if (index !== null) load(index);
        }
      }
    }
    function labels() {
      caption.textContent = t(slides[current].dataset.photoLabel);
    }
    function show(index) {
      if (requested !== index) return;
      current = index;
      slides.forEach((image, position) => { image.hidden = position !== current; });
      labels();
      prime();
    }
    function draw(index, direction = 1) {
      const candidate = available(index, direction);
      if (candidate === null) return;
      requested = candidate;
      const image = load(candidate);
      if (image.complete && image.naturalWidth > 0) show(candidate);
    }
    slides.forEach((image, index) => {
      image.addEventListener('load', () => show(index));
      image.addEventListener('error', () => {
        failed.add(index);
        if (requested === index) requested = current;
      });
    });
    labels();
    draw(0);
    prime();
    const timer = window.setInterval(() => {
      if (reduced.matches || document.hidden || document.querySelector('dialog[open]')) return;
      const index = available(current + 1);
      if (index === null) return;
      const next = load(index);
      if (next.complete && next.naturalWidth > 0) draw(index);
    }, 1000);
    reduced.addEventListener('change', prime);
    document.addEventListener('visibilitychange', prime);
    document.addEventListener('product-language-change', labels);
    window.addEventListener('pagehide', () => window.clearInterval(timer), {once: true});
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
