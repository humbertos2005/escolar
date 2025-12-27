(function(){
  if (window.__rfo_handler_installed) return;
  window.__rfo_handler_installed = true;

  const normalize = s => (s||"").toString().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/\s+/g," ").trim();

  function applyType(selectedText, rfoId){
    try {
      const doc = document;
      const isElogio = /elogio/i.test(selectedText);
      const isFalta = /falta/i.test(selectedText);

      const label = Array.from(doc.querySelectorAll("label,div,span,p,strong,legend,h3,h4")).find(el => /\btrata[- ]?se\b/i.test(normalize(el.textContent||"")));
      const container = label ? (label.closest(".form-group") || label.closest("fieldset") || label.closest(".card") || label.parentElement) : (doc.querySelector("form") || doc.body);
      if (!container) return;

      let disp = container.querySelector(".rfo-auto-applied");
      if (!disp) {
        disp = doc.createElement("div");
        disp.className = "rfo-auto-applied";
        disp.style.fontWeight = "700";
        disp.style.margin = "6px 0";
        disp.style.padding = "6px 8px";
        disp.style.background = "#fff8e1";
        disp.style.border = "1px solid #ffd54f";
        disp.style.borderRadius = "4px";
        if (label && label.parentNode) label.parentNode.insertBefore(disp, label.nextSibling);
        else container.insertBefore(disp, container.firstChild);
      }
      disp.textContent = selectedText;

      try {
        const radios = Array.from(container.querySelectorAll("input[type=radio]")).concat(Array.from(doc.querySelectorAll("input[type=radio]")));
        for (const r of radios) {
          const lab = r.id ? doc.querySelector("label[for=\""+r.id+"\"]") : (r.parentElement && r.parentElement.tagName && r.parentElement.tagName.toLowerCase()==="label" ? r.parentElement : null);
          const composite = ((r.value||"") + " " + (lab ? (lab.textContent||"") : "")).toLowerCase();
          if ((isElogio && /elogio/.test(composite)) || (isFalta && /falta/.test(composite)) || new RegExp(selectedText.replace(/\*/g,"\\*"),"i").test(composite)) {
            try { r.checked = true; r.dispatchEvent(new Event("change",{bubbles:true})); } catch(e){}
            if (lab && lab.classList) lab.classList.add("active");
            break;
          }
        }

        const selects = Array.from(container.querySelectorAll("select")).concat(Array.from(doc.querySelectorAll("select")));
        for (const s of selects) {
          for (let i=0;i<s.options.length;i++){
            const opt = s.options[i];
            const txt = ((opt.text||"") + " " + (opt.value||"")).toLowerCase();
            if ((isElogio && /elogio/.test(txt)) || (isFalta && /falta/.test(txt)) || new RegExp(selectedText.replace(/\*/g,"\\*"),"i").test(txt)) {
              try { s.selectedIndex = i; s.dispatchEvent(new Event("change",{bubbles:true})); } catch(e){}
              i = s.options.length; break;
            }
          }
        }
      } catch(e){}

      try {
        const classifier = Array.from(doc.querySelectorAll("fieldset, .form-fieldset, .card, legend, h3, h4, div")).find(el => /classifica.*o da falta|classificacao da falta|classificação da falta|tipo de falta/i.test(normalize(el.textContent||"")));
        if (classifier) {
          const toHide = classifier.closest("fieldset") || classifier.closest(".form-fieldset") || classifier.closest(".card") || classifier;
          const bodyH = doc.documentElement ? doc.documentElement.scrollHeight : (doc.body ? doc.body.scrollHeight : 0);
          const r = toHide.getBoundingClientRect ? toHide.getBoundingClientRect() : { height: 0 };
          const proportion = bodyH ? (r.height / bodyH) : 0;
          if (isElogio && proportion < 0.75) {
            window.__rfo_handler_backup = window.__rfo_handler_backup || [];
            window.__rfo_handler_backup.push({ el: toHide, style: { display: toHide.style.display } });
            toHide.style.display = "none";
          }
        }
      } catch(e){}
    } catch(err) {
      console.error("applyType err", err);
    }
  }

  window.addEventListener("message", ev => {
    try {
      const data = ev.data || {};
      const type = data.type || data.rfo_type;
      const rfoId = data.rfoId || null;
      if (!type) return;
      applyType(type, rfoId);
    } catch(e){}
  }, false);

  try { if (window.__rfo_incoming && (window.__rfo_incoming.type || window.__rfo_incoming.rfo_type)) { applyType(window.__rfo_incoming.type || window.__rfo_incoming.rfo_type, window.__rfo_incoming.rfoId || null); try { delete window.__rfo_incoming; } catch(e){} } } catch(e){}
})();
