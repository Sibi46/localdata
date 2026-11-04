(() => {
  const dialog = document.getElementById('locationPermission');
  if (!dialog) return;
  const key = 'opc-location-choice-v1';
  const remember = value => { try { sessionStorage.setItem(key, value); } catch (_) {} };
  function dismiss() { remember('dismissed'); dialog.close(); }
  dialog.querySelectorAll('[data-location-dismiss]').forEach(button => button.addEventListener('click', dismiss));
  dialog.addEventListener('cancel', event => { event.preventDefault(); dismiss(); });
  function status(message) { document.querySelectorAll('[data-location-status]').forEach(element => { element.textContent = message; }); }
  document.querySelectorAll('[data-use-location]').forEach(button => button.addEventListener('click', () => {
    if (!window.isSecureContext || !navigator.geolocation) {
      status('Location is unavailable in this browser. Enter your pincode instead.');
      return;
    }
    button.disabled = true;
    status('Choose Allow in your browser’s location request.');
    navigator.geolocation.getCurrentPosition(position => {
      remember('allowed');
      const lat = position.coords.latitude.toFixed(3), lng = position.coords.longitude.toFixed(3);
      document.querySelectorAll('[data-location-jobs]').forEach(link => {
        link.href = '/jobs/?pincode=&lat=' + encodeURIComponent(lat) + '&lng=' + encodeURIComponent(lng) + '&radius=5';
        link.hidden = false;
      });
      status('Location allowed. Find jobs near you, or confirm your pincode for local shops and communities.');
      button.disabled = false;
      button.textContent = 'Location allowed';
      dialog.querySelector('.location-later').textContent = 'Continue';
    }, error => {
      remember('declined');
      status(error.code === 1 ? 'Location access was not allowed. Enter your pincode, or enable location in your browser settings.' : 'We could not get your location. Enter your pincode instead.');
      button.disabled = false;
    }, {enableHighAccuracy:false, timeout:12000, maximumAge:300000});
  }));
  document.addEventListener('submit', event => {
    if (event.target.matches('.location-manual,.account-area-form')) remember('manual');
  }, true);
  // Ask on entry without stacking a second modal over the existing welcome intro.
  if (location.pathname !== '/' || location.search || location.hash) return;
  try { if (sessionStorage.getItem(key)) return; } catch (_) {}
  function show() {
    const welcome = document.getElementById('welcomeIntro');
    if (welcome && welcome.open) { welcome.addEventListener('close', show, {once:true}); return; }
    if (typeof dialog.showModal === 'function') dialog.showModal();
  }
  setTimeout(show, 250);
})();
