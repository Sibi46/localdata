(() => {
  document.querySelectorAll('[data-account-pincode]').forEach(input=>{
    const form=input.closest('form');
    const city=form?.querySelector('[data-account-city]');
    if(!city)return;
    const hint=document.createElement('small');hint.setAttribute('role','status');hint.className='account-location-hint';input.insertAdjacentElement('afterend',hint);
    let timer,controller;
    async function lookup(changed=false){
      const pin=input.value.trim();
      controller?.abort();
      if(changed)city.value='';
      hint.textContent='';
      if(!/^[1-9][0-9]{5}$/.test(pin))return;
      controller=new AbortController();hint.textContent='Finding your city / town...';
      try{
        const response=await fetch('/api/pincode/'+pin+'/',{signal:controller.signal,credentials:'same-origin'});
        const data=await response.json();
        if(input.value.trim()!==pin)return;
        if(data.success){if(changed||!city.value)city.value=data.city||data.area||data.district;hint.textContent=[data.area,data.district,data.state].filter(Boolean).join(', ');}
        else hint.textContent=data.code==='lookup_unavailable'?'City lookup is temporarily unavailable. Please enter your city / town below.':'Pincode not found. Check the number or enter your city / town below.';
      }catch(error){if(error.name!=='AbortError')hint.textContent='Area lookup is unavailable. Enter your city / town below.';}
    }
    input.addEventListener('input',()=>{input.value=input.value.replace(/\D/g,'').slice(0,6);city.value='';clearTimeout(timer);timer=setTimeout(()=>lookup(true),250);});
    lookup();
  });
})();
