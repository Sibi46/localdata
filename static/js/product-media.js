(() => {
  document.querySelectorAll('[data-image-preview]').forEach(input => {
    let urls = [];
    const max = Number(input.dataset.maxImages) || 1;
    const multiple = max > 1;
    let preview = document.getElementById(input.dataset.imagePreview);
    if (!preview) {
      preview = document.createElement('div');
      preview.id = input.dataset.imagePreview;
      preview.className = 'upload-image-previews';
      input.insertAdjacentElement('afterend', preview);
    }
    const status = document.createElement('p');
    status.className = 'upload-image-status';
    status.setAttribute('aria-live', 'polite');
    if (multiple) {
      input.classList.add('product-file-input');
      preview.classList.add('product-image-slots');
      preview.insertAdjacentElement('beforebegin', status);
    }
    const replaceFiles = files => {
      const transfer = new DataTransfer();
      files.forEach(file => transfer.items.add(file));
      input.files = transfer.files;
      input.dispatchEvent(new Event('change', {bubbles: true}));
    };
    const pick = replaceIndex => {
      const picker = document.createElement('input');
      picker.type = 'file';
      picker.accept = input.accept;
      picker.multiple = replaceIndex === null;
      // Keep the picker in the document for mobile browsers until it closes.
      picker.hidden = true;
      input.parentElement.append(picker);
      picker.addEventListener('change', () => {
        const files = [...input.files];
        const selected = [...picker.files];
        picker.remove();
        if (!selected.length) return;
        if (replaceIndex === null) files.push(...selected);
        else files[replaceIndex] = selected[0];
        if (files.length > max) {
          status.textContent = `You can add up to ${max} images. There are ${input.files.length} selected; choose ${max - input.files.length} more or fewer.`;
          return;
        }
        replaceFiles(files);
      }, {once:true});
      picker.addEventListener('cancel', () => picker.remove(), {once:true});
      picker.click();
    };
    const button = (text, label, action, className='image-slot-action') => {
      const element = document.createElement('button');
      element.type = 'button';
      element.className = className;
      element.textContent = text;
      element.setAttribute('aria-label', label);
      element.addEventListener('click', action);
      return element;
    };
    const render = () => {
      urls.forEach(url => URL.revokeObjectURL(url));
      urls = [];
      preview.replaceChildren();
      const files = [...input.files];
      input.setCustomValidity(files.length > max ? `Choose a maximum of ${max} images.` : '');
      if (files.length > max) input.reportValidity();
      status.textContent = `${files.length} / ${max} images selected. Image 1 is the cover.`;
      files.slice(0, max).forEach((file, index) => {
        const figure = document.createElement('figure');
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        urls.push(img.src);
        img.alt = file.name;
        const caption = document.createElement('figcaption');
        caption.textContent = max > 1 ? (index === 0 ? 'Cover image' : `Image ${index + 1}`) : file.name;
        figure.append(img, caption);
        if (input.dataset.imageCrop) {
          figure.append(button('Crop / adjust', `Crop ${multiple ? `image ${index + 1}` : input.dataset.imageCrop}`, () => input.dispatchEvent(new CustomEvent('localfrom:cropimage', {
            bubbles: true, detail: {input, index}
          })), 'image-crop-trigger'));
        }
        if (multiple) {
          const actions = document.createElement('div');
          actions.className = 'image-slot-actions';
          actions.append(button('Replace', `Replace image ${index + 1}`, () => pick(index)));
          actions.append(button('Remove', `Remove image ${index + 1}`, () => {
            const remaining = [...input.files]; remaining.splice(index,1); replaceFiles(remaining);
          }));
          if (index > 0) actions.append(button('Set as cover', `Set image ${index + 1} as cover`, () => {
            const ordered = [...input.files]; const [cover] = ordered.splice(index,1); ordered.unshift(cover); replaceFiles(ordered);
          }));
          figure.append(actions);
        }
        preview.append(figure);
      });
      if (multiple) {
        for (let index=files.length; index<max; index++) {
          const slot = button(`+ Add image ${index + 1}`, `Add image ${index + 1}`, () => pick(null), 'image-slot-empty');
          preview.append(slot);
        }
      }
    };
    input.addEventListener('change', render);
    if (multiple) render();
  });
  document.querySelectorAll('[data-product-gallery]').forEach(gallery => {
    const images = [...gallery.querySelectorAll('[data-gallery-image]')];
    const thumbs = [...gallery.querySelectorAll('[data-gallery-thumb]')];
    const stage = gallery.querySelector('[data-image-stage]');
    const dialog = gallery.querySelector('[data-gallery-dialog]');
    const zoom = gallery.querySelector('[data-zoom-image]');
    let index = 0;
    const show = next => {
      index = (next + images.length) % images.length;
      images.forEach((img, position) => { img.hidden = position !== index; });
      thumbs.forEach((button, position) => {
        if (position === index) button.setAttribute('aria-current', 'true');
        else button.removeAttribute('aria-current');
      });
      gallery.querySelector('[data-gallery-counter]').textContent = `${index + 1} / ${images.length}`;
      zoom.src = images[index].src;
      zoom.alt = images[index].alt;
    };
    thumbs.forEach((button, position) => button.addEventListener('click', () => show(position)));
    gallery.querySelector('[data-gallery-prev]')?.addEventListener('click', () => show(index - 1));
    gallery.querySelector('[data-gallery-next]')?.addEventListener('click', () => show(index + 1));
    stage.addEventListener('keydown', event => {
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        event.preventDefault();
        show(index + (event.key === 'ArrowRight' ? 1 : -1));
      }
    });
    let startX;
    stage.addEventListener('touchstart', event => { startX = event.touches[0].clientX; }, {passive: true});
    stage.addEventListener('touchend', event => {
      const change = event.changedTouches[0].clientX - startX;
      if (Math.abs(change) > 45) show(index + (change < 0 ? 1 : -1));
    }, {passive: true});
    gallery.querySelector('[data-gallery-expand]').addEventListener('click', () => { show(index); dialog.showModal(); });
    gallery.querySelector('[data-gallery-close]').addEventListener('click', () => dialog.close());
    dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  });
})();
