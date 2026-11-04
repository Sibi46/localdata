(() => {
  const labels=[...document.querySelectorAll('[data-brand-word]')];
  if(!labels.length)return;
  const words=['From','Shop','Offers','News','Products'];
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
  let index=0,timer;
  function schedule(){
    clearInterval(timer);
    if(reducedMotion.matches){index=0;labels.forEach(label=>{label.textContent=words[0];});return;}
    if(document.hidden)return;
    timer=setInterval(()=>{
      index=(index+1)%words.length;
      labels.forEach(label=>{
        label.textContent=words[index];
        label.animate?.([{opacity:0,transform:'translateY(3px)'},{opacity:1,transform:'translateY(0)'}],{duration:180,easing:'ease-out'});
      });
    },1000);
  }
  document.addEventListener('visibilitychange',schedule);
  reducedMotion.addEventListener('change',schedule);
  schedule();
})();
