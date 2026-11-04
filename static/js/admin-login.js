(() => {
  const toggle=document.querySelector('[data-admin-password-toggle]');
  if(!toggle)return;
  const input=document.getElementById(toggle.getAttribute('aria-controls'));
  toggle.addEventListener('click',()=>{
    const visible=input.type==='password';
    input.type=visible?'text':'password';
    toggle.textContent=visible?'Hide password':'Show password';
    toggle.setAttribute('aria-pressed',String(visible));
  });
})();
