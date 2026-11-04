(() => {
  const script=document.querySelector('script[data-local-analytics]');
  if(!script || navigator.doNotTrack==='1' || navigator.globalPrivacyControl)return;
  const endpoint=script.dataset.endpoint,csrf=script.dataset.csrf;
  function csrfToken(){
    const name=script.dataset.csrfCookie || 'csrftoken';
    const cookie=document.cookie.split(';').map(item=>item.trim()).find(item=>item.startsWith(name+'='));
    try{return cookie?decodeURIComponent(cookie.slice(name.length+1)):csrf;}catch{return csrf;}
  }
  const page=location.pathname;
  const device=innerWidth<768?'mobile':innerWidth<1024?'tablet':'desktop';
  let queue=[],last=performance.now(),viewed=false,visible=document.visibilityState==='visible';
  let referrer='';try{if(document.referrer)referrer=new URL(document.referrer).origin;}catch{}
  const id=()=>crypto.randomUUID();
  function flush(beacon=false){
    const now=performance.now();
    const seconds=visible?Math.min(25,(now-last)/1000):0;
    last=now;
    const events=queue.splice(0,30);
    const data=new URLSearchParams({csrfmiddlewaretoken:csrfToken(),events:JSON.stringify(events),seconds:String(seconds),path:page,device,referrer});
    if(beacon && navigator.sendBeacon?.(endpoint,data))return;
    fetch(endpoint,{method:'POST',body:data,credentials:'same-origin',keepalive:true}).catch(()=>{});
  }
  function view(){
    if(viewed || document.visibilityState!=='visible')return;
    viewed=true;queue.push({id:id(),type:'pageview',path:page});flush();
  }
  function target(control){
    const raw=control.getAttribute('href') || control.form?.getAttribute('action') || '';
    if(!raw)return '';
    try{const url=new URL(raw,location.href);return url.origin===location.origin?url.pathname:url.protocol==='https:'||url.protocol==='http:'?url.origin:url.protocol;}catch{return '';}
  }
  function label(control){
    // Only control labels; never input values, search terms, or message bodies.
    if(control.matches('[data-notification-toggle]'))return 'Notifications';
    let text=control.dataset.analyticsLabel || control.getAttribute('aria-label');
    if(!text){
      const copy=control.cloneNode(true);
      copy.querySelectorAll('[aria-hidden="true"],svg,script,style').forEach(node=>node.remove());
      text=control.matches('input')?'Submit':copy.textContent;
    }
    return (text || control.getAttribute('title') || 'Button').trim().replace(/\s+/g,' ').slice(0,80);
  }
  window.addEventListener('click',event=>{
    if(!event.isTrusted || page.startsWith('/messages/') || page.startsWith('/notifications/'))return;
    const control=event.target.closest('a,button,[role="button"],input[type="submit"]');
    if(!control || control.closest('[data-analytics-ignore],[contenteditable],[data-notification-panel],.notification-panel,.message-bubble,.chat-message,[data-private-content]'))return;
    queue.push({id:id(),type:'click',path:page,label:label(control),target:target(control)});
    // Capture before navigation and before the guest registration gate runs.
    flush(true);
  },true);
  window.addEventListener('submit',event=>{
    if(page.startsWith('/messages/') || page.startsWith('/notifications/') || event.target.closest('[data-analytics-ignore]'))return;
    const button=event.submitter;
    queue.push({id:id(),type:'submit',path:page,label:button?label(button):'Form submit',target:event.target.getAttribute('action') || page});flush(true);
  },true);
  document.addEventListener('visibilitychange',()=>{
    if(document.visibilityState==='visible'){visible=true;last=performance.now();view();flush();}
    else{flush(true);visible=false;}
  });
  window.addEventListener('pagehide',()=>flush(true));
  window.addEventListener('pageshow',event=>{
    if(event.persisted && document.visibilityState==='visible'){
      queue.push({id:id(),type:'pageview',path:page});flush();
    }
  });
  setInterval(()=>{if(document.visibilityState==='visible')flush();},20000);
  view();
})();
