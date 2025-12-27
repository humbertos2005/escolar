// static/js/registrar_fmd.js
// Versão ajustada: corrige problema em que clicar na sugestão do autocomplete
// não fixava o nome/ID no formulário. Mudança principal: usar 'mousedown'
// + preventDefault() ao selecionar item para evitar que o input perca o foco
// antes da seleção (blur race condition). Mantive restante da lógica.
(function () {
  'use strict';

  // NÃO alterar: estas constantes são definidas pelo template registrar_fmd.html
  // AUTOCOMPLETE_ALUNOS_URL, AUTOCOMPLETE_FALTAS_URL, AUTOCOMPLETE_COMPORTAMENTO_URL,
  // AUTOCOMPLETE_PONTUACAO_URL, AUTOCOMPLETE_CIRCUNSTANCIAS_URL, AUTOCOMPLETE_USUARIOS_URL

  const DEBOUNCE_MS = 300;

  // Debounce helper (returns a function that schedules fn)
  function debounce(fn, ms = DEBOUNCE_MS) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  // Generic fetcher with abort support
  function fetchJson(url, q, controller) {
    if (!q) return Promise.resolve([]);
    const fetchUrl = `${url}?q=${encodeURIComponent(q)}`;
    const opts = controller && controller.signal ? { signal: controller.signal } : {};
    return fetch(fetchUrl, opts)
      .then(r => (r.ok ? r.json() : []))
      .catch(() => {
        // fetch aborted or network error
        return [];
      });
  }

  // Small util: dedupe array by id (stringified)
  function dedupeById(arr, idKey = 'id') {
    const seen = new Set();
    const out = [];
    (arr || []).forEach(item => {
      const id = String(item[idKey]);
      if (!seen.has(id)) {
        seen.add(id);
        out.push(item);
      }
    });
    return out;
  }

  // Attach an autocomplete behavior to an input + list container
  // options: { minChars = 3, format(item) => label, onSelect(item), idKey='id' }
  function attachAutocomplete(inputEl, listEl, url, options = {}) {
    if (!inputEl || !listEl || !url) return;
    const minChars = options.minChars || 3;
    const idKey = options.idKey || 'id';
    let controller = null;

    // ensure list is empty and hidden initially
    listEl.innerHTML = '';
    listEl.classList.remove('show');

    const doSearch = (q) => {
      if (controller) {
        try { controller.abort(); } catch (e) {}
        controller = null;
      }
      controller = window.AbortController ? new AbortController() : null;
      return fetchJson(url, q, controller).then(arr => dedupeById(arr, idKey));
    };

    const renderResults = (items) => {
      listEl.innerHTML = '';
      if (!items || items.length === 0) {
        const d = document.createElement('div');
        d.textContent = 'Nenhum resultado encontrado.';
        listEl.appendChild(d);
        listEl.classList.add('show');
        return;
      }
      items.forEach(item => {
        const label = options.format ? options.format(item) : (item.value || item.descricao || item.nome || item.username || '');
        const d = document.createElement('div');
        d.textContent = label;
        d.dataset.payload = JSON.stringify(item);
        // Use mousedown to prevent input blur before selection (fix race)
        d.addEventListener('mousedown', (e) => {
          if (e && typeof e.preventDefault === 'function') e.preventDefault(); // prevent blur
          if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
          if (typeof options.onSelect === 'function') options.onSelect(item);
          listEl.innerHTML = '';
          listEl.classList.remove('show');
        });
        // keep click as fallback (some devices)
        d.addEventListener('click', (e) => {
          if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
          if (typeof options.onSelect === 'function') options.onSelect(item);
          listEl.innerHTML = '';
          listEl.classList.remove('show');
        });
        listEl.appendChild(d);
      });
      listEl.classList.add('show');
    };

    const onInput = debounce(function () {
      const q = this.value.trim();
      listEl.innerHTML = '';
      listEl.classList.remove('show');
      if (!q || q.length < minChars) return;
      doSearch(q).then(renderResults);
    }, DEBOUNCE_MS);

    inputEl.addEventListener('input', onInput);

    // close when clicking outside
    document.addEventListener('click', function (e) {
      if (e.target === inputEl) return;
      if (!listEl.contains(e.target)) {
        listEl.innerHTML = '';
        listEl.classList.remove('show');
      }
    });
  }

  // -------- ALUNO autocomplete (corrigido: usa mousedown to avoid blur race) --------
  function setupAlunoAutocomplete() {
    const alunoInput = document.getElementById('aluno_busca_fmd');
    const alunoHidden = document.getElementById('aluno_id_fmd');
    const alunoInfo = document.getElementById('aluno-info-fmd');
    let alunoList = document.getElementById('aluno_autocomplete_list_fmd');

    if (!alunoInput) return;

    // cria container de lista se não existir
    if (!alunoList) {
      alunoList = document.createElement('div');
      alunoList.id = 'aluno_autocomplete_list_fmd';
      alunoList.className = 'autocomplete-items';
      // anexa logo após o input para manter posicionamento relativo
      if (alunoInput.parentElement) alunoInput.parentElement.appendChild(alunoList);
      else document.body.appendChild(alunoList);
    }

    let timer = null;
    let controller = null;

    // fecha somente a lista de sugestões (mantém info visível quando apropriado)
    function closeList() {
      alunoList.innerHTML = '';
      alunoList.classList.remove('show');
    }

    // esconde info (usado quando clicar fora ou ao digitar nova consulta)
    function hideInfo() {
      if (alunoInfo) {
        alunoInfo.classList.remove('show');
        alunoInfo.style.opacity = '0';
        alunoInfo.style.display = 'none';
      }
    }

    function renderResults(items) {
      alunoList.innerHTML = '';
      if (!items || items.length === 0) {
        const d = document.createElement('div');
        d.textContent = 'Nenhum resultado encontrado.';
        alunoList.appendChild(d);
        alunoList.classList.add('show');
        return;
      }
      items.forEach(item => {
        const div = document.createElement('div');
        div.textContent = item.value || `${item.matricula || ''} - ${item.nome || ''}`;
        div.dataset.payload = JSON.stringify(item);

        // Use mousedown to avoid input blur BEFORE selection (this is the fix)
        div.addEventListener('mousedown', (e) => {
          if (e && typeof e.preventDefault === 'function') e.preventDefault(); // prevents input blur
          if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
          // preenche hidden e input
          if (alunoHidden) alunoHidden.value = item.id || item.ID || item.aluno_id || item.pk || '';
          alunoInput.value = item.value || `${item.matricula || ''} - ${item.nome || ''}`;
          // mostra série e turma (mantém visível)
          if (alunoInfo) {
            const s = (item.data && item.data.serie) ? item.data.serie : (item.serie || '');
            const t = (item.data && item.data.turma) ? item.data.turma : (item.turma || '');
            alunoInfo.innerHTML = `<strong>Série/Turma:</strong> ${s} ${t}`.trim();
            alunoInfo.classList.add('show');
            alunoInfo.style.opacity = '1';
            alunoInfo.style.display = 'block';
            alunoInfo.style.zIndex = '9999';
          }
          // limpa somente a lista (não esconde info)
          closeList();
        });

        // fallback click
        div.addEventListener('click', (e) => {
          if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
          if (alunoHidden) alunoHidden.value = item.id || item.ID || item.aluno_id || item.pk || '';
          alunoInput.value = item.value || `${item.matricula || ''} - ${item.nome || ''}`;
          if (alunoInfo) {
            const s = (item.data && item.data.serie) ? item.data.serie : (item.serie || '');
            const t = (item.data && item.data.turma) ? item.data.turma : (item.turma || '');
            alunoInfo.innerHTML = `<strong>Série/Turma:</strong> ${s} ${t}`.trim();
            alunoInfo.classList.add('show');
            alunoInfo.style.opacity = '1';
            alunoInfo.style.display = 'block';
            alunoInfo.style.zIndex = '9999';
          }
          closeList();
        });

        alunoList.appendChild(div);
      });
      alunoList.classList.add('show');
    }

    alunoInput.addEventListener('input', function () {
      const q = this.value.trim();
      // when typing a new query, hide the previous info (user is changing)
      if (alunoInfo) {
        alunoInfo.classList.remove('show');
        alunoInfo.style.opacity = '0';
        alunoInfo.style.display = 'none';
      }
      closeList();
      if (timer) clearTimeout(timer);
      if (!q || q.length < 3) return;
      timer = setTimeout(() => {
        // abort previous fetch
        if (controller) {
          try { controller.abort(); } catch (e) {}
          controller = null;
        }
        controller = window.AbortController ? new AbortController() : null;
        const signal = controller ? controller.signal : undefined;
        fetch(`${AUTOCOMPLETE_ALUNOS_URL}?q=${encodeURIComponent(q)}`, { signal })
          .then(r => r.ok ? r.json() : [])
          .then(arr => {
            const items = dedupeById(arr || [], 'id');
            renderResults(items);
          })
          .catch(() => {
            // silent on abort/error
          });
      }, 250);
    });

    // when clicking outside, hide both list and info
    document.addEventListener('click', function (e) {
      if (e.target === alunoInput) return;
      if (!alunoList.contains(e.target)) {
        closeList();
        hideInfo();
      }
    });
  }

  // -------- TIPOS DE FALTA (FMD) - buttons -> pills (allow duplicates) --------
  function setupTipoFaltaFmd() {
    const buttons = document.querySelectorAll('.tipo-adicionar-fmd');
    const display = document.getElementById('tipo_falta_selecionadas_fmd');
    const hidden = document.getElementById('tipo_falta_list_fmd');
    if (!buttons || !display || !hidden) return;

    const tipos = [];

    function render() {
      display.innerHTML = '';
      tipos.forEach((t, idx) => {
        const pill = document.createElement('span');
        pill.className = 'pill';
        pill.innerHTML = `${t} <span class="remove" data-idx="${idx}">&times;</span>`;
        display.appendChild(pill);
      });
      hidden.value = tipos.join(',');
    }

    buttons.forEach(b => {
      b.addEventListener('click', () => {
        const tipo = b.dataset.tipo;
        if (!tipo) return;
        tipos.push(tipo);
        render();
      });
    });

    display.addEventListener('click', (e) => {
      if (e.target.classList.contains('remove')) {
        const idx = Number(e.target.dataset.idx);
        if (!isNaN(idx)) {
          tipos.splice(idx, 1);
          render();
        }
      }
    });

    // initialize if hidden has values
    if (hidden.value && hidden.value.trim()) {
      hidden.value.split(',').map(s => s.trim()).filter(Boolean).forEach(s => tipos.push(s));
      render();
    }
  }

  // -------- ITENS/FALTAS MULTISELECT (FMD) --------
  function setupFaltasMultiselect() {
    const input = document.getElementById('falta-search-fmd');
    const list = document.getElementById('falta-autocomplete-list-fmd');
    const container = document.getElementById('falta-selecionadas-fmd');
    const hidden = document.getElementById('falta_disciplinar_ids_fmd');

    if (!input || !list || !container || !hidden) return;

    let controller = null;
    let selected = [];

    // initialize from hidden (fetch descriptions by ids)
    const initIds = (hidden.value || '').split(',').map(s => s.trim()).filter(Boolean);
    if (initIds.length) {
      // backend accepts ids-only queries; join with spaces or commas
      const q = initIds.join(' ');
      fetchJson(AUTOCOMPLETE_FALTAS_URL, q, null).then(arr => {
        arr = dedupeById(arr, 'id');
        selected = initIds.map(id => {
          const found = arr.find(a => String(a.id) === String(id));
          return found ? { id: String(found.id), descricao: found.descricao } : { id: String(id), descricao: '' };
        });
        render();
      });
    }

    function render() {
      container.innerHTML = '';
      selected.forEach(item => {
        const span = document.createElement('span');
        span.className = 'pill';
        span.innerHTML = `<strong>${item.id}</strong> - ${item.descricao || '(descrição)'} <span class="remove" data-id="${item.id}">&times;</span>`;
        container.appendChild(span);
      });
      hidden.value = selected.map(s => s.id).join(',');
    }

    function doSearch(q) {
      if (controller) {
        try { controller.abort(); } catch (e) {}
        controller = null;
      }
      controller = window.AbortController ? new AbortController() : null;
      return fetchJson(AUTOCOMPLETE_FALTAS_URL, q, controller);
    }

    const onInput = debounce(function () {
      const q = this.value.trim();
      list.innerHTML = '';
      list.classList.remove('show');
      if (!q || q.length < 3) return;
      doSearch(q).then(arr => {
        arr = dedupeById(arr, 'id');
        list.innerHTML = '';
        if (!arr.length) {
          const d = document.createElement('div'); d.textContent = 'Nenhum resultado.'; list.appendChild(d); list.classList.add('show'); return;
        }
        arr.forEach(item => {
          const d = document.createElement('div');
          d.textContent = `${item.id} - ${item.descricao}`;
          d.dataset.id = item.id;
          d.dataset.descricao = item.descricao;
          d.addEventListener('click', (e) => {
            if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
            if (!selected.find(s => String(s.id) === String(item.id))) {
              selected.push({ id: String(item.id), descricao: item.descricao });
              render();
            }
            input.value = '';
            list.innerHTML = '';
            list.classList.remove('show');
          });
          list.appendChild(d);
        });
        list.classList.add('show');
      });
    }, DEBOUNCE_MS);

    input.addEventListener('input', onInput);

    document.addEventListener('click', function (e) {
      if (e.target === input) return;
      if (!list.contains(e.target)) {
        list.innerHTML = '';
        list.classList.remove('show');
      }
    });

    container.addEventListener('click', function (e) {
      if (e.target.classList.contains('remove')) {
        const id = e.target.dataset.id;
        selected = selected.filter(s => String(s.id) !== String(id));
        render();
      }
    });

    // initial render (if hidden was empty this will just set empty)
    render();
  }

  // -------- Generic single-value autocompletes for comportamento, pontuacao, atenuantes, agravantes, gestor --------
  function setupSingleAutocomplete(inputId, listId, url, onSelectCallback, minChars = 2) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);
    if (!input || !list) return;

    attachAutocomplete(input, list, url, {
      minChars: minChars,
      format: item => item.nome || item.descricao || item.username || item.full_name || item.value || '',
      onSelect: item => {
        if (typeof onSelectCallback === 'function') onSelectCallback(item);
      },
      idKey: 'id'
    });
  }

  // -------- Setup submit behavior (fill defaults) --------
  function setupFormSubmitDefaults() {
    const form = document.getElementById('form-registrar-fmd');
    if (!form) return;
    form.addEventListener('submit', function () {
      // circunstâncias default
      const atenuantes = document.getElementById('circunstancias_atenuantes');
      const agravantes = document.getElementById('circunstancias_agravantes');
      if (atenuantes && !atenuantes.value.trim()) atenuantes.value = 'Não há';
      if (agravantes && !agravantes.value.trim()) agravantes.value = 'Não há';

      // gestor hidden: if empty, set to current session user (template fills gestor_id)
      const gestorHidden = document.getElementById('gestor_id');
      if (gestorHidden && !gestorHidden.value && typeof sessionUserId !== 'undefined') {
        gestorHidden.value = sessionUserId;
      }

      // nothing to block; form will submit normally
    });
  }

  // -------- Initialize everything (avoid double-init) --------
  function initOnce() {
    // guard
    if (window.__registrarFmdInit) return;
    window.__registrarFmdInit = true;

    setupAlunoAutocomplete();
    // --- popula série/turma se o campo aluno já estiver preenchido ---
    (function populateAlunoInfoIfNeeded() {
      const alunoInput = document.getElementById('aluno_busca_fmd');
      const alunoHidden = document.getElementById('aluno_id_fmd');
      const alunoInfo = document.getElementById('aluno-info-fmd');
      if (!alunoInput || !alunoInfo) return;

      function fetchAndShow(q) {
        if (!q) return;
        fetch(`${AUTOCOMPLETE_ALUNOS_URL}?q=${encodeURIComponent(q)}`)
          .then(r => r.ok ? r.json() : [])
          .then(arr => {
            if (!arr || !arr.length) return;
            const item = arr[0];
            if (alunoHidden && (!alunoHidden.value || alunoHidden.value === '')) {
              // se hidden vazio, preenche com o id retornado
              if (item.id) alunoHidden.value = item.id;
            }
            const s = item.data && item.data.serie ? item.data.serie : '';
            const t = item.data && item.data.turma ? item.data.turma : '';
            alunoInfo.innerHTML = `<strong>Série/Turma:</strong> ${s} ${t}`.trim();
            // garante visibilidade quando carregado no início
            alunoInfo.classList.add('show');
            alunoInfo.style.opacity = '1';
            alunoInfo.style.display = 'block';
            alunoInfo.style.zIndex = '9999';
          }).catch(() => {/* ignore */});
      }

      // tenta com o hidden (id) primeiro; se vazio, tenta com o valor do input
      const q0 = (alunoHidden && alunoHidden.value) ? alunoHidden.value.trim() : (alunoInput.value ? alunoInput.value.trim() : '');
      if (q0) fetchAndShow(q0);

      // e também atualiza quando o usuário sair do campo (blur), caso ele tenha digitado sem selecionar
      alunoInput.addEventListener('blur', function() {
        const q = (alunoHidden && alunoHidden.value) ? alunoHidden.value.trim() : (alunoInput.value ? alunoInput.value.trim() : '');
        if (q) fetchAndShow(q);
      });
    })();

    setupTipoFaltaFmd();
    setupFaltasMultiselect();

    // comportamento (single)
    setupSingleAutocomplete('comportamento', 'comportamento_autocomplete_list', AUTOCOMPLETE_COMPORTAMENTO_URL, item => {
      const hid = document.getElementById('comportamento_id');
      const inp = document.getElementById('comportamento');
      if (hid) hid.value = item.id;
      if (inp) inp.value = item.nome || item.value || inp.value;
    });

    // pontuação (single)
    setupSingleAutocomplete('pontuacao', 'pontuacao_autocomplete_list', AUTOCOMPLETE_PONTUACAO_URL, item => {
      const hid = document.getElementById('pontuacao_id');
      const inp = document.getElementById('pontuacao');
      if (hid) hid.value = item.id;
      if (inp) inp.value = item.descricao || item.value || inp.value;
    });

    // atenuantes / agravantes reuse pontuacoes endpoint
    setupSingleAutocomplete('circunstancias_atenuantes', 'atenuantes_autocomplete_list', AUTOCOMPLETE_CIRCUNSTANCIAS_URL, item => {
      const hid = document.getElementById('atenuantes_id');
      const inp = document.getElementById('circunstancias_atenuantes');
      if (hid) hid.value = item.id;
      if (inp) inp.value = item.descricao || item.nome || inp.value;
    }, 2);

    setupSingleAutocomplete('circunstancias_agravantes', 'agravantes_autocomplete_list', AUTOCOMPLETE_CIRCUNSTANCIAS_URL, item => {
      const hid = document.getElementById('agravantes_id');
      const inp = document.getElementById('circunstancias_agravantes');
      if (hid) hid.value = item.id;
      if (inp) inp.value = item.descricao || item.nome || inp.value;
    }, 2);

    // gestor autocomplete (user)
    setupSingleAutocomplete('gestor', 'gestor_autocomplete_list', AUTOCOMPLETE_USUARIOS_URL, item => {
      const hid = document.getElementById('gestor_id');
      const inp = document.getElementById('gestor');
      if (hid) hid.value = item.id;
      if (inp) inp.value = item.username || item.full_name || inp.value;
    }, 2);

    // prazo 'não há'
    const prazoNaoHa = document.getElementById('prazo_nao_ha');
    const prazoField = document.getElementById('prazo_comparecimento');
    if (prazoNaoHa && prazoField) {
      prazoNaoHa.addEventListener('change', function () {
        if (this.checked) {
          prazoField.value = '';
          prazoField.disabled = true;
        } else {
          prazoField.disabled = false;
        }
      });
    }

    setupFormSubmitDefaults();
  }

  // DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOnce);
  } else {
    initOnce();
  }

})();