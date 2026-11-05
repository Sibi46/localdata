(() => {
  const search=document.querySelector('[data-shop-lookup]');
  if(!search)return;
  const results=document.querySelector('[data-shop-results]');
  const status=document.querySelector('[data-shop-status]');
  const form=document.querySelector('[data-business-form]');
  const selected=form.querySelector('[name="directory_entry"]');
  let timer,controller;
  function choose(entry){
    if(!entry.can_select)return;
    for(const key of ['name','category','pincode','city','address']){
      if(entry[key])form.elements[key].value=entry[key];
    }
    selected.value=entry.id;
    search.value=entry.name;
    results.replaceChildren();
    status.textContent=entry.name+' selected. Check your details below, then create your dashboard.';
    form.elements.name.focus();
  }
  async function lookup(){
    const query=search.value.trim();
    controller?.abort();results.replaceChildren();status.textContent='';
    if(query.length<2)return;
    controller=new AbortController();status.textContent='Finding your shop...';
    try{
      const response=await fetch(search.dataset.url+'?'+new URLSearchParams({q:query}),{signal:controller.signal,credentials:'same-origin'});
      if(!response.ok)throw Error('Search unavailable');
      const data=await response.json();
      if(search.value.trim()!==query)return;
      status.textContent=data.results.length?'Choose your shop. Selection requires your account phone to match an imported contact.':'No matching shop name found. You can enter your shop details below.';
      data.results.forEach(entry=>{
        const button=document.createElement('button');button.type='button';
        const info=document.createElement('span'),name=document.createElement('strong'),detail=document.createElement('small'),action=document.createElement('span');
        name.textContent=entry.name;
        detail.textContent=entry.can_select?[entry.phone,entry.city].filter(Boolean).join(' / '):'Contact admin if this is your shop: its contact must match your account phone.';
        action.textContent=entry.can_select?'Use this shop':'Phone must match';
        button.disabled=!entry.can_select;
        info.append(name,detail);button.append(info,action);button.addEventListener('click',()=>choose(entry));results.append(button);
      });
    }catch(error){if(error.name!=='AbortError')status.textContent='Search is unavailable. You can still enter your shop details below.';}
  }
  search.addEventListener('input',()=>{controller?.abort();clearTimeout(timer);selected.value='';timer=setTimeout(lookup,250);});
  search.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();clearTimeout(timer);lookup();}});
  form.elements.name.addEventListener('input',()=>{selected.value='';status.textContent='Enter or update your shop details below.';});
})();
