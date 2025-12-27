(function(){
  if (window.__rfo_router_installed) return;
  window.__rfo_router_installed = true;
  const trustedOrigins = [location.origin];
  window.__rfo_router_store = window.__rfo_router_store || {};

  window.addEventListener('message', ev => {
    try {
      if (!trustedOrigins.includes(ev.origin)) return;
      const data = ev.data || {};
      const type = data.type || data.rfo_type;
      const rfoId = data.rfoId || data.rfo_id || null;
      if (!type) return;

      if (rfoId) window.__rfo_router_store[rfoId] = type;
      else window.__rfo_router_store['_last'] = type;

      const iframe = document.getElementById('iframe-tratar')
        || Array.from(document.querySelectorAll('iframe')).find(f => f.src && f.src.includes('listar_rfo'));

      if (!iframe) return;

      try {
        iframe.contentWindow.postMessage({ type, rfoId }, location.origin);
      } catch(e) {
        try { iframe.contentWindow.__rfo_incoming = { type, rfoId }; } catch(err){}
      }
    } catch(e){}
  }, false);
})();
