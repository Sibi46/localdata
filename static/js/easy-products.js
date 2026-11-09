/* Photo-first entry. Draft photos use IndexedDB, never localStorage or a server draft. */
(() => {
  'use strict';
  const root = document.querySelector('[data-easy-products]');
  if (!root) return;
  const locale = window.LocalfromProductLanguage;
  const t = (key, params) => locale.t(key, params);
  let feedbackState = null;
  let draftMessage = 'Drafts stay in this browser on this device. Use one tab. Clear drafts on shared devices.';
  const $ = selector => root.querySelector(selector);
  const cards = $('[data-cards]'), picker = $('#easy-photo-picker');
  const form = $('[data-entry-form]'), review = $('[data-review-panel]');
  const feedback = $('[data-feedback]'), draftStatus = $('[data-draft-status]');
  const draftKey = `${root.dataset.owner}:${root.dataset.shop}`;
  const MAX_PRODUCTS = 20, MAX_IMAGE = 5 * 1024 * 1024;
  let entries = [], busy = false, db = null, saveQueue = Promise.resolve(), urls = [];
  let remaining = Number(root.dataset.remaining);
  const voice = window.LocalfromProductVoice;
  let saveTimer = null;

  function say(message, error = false, params = {}) {
    feedbackState = {message, error, params};
    feedback.textContent = error ? locale.error(message) : t(message, params);
    feedback.dataset.error = String(error);
  }
  function setDraftStatus(message) { draftMessage = message; draftStatus.textContent = t(message); }
  function showLimit() {
    const dialog = document.getElementById('product-limit-dialog');
    if (dialog && !dialog.open) dialog.showModal();
  }
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function imageURL(file) {
    const url = URL.createObjectURL(file); urls.push(url); return url;
  }
  function save() {
    clearTimeout(saveTimer);
    if (!db) return Promise.resolve();
    const snapshot = structuredClone(entries);
    saveQueue = saveQueue.catch(() => {}).then(() => new Promise((resolve, reject) => {
      const tx = db.transaction('drafts', 'readwrite');
      tx.objectStore('drafts').put(snapshot, draftKey);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    })).then(() => {
      setDraftStatus('Draft saved on this device. Clear it on shared devices.');
    }).catch(() => {
      setDraftStatus('Draft could not be saved. Keep this page open until you publish.');
    });
    return saveQueue;
  }
  function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(save, 350); }
  async function openDraft() {
    try {
      db = await new Promise((resolve, reject) => {
        const request = indexedDB.open('localfrom-product-entry', 1);
        request.onupgradeneeded = () => request.result.createObjectStore('drafts');
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
        request.onblocked = () => reject(new Error('Draft database is busy'));
      });
      const stored = await new Promise((resolve, reject) => {
        const request = db.transaction('drafts').objectStore('drafts').get(draftKey);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      });
      if (Array.isArray(stored)) {
        entries = stored.slice(0, MAX_PRODUCTS);
        // An interrupted upload has an unknown outcome. Retry its original ID;
        // the server receipt returns the existing product if it was committed.
        entries.forEach(entry => { if (entry.status === 'uploading') entry.status = 'pending'; });
        if (entries.length) say('Saved draft restored.');
      }
    } catch (_) {
      setDraftStatus('Draft saving is unavailable in this browser. Keep this page open until you publish.');
    }
    render();
  }
  async function preparePhoto(file) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('Choose JPG, PNG or WebP photos.');
    if (file.size > 25 * 1024 * 1024) throw new Error('Choose a photo smaller than 25 MB.');
    const bitmap = await createImageBitmap(file);
    try {
      const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(bitmap.width * scale));
      canvas.height = Math.max(1, Math.round(bitmap.height * scale));
      const context = canvas.getContext('2d');
      context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .85));
      if (!blob || blob.size > MAX_IMAGE) throw new Error('This photo is too large. Choose a smaller photo.');
      return new File([blob], 'product.jpg', {type: 'image/jpeg'});
    } finally { bitmap.close(); }
  }
  function listen(entry, input, button) {
    voice.start({input, button, lang: locale.language === 'ta' ? 'ta-IN' : 'en-IN',
      onStatus: (message, error) => say(message, error),
      onText: text => { entry.name = text; review.hidden = true; save(); }});
  }
  function field(entry, key, label, type, attributes) {
    const box = node('div'), id = `entry-${entry.id}-${key}`;
    const title = node('label', label); title.htmlFor = id; box.append(title);
    const row = node('div', '', key === 'name' ? 'easy-name' : '');
    const input = node('input'); input.id = id; input.type = type; input.value = entry[key];
    Object.entries(attributes).forEach(([name, value]) => input.setAttribute(name, value));
    input.disabled = busy || entry.status === 'published';
    input.addEventListener('input', () => { entry[key] = input.value; review.hidden = true; scheduleSave(); });
    input.addEventListener('invalid', () => input.setCustomValidity(t(key === 'name' ? 'Enter a product name.' : key === 'price' ? 'Enter a valid price greater than zero.' : 'Enter a whole discount percentage from 0 to 100.')));
    input.addEventListener('input', () => input.setCustomValidity(''));
    row.append(input);
    if (key === 'name' && voice && entry.status !== 'published') {
      const mic = node('button', '🎤', 'easy-mic'); mic.type = 'button'; mic.disabled = busy;
      mic.title = t('Speak product name'); mic.setAttribute('aria-label', t('Speak product name'));
      mic.setAttribute('aria-pressed', 'false');
      mic.onclick = () => listen(entry, input, mic); row.append(mic);
    }
    box.append(row); return box;
  }
  function render() {
    if (voice) voice.stop();
    urls.forEach(URL.revokeObjectURL); urls = []; cards.replaceChildren();
    $('[data-slots]').textContent = remaining;
    entries.forEach((entry, index) => {
      const card = node('article', '', 'easy-card'); card.dataset.published = entry.status === 'published';
      card.append(node('h2', t('Product {number}', {number: index + 1})));
      const photos = node('div', '', 'easy-photos');
      entry.photos.forEach((photo, position) => {
        const box = node('div', '', 'easy-photo'), img = node('img');
        img.src = imageURL(photo); img.alt = t('Product {number}, image {image}', {number: index + 1, image: position + 1}); box.append(img);
        if (!busy && entry.status !== 'published' && entry.photos.length > 1) {
          const remove = node('button', '×'); remove.type = 'button';
          remove.setAttribute('aria-label', t('Remove image {number}', {number: position + 1}));
          remove.onclick = () => { entry.photos.splice(position, 1); save(); render(); }; box.append(remove);
        }
        photos.append(box);
      });
      card.append(photos);
      card.append(field(entry, 'name', t('Product name'), 'text', {required:'', maxlength:'160', autocomplete:'off'}));
      const prices = node('div', '', 'easy-prices');
      prices.append(field(entry, 'price', t('Price ₹'), 'number', {required:'', min:'0.01', max:'9999999999.99', step:'0.01', inputmode:'decimal'}));
      prices.append(field(entry, 'discount', t('Discount % (optional)'), 'number', {min:'0', max:'100', step:'1', inputmode:'numeric'}));
      card.append(prices);
      if (entry.status !== 'published') {
        const label = node('label', t('Extra views ({number}/2)', {number: entry.photos.length}));
        const extra = node('input'); extra.type = 'file'; extra.accept = picker.accept; extra.multiple = true;
        extra.disabled = busy || entry.photos.length >= 2; label.append(extra); card.append(label);
        extra.onchange = async () => {
          busy = true; render();
          try {
            if (extra.files.length + entry.photos.length > 2) throw new Error('Maximum 2 images for one product.');
            for (const file of extra.files) entry.photos.push(await preparePhoto(file));
            await save();
          } catch (error) { say(error.message, true); }
          finally { busy = false; render(); }
        };
        const remove = node('button', t('Remove product'), 'easy-secondary');
        remove.type = 'button'; remove.disabled = busy;
        remove.onclick = () => { entries = entries.filter(item => item !== entry); save(); render(); };
        card.append(remove);
      } else {
        const link = node('a', t('✓ View product'));
        link.href = `/products/${Number(entry.productId)}/`; card.append(link);
        const edit = node('a', t('Edit this product'));
        edit.href = `/shop/products/${Number(entry.productId)}/edit/`; card.append(edit);
        const manage = node('a', t('Manage products / delete'));
        manage.href = '/employer/dashboard/#products'; card.append(manage);
      }
      if (entry.error) card.append(node('p', locale.error(entry.error), 'easy-card-error'));
      if (entry.status === 'uploading') card.append(node('p', t('Uploading…'), 'easy-card-status'));
      cards.append(card);
    });
    picker.disabled = busy || entries.length >= MAX_PRODUCTS;
    $('[data-clear]').disabled = busy;
    $('[data-review]').disabled = busy || !entries.some(entry => entry.status !== 'published');
    $('[data-publish]').disabled = busy; $('[data-back]').disabled = busy;
  }
  picker.onchange = async () => {
    const files = Array.from(picker.files); picker.value = ''; review.hidden = true;
    if (remaining <= 0) { showLimit(); return; }
    if (files.length + entries.length > MAX_PRODUCTS) return say('Choose up to 20 products per batch. Clear completed drafts to start another batch.', true);
    busy = true; render();
    try {
      for (const file of files) {
        const photo = await preparePhoto(file);
        entries.push({id: crypto.randomUUID(), name:'', price:'', discount:'', photos:[photo], status:'pending'});
      }
      await save(); say('Photos ready. Enter a name and price below.');
    } catch (error) { await save(); say(error.message, true); }
    finally { busy = false; render(); }
  };
  function renderReview() {
    const pending = entries.filter(entry => entry.status !== 'published');
    const list = $('[data-review-list]'); list.replaceChildren();
    pending.forEach(entry => {
      const row = node('div', '', 'easy-review-row'), img = node('img');
      img.src = imageURL(entry.photos[0]); img.alt = entry.name;
      const price = (Number(entry.price) * (100 - Number(entry.discount || 0)) / 100).toFixed(2);
      row.append(img, node('p', `${entry.name} · ₹${price}${entry.discount ? ` (${t('{number}% off', {number: entry.discount})})` : ''}`)); list.append(row);
    });
  }
  function photosWithinLimit() {
    if (entries.some(entry => entry.status !== 'published' && entry.photos.length > 2)) {
      review.hidden = true;
      say('Maximum 2 images for one product.', true);
      return false;
    }
    return true;
  }
  form.onsubmit = event => {
    event.preventDefault(); if (busy || !form.reportValidity()) return;
    if (!photosWithinLimit()) return;
    const pending = entries.filter(entry => entry.status !== 'published');
    if (!pending.length) return;
    if (pending.length > remaining) {
      showLimit();
      return say('Only {number} product slots remain. Remove extra drafts or request more slots.', false, {number: remaining});
    }
    renderReview();
    review.hidden = false; review.scrollIntoView({behavior:'smooth', block:'center'});
  };
  $('[data-back]').onclick = () => { review.hidden = true; cards.scrollIntoView({behavior:'smooth'}); };
  $('[data-clear]').onclick = async () => {
    if (busy || !confirm(t('Clear the draft photos and details on this device? Published products will remain in your shop.'))) return;
    entries = []; review.hidden = true; await save(); render(); say('Draft cleared. You can choose more photos.');
  };
  $('[data-publish]').onclick = async () => {
    if (busy) return;
    if (!photosWithinLimit()) return;
    if (voice) voice.stop();
    busy = true; review.hidden = true;
    const pending = entries.filter(entry => entry.status !== 'published');
    let completed = 0;
    try {
      for (const entry of pending) {
        entry.error = ''; entry.status = 'uploading'; await save(); render();
        say('Uploading {number} / {total}… Keep this page open.', false, {number: completed + 1, total: pending.length});
        const data = new FormData();
        data.set('csrfmiddlewaretoken', form.querySelector('[name=csrfmiddlewaretoken]').value);
        data.set('draft_id', entry.id); data.set('name', entry.name); data.set('price', entry.price);
        data.set('discount_percent', entry.discount || '0');
        entry.photos.forEach((photo, index) => data.append('images', photo, `view-${index + 1}.jpg`));
        try {
          const response = await fetch(root.dataset.publishUrl, {method:'POST', body:data, credentials:'same-origin', headers:{Accept:'application/json'}});
          if (response.redirected || !response.headers.get('content-type')?.includes('application/json')) {
            throw new Error('Session expired or upload interrupted. Check My products, sign in again, then return to this draft.');
          }
          const result = await response.json();
          if (!response.ok) {
            if (result.limit_reached) showLimit();
            const details = Object.values(result.errors || {}).flat().map(item => item.message).join(' ');
            throw new Error(details || result.error || 'Upload failed. Check My products before retrying.');
          }
          entry.status = 'published'; entry.productId = result.id; entry.photos = entry.photos.slice(0, 1);
          remaining = Math.max(0, remaining - 1); completed++; await save();
        } catch (error) {
          entry.status = 'pending'; entry.error = error.message; await save();
          throw error;
        }
      }
      say(completed === 1 ? 'Your product has been added to LOCALFROM.' : '{number} products have been added to LOCALFROM.', false, {number: completed});
      if (completed > 0) window.LocalfromProductAdded?.show(completed);
    } catch (error) { say(error.message, true); }
    finally { busy = false; render(); }
  };
  window.addEventListener('beforeunload', event => { if (busy) { event.preventDefault(); event.returnValue = ''; } });
  document.addEventListener('product-language-change', () => {
    if (voice) voice.stop();
    const previewOpen = !review.hidden;
    render();
    if (previewOpen) renderReview();
    setDraftStatus(draftMessage);
    if (feedbackState) say(feedbackState.message, feedbackState.error, feedbackState.params);
  });
  setDraftStatus(draftMessage);
  picker.disabled = true;
  openDraft();
})();
