(function(){
  const normalize = s => (s||"").toString().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/\s+/g," ").trim().toLowerCase();

  function detectType(doc){
    const txt = doc.body && doc.body.innerText ? doc.body.innerText : "";
    const n = normalize(txt);
    if (/\belogio\b/i.test(n)) return "Elogio";
    if (/\bfalta disciplinar\b/i.test(n) || /\bfalta\b.*disciplinar/i.test(n)) return "Falta Disciplinar";
    const nodes = Array.from(doc.querySelectorAll("label,div,span,p,strong"));
    for (const el of nodes){
      const t = normalize(el.textContent||"");
      if (/\belogio\b/i.test(t)) return "Elogio";
      if (/\bfalta disciplinar\b/i.test(t) || /\btipo de falta\b/i.test(t)) return "Falta Disciplinar";
    }
    return null;
  }

  (function send() {
    const type = detectType(document) || prompt('Não detectei tipo automaticamente. Digite EXATAMENTE "Elogio" ou "Falta Disciplinar":');
    if (!type) return;
    const idMatch = (document.body && document.body.innerText||"").match(/RFO[-\s#:]*([0-9A-Z\-]+)/i);
    const rfoId = idMatch ? idMatch[0] : null;
    try { window.parent.postMessage({ type, rfoId, from: "visualizar" }, location.origin); } catch(e){ console.error("Erro ao enviar mensagem ao parent:", e); }
  })();
})();
