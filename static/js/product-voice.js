/* Browser speech entry. LOCALFROM receives text, never a recorded audio upload. */
(() => {
  'use strict';
  const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
  let active = null;
  function stop() {
    const session = active;
    if (!session) return;
    active = null;
    session.button.textContent = '\uD83C\uDFA4';
    session.button.setAttribute('aria-pressed', 'false');
    try { session.engine.abort(); } catch (_) {}
  }
  function start({input, button, lang, onStatus, onText}) {
    if (active && active.button === button) { stop(); return; }
    stop();
    if (!window.isSecureContext) {
      onStatus('Open LOCALFROM using HTTPS to use the microphone.', true); return;
    }
    if (!Speech) {
      onStatus('Voice entry is not supported here. Use the microphone on your phone keyboard, or type the name.', true); return;
    }
    const engine = new Speech();
    const session = {engine, button, received: false, failed: false};
    active = session;
    engine.lang = lang;
    engine.continuous = false;
    engine.interimResults = true;
    engine.maxAlternatives = 1;
    button.textContent = '\u23F9';
    button.setAttribute('aria-pressed', 'true');
    onStatus('Listening. Say the product name clearly.', false);
    engine.onresult = event => {
      if (active !== session || !input.isConnected || input.disabled) return;
      const text = Array.from(event.results).map(result => result[0]?.transcript || '').join(' ').trim().slice(0, 160);
      if (!text) return;
      session.received = true;
      input.value = text;
      input.dispatchEvent(new Event('input', {bubbles: true}));
      onText(text);
      onStatus('Product name entered. Check it before publishing.', false);
    };
    engine.onerror = event => {
      if (active !== session) return;
      session.failed = true;
      const messages = {
        'not-allowed': 'Allow microphone access for this site in Chrome settings, then try again. You can also use your keyboard microphone.',
        'service-not-allowed': 'Chrome voice recognition is unavailable. Use your keyboard microphone or type the name.',
        'audio-capture': 'No microphone is available. Check your phone microphone permissions, or use keyboard typing.',
        'network': 'Voice recognition needs an internet connection. Check your connection, or use your keyboard microphone.',
        'no-speech': 'No speech was heard. Tap the microphone and speak again.',
        'language-not-supported': 'This speech language is unavailable. Try the other page language or your keyboard microphone.'
      };
      if (event.error !== 'aborted') onStatus(messages[event.error] || 'Voice entry stopped. Try again or use your keyboard microphone.', true);
      stop();
    };
    engine.onend = () => {
      if (active !== session) return;
      if (!session.received && !session.failed) onStatus('No speech was heard. Tap the microphone and speak again.', true);
      active = null;
      button.textContent = '\uD83C\uDFA4';
      button.setAttribute('aria-pressed', 'false');
    };
    try { engine.start(); }
    catch (_) { stop(); onStatus('Voice entry could not start. Try again or use your keyboard microphone.', true); }
  }
  window.LocalfromProductVoice = {start, stop};
  window.addEventListener('pagehide', stop);
})();
