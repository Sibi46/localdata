(() => {
  const showcase = document.querySelector('[data-showcase]');
  if (!showcase) return;
  const slides = [...showcase.querySelectorAll('[data-showcase-slide]')];
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let index = 0;
  let timer;
  const show = next => {
    index = (next + slides.length) % slides.length;
    slides.forEach((slide, position) => {
      slide.hidden = position !== index;
      slide.classList.toggle('is-active', position === index);
    });
    showcase.querySelector('[data-showcase-count]').textContent = `${index + 1} / ${slides.length}`;
  };
  const schedule = () => {
    window.clearInterval(timer);
    if (!reducedMotion.matches && !document.hidden && !showcase.contains(document.activeElement)) {
      timer = window.setInterval(() => show(index + 1), 1500);
    }
  };
  showcase.querySelector('[data-showcase-prev]').addEventListener('click', () => { show(index - 1); schedule(); });
  showcase.querySelector('[data-showcase-next]').addEventListener('click', () => { show(index + 1); schedule(); });
  showcase.addEventListener('focusin', schedule);
  showcase.addEventListener('focusout', () => window.setTimeout(schedule, 0));
  document.addEventListener('visibilitychange', schedule);
  reducedMotion.addEventListener('change', schedule);
  schedule();
})();
