(() => {
  const dialog = document.getElementById('hospital-launch-dialog');
  let opener;
  if (dialog) {
    document.querySelectorAll('[data-hospital-launch]').forEach(button => button.addEventListener('click', () => {
      opener = button;
      if (!dialog.open) dialog.showModal();
    }));
    dialog.querySelectorAll('[data-hospital-close]').forEach(button => button.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('close', () => opener?.focus());
  }
  document.querySelectorAll('[data-ride-confirm]').forEach(button => button.addEventListener('click', event => {
    if (!window.confirm(button.dataset.rideConfirm)) event.preventDefault();
  }));
})();
