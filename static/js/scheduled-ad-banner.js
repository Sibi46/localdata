(() => {
  'use strict';
  const section = document.querySelector('[data-scheduled-ads]');
  if (!section) return;
  const slides = [...section.querySelectorAll('[data-scheduled-slide]')];
  const dots = [...section.querySelectorAll('[data-ad-index]')];
  if (slides.length < 2) return;
  let index = 0;
  const show = value => {
    index = (value + slides.length) % slides.length;
    slides.forEach((slide, position) => { slide.hidden = position !== index; });
    dots.forEach((dot, position) => dot.setAttribute('aria-pressed', String(position === index)));
  };
  section.querySelectorAll('[data-ad-direction]').forEach(button => button.addEventListener('click', () => show(index + Number(button.dataset.adDirection))));
  dots.forEach(button => button.addEventListener('click', () => show(Number(button.dataset.adIndex))));
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const timer = window.setInterval(() => {
    if (!reduced.matches && !document.hidden && !section.matches(':hover,:focus-within') && !document.querySelector('dialog[open]')) show(index + 1);
  }, 5000);
  window.addEventListener('pagehide', () => window.clearInterval(timer), {once: true});
})();
