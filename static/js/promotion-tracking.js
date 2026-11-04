(() => {
  'use strict';
  const script = document.querySelector('[data-promotion-tracking]');
  if (!script || navigator.doNotTrack === '1' || navigator.globalPrivacyControl) return;
  if (window.localfromPromotionTrackingActive) return;
  window.localfromPromotionTrackingActive = true;
  const queue = [], seen = new WeakSet(), timers = new Map();
  let scheduled;
  function record(card, action) {
    queue.push({id:crypto.randomUUID(), kind:card.dataset.promotionKind, object:card.dataset.promotionId, action});
    clearTimeout(scheduled); scheduled = setTimeout(flush,100);
  }
  function flush(beacon = false) {
    clearTimeout(scheduled);
    if (!queue.length) return;
    const data = new URLSearchParams({csrfmiddlewaretoken:script.dataset.csrf, events:JSON.stringify(queue.splice(0,20))});
    if (beacon && navigator.sendBeacon?.(script.dataset.endpoint, data)) return;
    fetch(script.dataset.endpoint, {method:'POST',body:data,credentials:'same-origin',keepalive:true}).catch(() => {});
  }
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      clearTimeout(timers.get(entry.target)); timers.delete(entry.target);
      if (entry.intersectionRatio < .5 || seen.has(entry.target) || document.hidden) return;
      timers.set(entry.target, setTimeout(() => {
        if (!document.hidden) { seen.add(entry.target); record(entry.target,'view'); observer.unobserve(entry.target); }
        timers.delete(entry.target);
      },1000));
    }), {threshold:[0,.5]});
    document.querySelectorAll('[data-promotion-kind][data-promotion-id]').forEach(card => observer.observe(card));
    document.addEventListener('visibilitychange', () => {
      timers.forEach(clearTimeout); timers.clear();
      if (!document.hidden) document.querySelectorAll('[data-promotion-kind][data-promotion-id]').forEach(card => { if (!seen.has(card)) { observer.unobserve(card); observer.observe(card); } });
    });
  }
  document.addEventListener('click', event => {
    const control = event.target.closest('a,button');
    const card = control?.closest('[data-promotion-kind][data-promotion-id]');
    if (card) record(card,'click');
  },true);
  window.addEventListener('pagehide', () => flush(true));
})();
