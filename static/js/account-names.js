document.querySelectorAll('[data-text-only-name]').forEach(input=>{
  const clean=()=>{input.value=input.value.replace(/[^\p{L}\p{M}\s]/gu,'');};
  input.addEventListener('input',event=>{if(!event.isComposing)clean();});
  input.addEventListener('compositionend',clean);
});
