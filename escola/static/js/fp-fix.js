(function(){
  // FP-FIX: reposicionamento dinâmico do flatpickr para inputs dentro de contêineres roláveis
  // - reposiciona ao abrir, no click, scroll/resize dos ancestrais roláveis e window
  // - garante z-index logo abaixo da navbar fixa
  function isScrollable(el){
    try{
      if(!el || el === document.documentElement) return false;
      var s = getComputedStyle(el);
      var overflowY = s.overflowY;
      if (/(auto|scroll|overlay)/.test(overflowY)) {
        return el.scrollHeight > el.clientHeight;
      }
      return false;
    }catch(e){ return false; }
  }

  function findScrollableAncestors(el){
    var ancestors = new Set();
    var cur = el;
    while(cur && cur !== document.documentElement){
      try{
        if(isScrollable(cur)) ancestors.add(cur);
      }catch(e){}
      cur = cur.parentElement;
    }
    if(document.scrollingElement) ancestors.add(document.scrollingElement);
    return Array.from(ancestors);
  }

  function repositionInstance(inst){
    try{
      if(!inst) return;
      var cal = inst.calendarContainer || inst._calendar || inst.calendar || document.querySelector('.flatpickr-calendar');
      var input = inst._input || inst.input;
      if(!cal || !input) return;
      var irect = input.getBoundingClientRect();
      cal.style.position = 'fixed';
      var calW = cal.offsetWidth || 308;
      var calH = cal.offsetHeight || 300;
      var left = Math.round(irect.right - calW);
      left = Math.max(8, Math.min(left, window.innerWidth - calW - 8));
      var top = Math.round(irect.bottom + 6);
      if (top + calH > window.innerHeight - 8) top = Math.max(8, window.innerHeight - calH - 8);
      cal.style.left = left + 'px';
      cal.style.top  = top + 'px';
      var nav = document.querySelector('nav.navbar.fixed-top') || document.querySelector('.navbar.fixed-top') || document.querySelector('nav') || document.querySelector('.navbar');
      var navZ = nav ? (parseInt(getComputedStyle(nav).zIndex,10)||1000) : 1000;
      cal.style.zIndex = String(Math.max(0, navZ - 1));
    }catch(e){ console.error('repositionInstance error', e); }
  }

  var attached = new WeakMap();

  function attachScrollHandlersToInput(input){
    if(!input || !input._flatpickr) return;
    var inst = input._flatpickr;
    if(attached.has(input)) return;
    var ancestors = findScrollableAncestors(input);
    ancestors.forEach(function(a){
      try{ a.addEventListener('scroll', function(){ repositionInstance(inst); }, {passive:true}); }catch(e){}
    });
    window.addEventListener('scroll', function(){ repositionInstance(inst); }, {passive:true});
    window.addEventListener('resize', function(){ repositionInstance(inst); }, {passive:true});
    try{
      var origOpen = inst.open;
      if(typeof origOpen === 'function' && !inst.__fp_patched_for_reposition){
        inst.open = function(){
          var r = origOpen.apply(this, arguments);
          setTimeout(function(){ repositionInstance(inst); }, 10);
          return r;
        };
        inst.__fp_patched_for_reposition = true;
      }
    }catch(e){}
    attached.set(input, true);
  }

  // Attach a instâncias existentes
  document.querySelectorAll('input').forEach(function(i){
    if(i && i._flatpickr) attachScrollHandlersToInput(i);
  });

  // Observer para novas instâncias/nós
  var mo = new MutationObserver(function(muts){
    muts.forEach(function(m){
      if(m.addedNodes && m.addedNodes.length){
        m.addedNodes.forEach(function(n){
          if(n.nodeType !== 1) return;
          if(n.tagName === 'INPUT' && n._flatpickr) attachScrollHandlersToInput(n);
          if(n.classList && n.classList.contains('flatpickr-calendar')) {
            if(window.flatpickr && flatpickr.instances){
              flatpickr.instances.forEach(function(inst){ repositionInstance(inst); });
            } else {
              document.querySelectorAll('input').forEach(function(i){
                if(i._flatpickr) repositionInstance(i._flatpickr);
              });
            }
          }
        });
      }
    });
  });
  mo.observe(document.documentElement || document.body, {childList:true, subtree:true});

  // Execução inicial para calendários abertos
  setTimeout(function(){
    if(window.flatpickr && flatpickr.instances && flatpickr.instances.length){
      flatpickr.instances.forEach(function(inst){ repositionInstance(inst); attachScrollHandlersToInput(inst._input); });
    } else {
      document.querySelectorAll('input').forEach(function(i){ if(i._flatpickr){ repositionInstance(i._flatpickr); attachScrollHandlersToInput(i); } });
    }
    console.log('FP-FIX: handlers attached and observer active.');
  }, 100);

})();
