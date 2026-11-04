(() => {
  const form = document.getElementById('news-phone-form');
  if (form) {
    const phone = document.getElementById('news-phone');
    const otp = document.getElementById('news-otp');
    const send = document.getElementById('news-send');
    const verify = document.getElementById('news-verify');
    const status = document.getElementById('news-otp-status');
    const error = document.getElementById('news-otp-error');
    const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
    let sending = false;
    async function request(url, values, button) {
      error.hidden = true;
      button.disabled = true;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15000);
      try {
        const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf}, body: JSON.stringify(values), signal: controller.signal});
        const data = await response.json();
        if (!response.ok || !data.success) throw new Error(data.error || 'Could not complete this request. Please try again.');
        return data;
      } catch (failure) {
        error.textContent = failure.name === 'TypeError' || failure.name === 'AbortError' ? 'Connection failed. Check your connection and try again.' : failure.message;
        error.hidden = false;
        return null;
      } finally { clearTimeout(timeout); button.disabled = false; }
    }
    phone.addEventListener('input', () => { phone.value = phone.value.replace(/\D/g, '').slice(0, 10); document.getElementById('news-otp-fields').hidden = true; status.textContent = ''; });
    otp.addEventListener('input', () => { otp.value = otp.value.replace(/\D/g, '').slice(0, 6); });
    form.addEventListener('submit', async event => {
      event.preventDefault();
      if (sending || !form.reportValidity()) return;
      sending = true;
      document.getElementById('news-otp-fields').hidden = true;
      otp.value = '';
      phone.readOnly = true;
      status.textContent = 'Sending OTP…';
      const data = await request(form.dataset.sendUrl, {phone: phone.value}, send);
      phone.readOnly = false;
      sending = false;
      status.textContent = data ? data.message : '';
      if (data) { document.getElementById('news-otp-fields').hidden = false; send.textContent = 'Resend OTP'; otp.focus(); }
    });
    verify.addEventListener('click', async () => {
      if (!/^[0-9]{6}$/.test(otp.value)) { error.textContent = 'Enter the six-digit OTP.'; error.hidden = false; otp.focus(); return; }
      const data = await request(form.dataset.verifyUrl, {otp: otp.value}, verify);
      if (data) location.href = data.redirect;
    });
    otp.addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); verify.click(); } });
  }
  const body = document.querySelector('[data-news-body]');
  const count = document.getElementById('news-word-count');
  if (body && count) {
    function update() {
      const words = body.value.replace(/[\u200b\ufeff]/g, '').trim().split(/\s+/).filter(Boolean).length;
      count.textContent = `${words} / 200 words`;
      count.dataset.overLimit = String(words > 200);
      body.setCustomValidity(words > 200 ? 'Keep your news within 200 words.' : '');
    }
    body.addEventListener('input', update);
    update();
  }
})();
