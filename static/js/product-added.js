(() => {
  'use strict';
  const dialog = document.getElementById('product-added-dialog');
  if (!dialog) return;
  const labels = {
    en: {one:'Your product has been added to LOCALFROM.',many:'{number} products have been added to LOCALFROM.',description:'You can view or edit it in My products.',view:'My products',close:'Continue'},
    ta: {one:'உங்கள் பொருள் LOCALFROM-இல் சேர்க்கப்பட்டது.',many:'{number} பொருட்கள் LOCALFROM-இல் சேர்க்கப்பட்டன.',description:'என் பொருட்கள் பகுதியில் பார்க்கலாம் அல்லது திருத்தலாம்.',view:'என் பொருட்கள்',close:'தொடரவும்'}
  };
  function show(count = 1) {
    if (!Number.isSafeInteger(count) || count < 1) return;
    let language = window.LocalfromProductLanguage?.language;
    if (!language) { try { language = localStorage.getItem('localfrom-product-language'); } catch (_) {} }
    const text = labels[language === 'ta' ? 'ta' : 'en'];
    dialog.querySelector('h2').textContent = (count === 1 ? text.one : text.many).replace('{number}', String(count));
    dialog.querySelector('#product-added-description').textContent = text.description;
    dialog.querySelector('[data-product-added-view]').textContent = text.view;
    dialog.querySelector('[data-product-added-close]').textContent = text.close;
    if (!dialog.open) {
      if (typeof dialog.showModal === 'function') dialog.showModal();
      else dialog.setAttribute('open', '');
    }
  }
  dialog.querySelector('[data-product-added-close]').addEventListener('click', () => {
    if (typeof dialog.close === 'function') dialog.close();
    else dialog.removeAttribute('open');
  });
  window.LocalfromProductAdded = {show};
  // This marker is rendered only for the server's successful create message.
  if (document.querySelector('[data-product-added]')) show();
})();
