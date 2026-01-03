// Versão corrigida: evita loops de reanexação e layout thrash (resolve piscar)
(function(){
  'use strict';

  const isVisible = el => !!el && el.offsetWidth > 0 && el.offsetHeight > 0;
  const WATCH_SELECTOR = 'div.flatpickr-calendar, div.ui-datepicker, div.datepicker, .datepicker-dropdown';

  // controle global para poder desligar / depurar
  window.__datepickerFix = window.__datepickerFix || {};
  const ctx = window.__datepickerFix;
  ctx._suspended = false;

  function findActiveInput() {
    return document.querySelector('input.flatpickr-input.active, input.datepicker:focus, input.datepicker.active, input[type="date"]:focus') ||
      (document.activeElement && document.activeElement.tagName === 'INPUT' ? document.activeElement : null);
  }

  function computeHeaderZBelow(x = 10, y = 10) {
    try {
      const elems = document.elementsFromPoint(x, y);
      for (let e of elems) {
        const s = getComputedStyle(e);
        if ((s.position === 'fixed' || s.position === 'sticky') && s.display !== 'none' && s.visibility !== 'hidden') {
          const z = parseInt(s.zIndex, 10);
          if (!isNaN(z)) return Math.max(0, z - 1);
          return 999;
        }
      }
    } catch(e) {}
    return 999;
  }

  function attachBehaviorToPopup(popup) {
    if (!popup || popup._datepickerFixInstalled) return;
    popup._datepickerFixInstalled = true;
    popup.setAttribute('data-datepickerfix-ignore', '1');

    // salvar estado original
    popup._origState = { parent: popup.parentNode, next: popup.nextSibling, style: popup.getAttribute('style') || '' };

    // mover para body
    try { document.body.appendChild(popup); } catch(e){}

    // usar FIXED para posicionamento relativo à viewport
    popup.style.position = 'fixed';
    popup.style.transform = 'none';
    popup.style.willChange = 'top,left';
    popup.style.zIndex = computeHeaderZBelow();

    // encontra input alvo (pode mudar enquanto usa)
    let input = findActiveInput();

    // atualização central (usa rect relativo à viewport)
    let rafId = null;
    const updatePosition = () => {
        cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
        input = input && isVisible(input) ? input : findActiveInput();
        if (!input) return;
        const r = input.getBoundingClientRect();
        const top = Math.round(r.bottom);
        const left = Math.round(r.left);
        popup.style.top = top + 'px';
        popup.style.left = left + 'px';
        popup.style.zIndex = computeHeaderZBelow(Math.max(5, Math.round(left + 5)), Math.max(5, Math.round(top + 5)));
        });
    };

    // Capture scrolls everywhere (capturing phase) — pega scrolls internos e de janela
    const handler = () => updatePosition();
    document.addEventListener('scroll', handler, true); // important: capture = true
    window.addEventListener('resize', handler);

    // IntersectionObserver detecta movimento do input na viewport
    const io = new (window.IntersectionObserver || function(cb){ this.observe = ()=>{}; this.disconnect = ()=>{}; })((entries) => {
        handler();
    });
    try { if (input) io.observe(input); } catch(e){}

    // ResizeObserver para input/popup
    const ro = new (window.ResizeObserver || function(){ this.observe = ()=>{}; this.disconnect = ()=>{}; })(handler);
    try { if (input) ro.observe(input); ro.observe(popup); } catch(e){}

    // MutationObserver apenas para detectar remoção do popup
    const mo = new MutationObserver(muts => {
        for (const m of muts) {
        for (const n of m.removedNodes) {
            if (n === popup) {
            cleanupPopup(popup);
            return;
            }
        }
        }
    });
    mo.observe(document.body, { childList: true, subtree: true });

    // guardar referências para cleanup
    popup._datepickerFix = { handler, io, ro, mo, rafId };

    // posição inicial
    updatePosition();
    }

  function cleanupPopup(popup){
    if (!popup || !popup._datepickerFixInstalled) return;
    const s = popup._datepickerFix || {};
    (s.scrollParents || []).forEach(p => p.removeEventListener('scroll', s.handler));
    window.removeEventListener('resize', s.handler);
    try { s.ro && s.ro.disconnect(); } catch(e){}
    try { s.mo && s.mo.disconnect(); } catch(e){}
    try {
      if (popup._origState && popup._origState.parent) popup._origState.parent.insertBefore(popup, popup._origState.next);
    } catch(e){}
    popup.setAttribute('style', popup._origState && popup._origState.style || '');
    popup.removeAttribute('data-datepickerfix-ignore');
    delete popup._datepickerFix;
    delete popup._origState;
    delete popup._datepickerFixInstalled;
    if (s.rafId) cancelAnimationFrame(s.rafId);
  }

  // Observer reduzido: só age sobre nós adicionados e ignora nós marcados
  const observer = new MutationObserver(mutations => {
    if (ctx._suspended) return;
    for (const m of mutations) {
      for (const n of m.addedNodes) {
        if (!(n instanceof HTMLElement)) continue;
        if (n.matches && n.matches(WATCH_SELECTOR)) {
          if (n.hasAttribute('data-datepickerfix-ignore') || n._datepickerFixInstalled) continue;
          // pequeno delay para a lib terminar layout - mas curto
          setTimeout(()=>{ if (!n._datepickerFixInstalled) attachBehaviorToPopup(n); }, 8);
        } else {
          // se algum filho novo contém popup
          try {
            const child = n.querySelector && n.querySelector(WATCH_SELECTOR);
            if (child && !child.hasAttribute('data-datepickerfix-ignore') && !child._datepickerFixInstalled) {
              setTimeout(()=>{ if (!child._datepickerFixInstalled) attachBehaviorToPopup(child); }, 8);
            }
          } catch(e){}
        }
      }
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  // aplicar a popups já presentes (mas sem reprocessar inputs)
  document.querySelectorAll(WATCH_SELECTOR).forEach(el => {
    try { if (isVisible(el) && !el.hasAttribute('data-datepickerfix-ignore')) attachBehaviorToPopup(el); } catch(e){}
  });

  // API pública
  ctx.attachAll = () => document.querySelectorAll(WATCH_SELECTOR).forEach(el => attachBehaviorToPopup(el));
  ctx.cleanupAll = () => document.querySelectorAll(WATCH_SELECTOR).forEach(el => cleanupPopup(el));
  ctx.disconnect = () => observer.disconnect();
  ctx._observer = observer;
})();