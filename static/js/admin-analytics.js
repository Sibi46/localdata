(() => {
  const panel=document.querySelector('[data-analytics-live]');if(!panel)return;
  const status=panel.querySelector('[data-live-status]');
  async function refresh(){
    if(document.hidden)return;
    try{
      const response=await fetch(panel.dataset.url,{credentials:'same-origin',headers:{Accept:'application/json'}});
      if(!response.ok || response.redirected)throw Error();
      const data=await response.json();
      panel.querySelectorAll('[data-live-count]').forEach(node=>{node.textContent=data[node.dataset.liveCount];});
      const visitors=document.querySelector('[data-live-visitors]');
      if(visitors && Array.isArray(data.visitors)){
        visitors.replaceChildren();
        data.visitors.forEach(visit=>{
          const row=document.createElement('tr');
          ['name','path','device','last'].forEach(key=>{const cell=document.createElement('td');cell.textContent=visit[key];row.append(cell);});
          visitors.append(row);
        });
        if(!data.visitors.length){const row=document.createElement('tr'),cell=document.createElement('td');cell.colSpan=4;cell.textContent='No visitors active right now.';row.append(cell);visitors.append(row);}
      }
      status.textContent='Live counts updated just now';
    }catch{status.textContent='Live update unavailable. Refresh to retry.';}
  }
  setInterval(refresh,15000);document.addEventListener('visibilitychange',refresh);
})();
