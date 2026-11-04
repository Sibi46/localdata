(() => {
  const dialog = document.querySelector('[data-image-crop-dialog]');
  if (!dialog) return;
  const $ = selector => dialog.querySelector(selector);
  const canvas = $('[data-crop-canvas]');
  const slider = $('[data-crop-zoom]');
  const shape = $('[data-crop-ratio]');
  const apply = $('[data-crop-apply]');
  const error = $('[data-crop-error]');
  let state, serial = 0, drag;
  function dimensions() {
    const sideways = Math.abs(state.angle % 180) === 90;
    return sideways ? [state.image.height, state.image.width] : [state.image.width, state.image.height];
  }
  function configure(reset = true) {
    const [width, height] = dimensions();
    state.ratio = state.kind === 'banner' ? 4 : state.kind === 'logo' ? 1 : shape.value === 'original' ? width / height : Number(shape.value);
    canvas.width = Math.max(1, Math.round(state.ratio >= 1 ? 800 : 800 * state.ratio));
    canvas.height = Math.max(1, Math.round(state.ratio >= 1 ? 800 / state.ratio : 800));
    state.minimum = Math.min(canvas.width / width, canvas.height / height) / Math.max(canvas.width / width, canvas.height / height);
    slider.min = Math.floor(state.minimum * 100) / 100;
    if (reset) {
      state.zoom = state.kind === 'logo' ? state.minimum : 1;
      state.x = state.y = 0;
    }
    draw();
  }
  function paint(target) {
    const ctx = target.getContext('2d');
    const [width, height] = dimensions();
    const scale = Math.max(target.width / width, target.height / height) * state.zoom;
    ctx.clearRect(0, 0, target.width, target.height);
    if (state.kind !== 'logo') { ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, target.width, target.height); }
    ctx.save();
    ctx.translate(target.width * (0.5 + state.x), target.height * (0.5 + state.y));
    ctx.rotate(state.angle * Math.PI / 180);
    ctx.drawImage(state.image, -state.image.width * scale / 2, -state.image.height * scale / 2, state.image.width * scale, state.image.height * scale);
    ctx.restore();
  }
  function draw() {
    if (!state?.ready) return;
    paint(canvas);
    slider.value = state.zoom;
    $('[data-crop-zoom-label]').textContent = `${Math.round(state.zoom * 100)}%`;
    $('[data-crop-output-note]').textContent = state.kind === 'logo' ? 'Square logo · 512 × 512 px' : state.kind === 'banner' ? 'Wide banner · 1600 × 400 px' : 'Adjust each product photo separately.';
  }
  document.addEventListener('localfrom:cropimage', event => {
    const {input, index} = event.detail;
    const file = input.files[index];
    if (!file || dialog.open) return;
    const token = ++serial;
    const image = new Image();
    const url = URL.createObjectURL(file);
    state = {input, index, file, image, url, kind: input.dataset.imageCrop, angle: 0, x: 0, y: 0, zoom: 1, ready: false, opener: document.activeElement};
    dialog.dataset.kind = state.kind;
    shape.value = '1';
    $('[data-crop-ratio-control]').hidden = state.kind !== 'product';
    error.hidden = true;
    apply.disabled = true;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    dialog.showModal();
    image.onload = () => {
      if (token !== serial) return;
      state.ready = true;
      configure();
      apply.disabled = false;
    };
    image.onerror = () => {
      if (token !== serial) return;
      error.textContent = 'This image could not be opened. Choose a JPG, PNG, or WebP image.';
      error.hidden = false;
    };
    image.src = url;
  });
  slider.addEventListener('input', () => { if (state?.ready) { state.zoom = Number(slider.value); draw(); } });
  shape.addEventListener('change', () => { if (state?.ready) configure(); });
  dialog.querySelectorAll('[data-crop-rotate]').forEach(button => button.addEventListener('click', () => {
    if (!state?.ready) return;
    state.angle = (state.angle + Number(button.dataset.cropRotate)) % 360;
    configure();
  }));
  $('[data-crop-fit]').addEventListener('click', () => {
    if (!state?.ready) return;
    state.zoom = state.minimum; state.x = state.y = 0; draw();
  });
  $('[data-crop-reset]').addEventListener('click', () => {
    if (!state?.ready) return;
    state.angle = 0; configure();
  });
  canvas.addEventListener('pointerdown', event => {
    if (!state?.ready) return;
    drag = {id: event.pointerId, x: event.clientX, y: event.clientY};
    canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener('pointermove', event => {
    if (!drag || drag.id !== event.pointerId) return;
    const bounds = canvas.getBoundingClientRect();
    state.x += (event.clientX - drag.x) / bounds.width;
    state.y += (event.clientY - drag.y) / bounds.height;
    drag.x = event.clientX; drag.y = event.clientY;
    draw();
  });
  ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(name => canvas.addEventListener(name, () => { drag = null; }));
  canvas.addEventListener('keydown', event => {
    if (!state?.ready || !['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
    event.preventDefault();
    const step = event.shiftKey ? 0.05 : 0.01;
    state.x += event.key === 'ArrowRight' ? step : event.key === 'ArrowLeft' ? -step : 0;
    state.y += event.key === 'ArrowDown' ? step : event.key === 'ArrowUp' ? -step : 0;
    draw();
  });
  dialog.querySelectorAll('[data-crop-close], [data-crop-cancel]').forEach(button => button.addEventListener('click', () => dialog.close()));
  dialog.addEventListener('close', () => {
    ++serial; drag = null;
    if (state) {
      URL.revokeObjectURL(state.url);
      const focus = state.opener?.isConnected ? state.opener : state.input;
      focus.focus();
    }
    state = null;
  });
  apply.addEventListener('click', async () => {
    if (!state?.ready) return;
    const current = state;
    apply.disabled = true;
    error.hidden = true;
    try {
      const result = document.createElement('canvas');
      const edge = current.kind === 'logo' ? 512 : current.kind === 'banner' ? 1600 : 1200;
      result.width = Math.round(current.ratio >= 1 ? edge : edge * current.ratio);
      result.height = Math.round(current.ratio >= 1 ? edge / current.ratio : edge);
      paint(result);
      const png = current.kind === 'logo' || current.file.type === 'image/png';
      const blob = await new Promise(resolve => result.toBlob(resolve, png ? 'image/png' : 'image/jpeg', 0.9));
      if (state !== current || !dialog.open) return;
      if (!blob || blob.size > 5 * 1024 * 1024) throw new Error('The adjusted image is too large. Please choose a smaller image.');
      if (current.input.files[current.index] !== current.file) throw new Error('Your selection changed. Close this window and select the image again.');
      const transfer = new DataTransfer();
      const name = current.file.name.replace(/\.[^.]+$/, '').slice(0, 100) + '-cropped.' + (png ? 'png' : 'jpg');
      [...current.input.files].forEach((file, index) => transfer.items.add(index === current.index ? new File([blob], name, {type: blob.type}) : file));
      current.input.files = transfer.files;
      current.input.dispatchEvent(new Event('change', {bubbles: true}));
      dialog.close();
    } catch (failure) {
      if (state !== current) return;
      error.textContent = failure.message || 'Could not adjust this image. Please try again.';
      error.hidden = false;
    } finally { apply.disabled = false; }
  });
})();
