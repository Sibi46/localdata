(() => {
  const dialog = document.getElementById('area-dialog');
  if (!dialog) return;
  let opener;
  const close = () => {
    dialog.close();
    document.body.classList.remove('dialog-open');
    opener?.focus();
  };
  document.querySelectorAll('[data-area-open]').forEach(button => {
    button.addEventListener('click', () => {
      opener = button;
      dialog.showModal();
      document.body.classList.add('dialog-open');
      document.getElementById('local-pincode').focus();
    });
  });
  dialog.querySelector('[data-area-close]').addEventListener('click', close);
  dialog.addEventListener('cancel', event => { event.preventDefault(); close(); });
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close();
  });
  const pincode = document.getElementById('local-pincode');
  pincode.addEventListener('input', () => {
    pincode.value = pincode.value.replace(/\D/g, '').slice(0, 6);
  });
  window.addEventListener('pageshow', () => {
    if (!dialog.open) document.body.classList.remove('dialog-open');
  });
})();
