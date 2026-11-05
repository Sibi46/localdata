/* Keep one language selector, moving it below search on small screens. */
(() => {
  const bar = document.querySelector('.home-language-bar');
  const mobileSlot = document.querySelector('[data-home-language-mobile]');
  if (!bar || !mobileSlot) return;

  const desktopPosition = document.createComment('Home language desktop position');
  bar.before(desktopPosition);
  const mobile = window.matchMedia('(max-width: 640px)');
  const position = () => {
    if (mobile.matches) mobileSlot.append(bar);
    else desktopPosition.after(bar);
  };
  position();
  mobile.addEventListener('change', position);
})();
