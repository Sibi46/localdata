(() => {
  if (window.localFromNotifications) return;
  window.localFromNotifications=true;
  document.querySelectorAll('[data-notification-menu]').forEach(menu => {
    const toggle=menu.querySelector('[data-notification-toggle]');
    const panel=menu.querySelector('[data-notification-panel]');
    const count=menu.querySelector('[data-notification-count]');
    const items=menu.querySelector('[data-notification-items]');
    const mark=menu.querySelector('[data-notification-mark]');
    const csrf=mark.querySelector('[name=csrfmiddlewaretoken]').value;
    let busy=false;
    const close=() => {panel.hidden=true;toggle.setAttribute('aria-expanded','false');};
    const updateCount=value => {
      count.hidden=!value;count.textContent=value>99?'99+':value;
      toggle.setAttribute('aria-label',value?`Notifications, ${value} unread`:'Notifications');
      menu.querySelector('[data-notification-summary]').textContent=`${value} unread`;
    };
    async function refresh() {
      if (busy || document.hidden) return;
      busy=true;
      try {
        const response=await fetch(menu.dataset.feedUrl,{headers:{Accept:'application/json'},cache:'no-store'});
        if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error();
        const data=await response.json();
        updateCount(data.unread_count);
        if (!panel.hidden) {
          items.replaceChildren();
          data.items.forEach(item => {
            const form=document.createElement('form');form.method='post';form.action=item.open_url;
            const token=document.createElement('input');token.type='hidden';token.name='csrfmiddlewaretoken';token.value=csrf;
            const button=document.createElement('button');button.type='submit';button.className='notification-recent-item'+(item.is_read?'':' unread');
            const title=document.createElement('strong');title.textContent=item.title;
            const body=document.createElement('span');body.textContent=item.message;
            const time=document.createElement('time');time.dateTime=item.created_at;time.textContent=new Date(item.created_at).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'});
            button.append(title,body,time);form.append(token,button);items.append(form);
          });
          if (!data.items.length) {const empty=document.createElement('p');empty.className='notification-empty';empty.textContent='You’re all caught up. Your next local update will appear here.';items.append(empty);}
        }
      } catch {
        if (!panel.hidden) {items.replaceChildren();const error=document.createElement('p');error.className='notification-empty';error.textContent='Could not load updates. Open all notifications below to try again.';items.append(error);}
      } finally {busy=false;}
    }
    toggle.addEventListener('click',() => {
      if (!panel.hidden) return close();
      const bounds=toggle.getBoundingClientRect();
      panel.style.top=`${Math.min(bounds.bottom+12,window.innerHeight-150)}px`;
      panel.style.right=`${Math.max(14,window.innerWidth-bounds.right)}px`;
      panel.hidden=false;toggle.setAttribute('aria-expanded','true');refresh();
    });
    menu.querySelector('[data-notification-close]').addEventListener('click',()=>{close();toggle.focus();});
    document.addEventListener('click',event=>{if(!menu.contains(event.target))close();});
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!panel.hidden){close();toggle.focus();}});
    mark.addEventListener('submit',async event=>{
      event.preventDefault();
      try {
        const response=await fetch(mark.action,{method:'POST',headers:{'X-CSRFToken':csrf,'X-Requested-With':'XMLHttpRequest'}});
        if (!response.ok) throw new Error();
        updateCount(0);refresh();
      } catch {mark.submit();}
    });
    setInterval(refresh,30000);
    document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh();});
    window.addEventListener('localfrom:notifications-changed',refresh);
  });
})();
