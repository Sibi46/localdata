(() => {
  const root=document.querySelector('[data-messaging]');
  if (!root) return;
  let filter='all';
  const search=document.getElementById('convSearch');
  const rows=[...root.querySelectorAll('.conv-item')];
  function filterRows() {
    const term=search.value.trim().toLowerCase();
    let visible=0;
    rows.forEach(row=>{row.hidden=!row.dataset.name.includes(term)||(filter==='unread'&&!Number(row.dataset.unread));if(!row.hidden)visible++;});
    root.querySelector('[data-conversation-empty]').hidden=visible>0||!rows.length;
  }
  search.addEventListener('input',filterRows);
  root.querySelectorAll('[data-conversation-filter]').forEach(button=>button.addEventListener('click',()=>{
    filter=button.dataset.conversationFilter;
    root.querySelectorAll('[data-conversation-filter]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
    filterRows();
  }));
  if(!root.dataset.conversation)return;
  const form=document.getElementById('msgForm');
  const text=document.getElementById('msgText');
  const send=document.getElementById('btnSend');
  const file=document.getElementById('fileInput');
  const preview=root.querySelector('[data-attach-preview]');
  const previewContent=root.querySelector('[data-attach-content]');
  const menu=root.querySelector('[data-attach-menu]');
  const toggle=root.querySelector('[data-attach-toggle]');
  const error=root.querySelector('[data-message-error]');
  const container=document.getElementById('msgsContainer');
  const area=document.getElementById('chatArea');
  const csrf=form.querySelector('[name=csrfmiddlewaretoken]').value;
  let pendingFile=null, previewUrl=null, sending=false, polling=false;
  let cursor=Math.max(0,...[...container.querySelectorAll('[data-id]')].map(item=>Number(item.dataset.id)));
  const bottom=()=>{area.scrollTop=area.scrollHeight;};
  const showError=message=>{error.textContent=message;error.hidden=false;};
  function closeMenu(){menu.hidden=true;toggle.setAttribute('aria-expanded','false');}
  function clearFile(){
    if(previewUrl)URL.revokeObjectURL(previewUrl);
    previewUrl=null;pendingFile=null;file.value='';preview.hidden=true;previewContent.replaceChildren();
  }
  function append(html,id,scrollOnLoad=false){
    if(container.querySelector(`[data-id="${Number(id)}"]`))return;
    const follow=scrollOnLoad||area.scrollHeight-area.scrollTop-area.clientHeight<100;
    container.querySelector('.chat-empty')?.remove();
    container.insertAdjacentHTML('beforeend',html);
    if(follow)container.lastElementChild?.querySelectorAll('img').forEach(img=>img.addEventListener('load',bottom,{once:true}));
  }
  function updatePreview(message,mine=false){
    const active=root.querySelector('.conv-item.active');
    if(!active)return;
    active.querySelector('.conv-preview').textContent=(mine?'You: ':'')+message;
    const time=active.querySelector('time');
    if(time){time.dateTime=new Date().toISOString();time.textContent=new Date().toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'});}
    active.parentElement.prepend(active);
  }
  async function poll(){
    if(polling||document.hidden)return;
    polling=true;
    try{
      const response=await fetch(`${root.dataset.pollUrl}?after=${cursor}`,{cache:'no-store'});
      if(!response.ok)return;
      const data=await response.json();
      const nearBottom=area.scrollHeight-area.scrollTop-area.clientHeight<100;
      if(data.ok&&data.messages.length){
        data.messages.forEach(message=>{append(message.html,message.id);cursor=Math.max(cursor,message.id);});
        const latest=data.messages[data.messages.length-1];
        updatePreview(latest.msg_type==='image'?'Photo':latest.file_name||latest.content);
        if(nearBottom)bottom();
        window.dispatchEvent(new Event('localfrom:notifications-changed'));
      }
    }catch{}finally{polling=false;}
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if(sending||(!text.value.trim()&&!pendingFile))return;
    sending=true;send.disabled=true;error.hidden=true;
    const sentText=text.value;
    const data=new FormData(form);
    data.set('msg_type','text');
    if(pendingFile){data.append('file',pendingFile);data.set('msg_type',pendingFile.type.startsWith('image/')?'image':'file');}
    try{
      const response=await fetch(root.dataset.sendUrl,{method:'POST',headers:{'X-CSRFToken':csrf},body:data});
      const result=await response.json();
      if(!response.ok||!result.ok)throw new Error(result.error||'Could not send your message. Please try again.');
      append(result.html,result.msg_id,true);
      updatePreview(pendingFile?(pendingFile.type.startsWith('image/')?'Photo':pendingFile.name):sentText,true);
      if(text.value===sentText){text.value='';text.style.height='auto';}
      clearFile();bottom();poll();
    }catch(failure){showError(failure.message||'Could not send. Your draft is still here.');}
    finally{sending=false;send.disabled=false;}
  });
  text.addEventListener('input',()=>{text.style.height='auto';text.style.height=`${Math.min(text.scrollHeight,110)}px`;});
  text.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();form.requestSubmit();}});
  toggle.addEventListener('click',()=>{menu.hidden=!menu.hidden;toggle.setAttribute('aria-expanded',String(!menu.hidden));});
  root.querySelectorAll('[data-attach-type]').forEach(button=>button.addEventListener('click',()=>{
    file.accept=button.dataset.attachType==='image'?'image/jpeg,image/png,image/gif,image/webp':'.pdf,.doc,.docx,.xls,.xlsx,.zip,.txt';
    file.click();closeMenu();
  }));
  file.addEventListener('change',()=>{
    const selected=file.files[0];if(!selected)return;
    if(selected.size>10*1024*1024){showError('Choose a file smaller than 10 MB.');file.value='';return;}
    clearFile();pendingFile=selected;preview.hidden=false;error.hidden=true;
    if(selected.type.startsWith('image/')){previewUrl=URL.createObjectURL(selected);const img=document.createElement('img');img.src=previewUrl;img.alt='Selected photo';previewContent.append(img);}
    const name=document.createElement('span');name.textContent=selected.name;previewContent.append(name);
  });
  root.querySelector('[data-attach-clear]').addEventListener('click',clearFile);
  document.addEventListener('click',event=>{if(!menu.contains(event.target)&&!toggle.contains(event.target))closeMenu();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMenu();});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});
  container.querySelectorAll('img').forEach(img=>img.addEventListener('load',bottom,{once:true}));
  bottom();setInterval(poll,3000);
})();
