// static/js/tratar_rfo.js
// Versão ajustada: mantem botão "Cancelar reclassificação" visível após reclassificar (não remove a UI).
// Ajuste mínimo aplicado ao handler de sucesso para NÃO chamar clearReclassifyUI() e manter o cancel disponível.
// Também adiciona suporte para modo "Elogio": oculta/dispensa campos de falta/medida no front-end.

(function () {
  'use strict';

  // Prevent double-initialization if script is included twice
  if (window.__trfInitialized) return;
  window.__trfInitialized = true;

  console.log('tratar_rfo.js loaded');

  const DEBOUNCE_MS = 300;

  // Utility debounce that returns a cancel function
  function debounce(fn, ms) {
    let handle = null;
    return {
      run(...args) {
        if (handle) clearTimeout(handle);
        handle = setTimeout(() => {
          handle = null;
          try {
            fn(...args);
          } catch (e) {
            console.error('debounced fn error', e);
          }
        }, ms);
      },
      cancel() {
        if (handle) {
          clearTimeout(handle);
          handle = null;
        }
      }
    };
  }

  function qs(sel) { return document.querySelector(sel); }
  function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }

  function init() {
    const faltaSearch = document.getElementById('falta_search');
    const faltaList = document.getElementById('falta_autocomplete_list');
    const faltaSelectedContainer = document.getElementById('falta_selecionadas');
    const faltaHidden = document.getElementById('falta_disciplinar_ids');

    const tipoButtons = qsa('.tipo-adicionar');
    const tipoSelectedContainer = document.getElementById('tipo_falta_selecionadas');
    const tipoHidden = document.getElementById('tipo_falta_list');

    const alunoIdInput = qs('input[name="aluno_id"]');
    const resultEl = document.getElementById('reincidenciaResult');
    const reclassifyContainer = document.getElementById('reclassifyContainer');
    const form = document.getElementById('form-tratar-rfo');
    // -- Inserir imediatamente após: const form = document.getElementById('form-tratar-rfo');
    if (form) {
      form.addEventListener('submit', function (ev) {
        // garante que existam hidden inputs com os valores atuais antes do envio
        function ensureHidden(name, value) {
          let el = form.querySelector('[name="' + name + '"]');
          if (!el) {
            el = document.createElement('input');
            el.type = 'hidden';
            el.name = name;
            form.appendChild(el);
          }
          el.value = value === undefined || value === null ? '' : String(value);
        }

        // valor que o JS já determina em runtime (form.dataset.tipo pode ser preenchido)
        ensureHidden('tipo_rfo', form.dataset.tipo || '');

        // campos que existem no form (selects/inputs) — o valor atual será copiado para hidden
        const selTrat = form.querySelector('select[name="tratamento_classificacao"]');
        ensureHidden('tratamento_classificacao', selTrat ? selTrat.value : '');

        const selMed = form.querySelector('select[name="medida_aplicada"]');
        ensureHidden('medida_aplicada', selMed ? selMed.value : '');

        // sinaliza explicitamente ao backend se este RFO deve ser tratado como elogio
        // isElogio() é a função já presente no script (se não estiver, substitua por verificação simples)
        try {
          ensureHidden('is_elogio', (typeof isElogio === 'function' && isElogio()) ? '1' : '0');
        } catch (e) {
          // fallback seguro
          ensureHidden('is_elogio', '0');
        }
      }, true); // use capture=true para rodar antes de handlers que previnam envio
    }

    // New: references to the two fieldsets we may hide/show (ids must exist in template)
    const fsClassificacao = document.getElementById('fieldset-classificacao');
    const fsMedida = document.getElementById('fieldset-medida');
    const medidaSelect = document.getElementById('medida_aplicada');

    // controllers for fetches
    let searchController = null;
    let checkController = null;

    // state
    let selectedFaltas = []; // array of { id, descricao }
    let selectedTipos = [];  // array of strings

    // safety checks
    if (!form) {
      console.log('tratar_rfo.js: form not found, aborting init');
      return; // form not found -> nothing to do
    }
    // Initialize flags to avoid double wiring
    if (form.dataset.trfInit === '1') {
      console.log('tratar_rfo.js: already initialized');
      return;
    }
    form.dataset.trfInit = '1';

    // helper: dedupe by id (preserve order)
    function dedupeById(arr) {
      const seen = new Set();
      const out = [];
      (arr || []).forEach(item => {
        const k = String(item.id);
        if (!seen.has(k)) {
          seen.add(k);
          out.push(item);
        }
      });
      return out;
    }

    // Ensure there's a hidden reincidencia field for submission and JS updates.
    let reincHidden = document.getElementById('reincidencia_hidden');
    if (!reincHidden) {
      reincHidden = document.createElement('input');
      reincHidden.type = 'hidden';
      reincHidden.id = 'reincidencia_hidden';
      reincHidden.name = 'reincidencia';
      reincHidden.value = (typeof window.__initial_reincidencia !== 'undefined') ? String(window.__initial_reincidencia) : '0';
      form.appendChild(reincHidden);
    }

    // Render selected faltas pills and update hidden
    function renderFaltas() {
      if (!faltaSelectedContainer) return;
      faltaSelectedContainer.innerHTML = '';
      selectedFaltas.forEach(item => {
        const pill = document.createElement('span');
        pill.className = 'pill';
        const desc = item.descricao || '(descrição não carregada)';
        pill.innerHTML = `<strong>${item.id}</strong> - ${escapeHtml(desc)} <span class="remove" data-id="${escapeHtml(String(item.id))}">&times;</span>`;
        faltaSelectedContainer.appendChild(pill);
      });
      if (faltaHidden) {
        const ids = selectedFaltas.map(i => i.id);
        faltaHidden.value = ids.join(',');
        // dispatch change for listeners
        const ev = new Event('change', { bubbles: true });
        faltaHidden.dispatchEvent(ev);
      }
    }

    // Render tipos and update hidden
    function renderTipos() {
      if (!tipoSelectedContainer) return;
      tipoSelectedContainer.innerHTML = '';
      selectedTipos.forEach((t, idx) => {
        const pill = document.createElement('span');
        pill.className = 'pill';
        pill.innerHTML = `${escapeHtml(t)} <span class="remove" data-idx="${idx}">&times;</span>`;
        tipoSelectedContainer.appendChild(pill);
      });
      if (tipoHidden) {
        tipoHidden.value = selectedTipos.join(',');
      }
    }

    // Basic escaping to avoid XSS from server content
    function escapeHtml(s) {
      if (s === null || s === undefined) return '';
      return String(s).replace(/[&<>"']/g, function (m) {
        return { '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[m];
      });
    }

    // Dropdown visibility helpers
    function setDropdownVisible(visible) {
      if (!faltaList) return;
      if (visible) {
        faltaList.classList.add('show');
        if (getComputedStyle(faltaList).display === 'none') faltaList.style.display = 'block';
      } else {
        faltaList.classList.remove('show');
        if (getComputedStyle(faltaList).display !== 'none') faltaList.style.display = 'none';
      }
    }
    function closeDropdown() {
      if (!faltaList) return;
      faltaList.innerHTML = '';
      setDropdownVisible(false);
    }

    // Fetch functions with AbortController
    function fetchFaltas(q) {
      if (!faltaList) return Promise.resolve([]);
      if (searchController) {
        try { searchController.abort(); } catch (e) {}
        searchController = null;
      }
      searchController = window.AbortController ? new AbortController() : null;
      const signal = searchController ? searchController.signal : undefined;
      const url = `/disciplinar/api/faltas_busca?q=${encodeURIComponent(q)}`;
      return fetch(url, { signal })
        .then(res => res.ok ? res.json() : [])
        .then(arr => Array.isArray(arr) ? arr : [])
        .catch(err => {
          // aborted or other error
          return [];
        });
    }

    // Check reincidencia API
    function checkReincidenciaUsing(faltaIdOrDescricao) {
      if (!resultEl || !alunoIdInput) return Promise.resolve(null);
      const alunoId = alunoIdInput.value;
      if (!alunoId) return Promise.resolve(null);

      if (checkController) {
        try { checkController.abort(); } catch (e) {}
        checkController = null;
      }
      checkController = window.AbortController ? new AbortController() : null;
      const signal = checkController ? checkController.signal : undefined;

      let url = `/disciplinar/api/check_reincidencia?aluno_id=${encodeURIComponent(alunoId)}`;
      if (!faltaIdOrDescricao) {
        // nothing to check
        return Promise.resolve(null);
      }
      if (/^\d+$/.test(String(faltaIdOrDescricao))) {
        url += `&falta_id=${encodeURIComponent(faltaIdOrDescricao)}`;
      } else {
        url += `&descricao=${encodeURIComponent(faltaIdOrDescricao)}`;
      }

      console.log('checkReincidencia: calling', url);
      return fetch(url, { signal })
        .then(res => res.ok ? res.json() : null)
        .catch(err => {
          console.error('checkReincidencia fetch error', err);
          return null;
        });
    }

    function showResult(text, color) {
      if (!resultEl) return;
      resultEl.textContent = text || '';
      resultEl.style.color = color || '#000';
    }

    function clearReclassifyUI() {
      if (!reclassifyContainer) return;
      reclassifyContainer.innerHTML = '';
      const hidden = form.querySelector('input[name="ocorrencia_to_reclassify"]');
      if (hidden) hidden.remove();
    }

    // Updated reclassify UI: buttons (LEVE / MÉDIA / GRAVE) with Cancel action
    function showReclassifyUI(last) {
      if (!reclassifyContainer) return;
      reclassifyContainer.innerHTML = '';

      const p = document.createElement('p');
      p.innerHTML = 'Já existe lançamento desta falta para o aluno. Último tipo: <strong>' + escapeHtml(last.tipo || '-') + '</strong>';
      reclassifyContainer.appendChild(p);

      const label = document.createElement('label');
      label.textContent = 'Deseja reclassificar o tipo para:';
      reclassifyContainer.appendChild(label);

      const typesWrap = document.createElement('div');
      typesWrap.className = 'reclassify-types';
      const TYPES = ['LEVE', 'MÉDIA', 'GRAVE'];

      // create buttons reusing same classes as Tipo de Falta so layout is identical
      TYPES.forEach(t => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'button tipo-adicionar reclassify-btn';
        b.textContent = t;
        b.dataset.tipo = t;
        b.addEventListener('click', function () {
          this.classList.toggle('active');
        });
        typesWrap.appendChild(b);
      });

      reclassifyContainer.appendChild(typesWrap);

      const spacer = document.createElement('div');
      spacer.style.marginTop = '8px';
      reclassifyContainer.appendChild(spacer);

      const actionsWrap = document.createElement('div');
      actionsWrap.style.marginTop = '8px';
      actionsWrap.style.display = 'flex';
      actionsWrap.style.gap = '8px';
      reclassifyContainer.appendChild(actionsWrap);

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-warning';
      btn.textContent = 'Reclassificar lançamento anterior';
      btn.style.marginTop = '0px';
      actionsWrap.appendChild(btn);

      // Cancel button
      const cancelBtn = document.createElement('button');
      cancelBtn.type = 'button';
      cancelBtn.className = 'btn btn-secondary';
      cancelBtn.textContent = 'Cancelar reclassificação';
      cancelBtn.style.marginTop = '0px';
      actionsWrap.appendChild(cancelBtn);

      // hidden to store ocorrencia id to reclassify on server (also useful for backend)
      let hidden = form.querySelector('input[name="ocorrencia_to_reclassify"]');
      if (!hidden) {
        hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'ocorrencia_to_reclassify';
        form.appendChild(hidden);
      }
      hidden.value = last.id;

      btn.addEventListener('click', function () {
        const selected = Array.from(typesWrap.querySelectorAll('button.active')).map(b => b.dataset.tipo);
        if (!selected.length) {
          alert('Informe ao menos uma nova tipificação');
          return;
        }
        const newTipo = selected.join(',');
        const fd = new FormData();
        fd.append('ocorrencia_id', last.id);
        fd.append('new_tipo', newTipo);

        // Indicate request in UI
        btn.disabled = true;
        btn.textContent = 'Enviando...';
        // keep cancel available while request runs
        cancelBtn.disabled = false;

        fetch('/disciplinar/reclassificar_ocorrencia', {
          method: 'POST',
          body: fd
        }).then(r => r.json()).then(resp => {
          if (resp && resp.success) {
            alert('Reclassificação efetuada com sucesso.');
            // mark reincidencia as true
            if (reincHidden) reincHidden.value = '1';
            // update result text to reflect reclassification
            showResult('SIM (reclassificado)', 'green');

            // DO NOT remove reclassify UI here — keep Cancel visible as requested.
            // Instead: disable type buttons and update the reclass button to reflect success,
            // but keep cancelBtn present so user can still cancel/close UI.
            btn.textContent = 'Reclassificado';
            btn.classList.add('disabled');
            btn.disabled = true;

            // disable type buttons to avoid further edits
            Array.from(typesWrap.querySelectorAll('button')).forEach(b => {
              b.disabled = true;
              b.classList.remove('active');
            });

            // ensure cancel button is enabled so the user can dismiss
            cancelBtn.disabled = false;

            // log for debugging
            console.log('reclassificacao: success, UI preserved with cancel available.');

          } else {
            alert('Erro ao reclassificar: ' + (resp && resp.error ? resp.error : 'Erro desconhecido'));
            btn.disabled = false;
            btn.textContent = 'Reclassificar lançamento anterior';
          }
        }).catch(err => {
          console.error(err);
          alert('Erro ao chamar endpoint de reclassificação.');
          btn.disabled = false;
          btn.textContent = 'Reclassificar lançamento anterior';
        });
      });

      cancelBtn.addEventListener('click', function () {
        // Cancel: remove hidden ocorrencia id, clear UI and restore result label to SIM (if it was)
        const hidden = form.querySelector('input[name="ocorrencia_to_reclassify"]');
        if (hidden) hidden.remove();

        // keep reincidencia hidden as-is (typically '1' because we are inside reclassify)
        if (reincHidden) {
          // ensure label remains SIM if reincHidden indicates exists
          if (reincHidden.value === '1') showResult('SIM', 'green');
          else if (reincHidden.value === '0') showResult('NÃO', 'red');
          else showResult('', '#000');
        }

        // clear the reclassify area (user closed)
        reclassifyContainer.innerHTML = '';

        console.log('reclassificacao: cancelled/closed by user.');
      });
    }

    // decide which falta identifier to use for reincidencia checking: first selected id OR current input text
    function decideFaltaIdentifier() {
      if (selectedFaltas && selectedFaltas.length) {
        return String(selectedFaltas[0].id);
      }
      if (faltaHidden && faltaHidden.value && faltaHidden.value.trim()) {
        const first = faltaHidden.value.split(',').map(s => s.trim()).filter(Boolean)[0];
        if (first) return String(first);
      }
      if (faltaSearch && faltaSearch.value && faltaSearch.value.trim()) {
        return faltaSearch.value.trim();
      }
      return null;
    }

    // checkReincidencia wrapper with debounce
    const debouncedCheck = debounce(function () {
      const identifier = decideFaltaIdentifier();
      console.log('debouncedCheck invoked, identifier=', identifier);
      if (!identifier || !alunoIdInput || !alunoIdInput.value) {
        showResult('');
        clearReclassifyUI();
        return;
      }
      showResult('Verificando...', '#666');
      checkReincidenciaUsing(identifier).then(data => {
        console.log('checkReincidencia result ->', data);
        if (!data) {
          showResult('');
          clearReclassifyUI();
          return;
        }
        if (data.exists) {
          // update hidden reincidencia to 1
          if (reincHidden) reincHidden.value = '1';
          showResult('SIM', 'green');
          if (data.last) {
            showReclassifyUI(data.last);
          } else {
            clearReclassifyUI();
          }
        } else {
          // update hidden reincidencia to 0
          if (reincHidden) reincHidden.value = '0';
          showResult('NÃO', 'red');
          clearReclassifyUI();
        }
      }).catch(err => {
        console.error(err);
        showResult('Erro ao checar reincidência', 'orange');
      });
    }, DEBOUNCE_MS);

    // Initialize selectedFaltas from hidden input if present
    if (faltaHidden && faltaHidden.value && faltaHidden.value.trim()) {
      const ids = String(faltaHidden.value).split(',').map(s => s.trim()).filter(Boolean);
      const unique = [...new Set(ids)];
      selectedFaltas = unique.map(id => ({ id: id, descricao: '' }));
      if (unique.length) {
        // fetch descriptions
        fetchFaltas(unique.join(' ')).then(arr => {
          const lookup = {};
          (arr || []).forEach(a => { lookup[String(a.id)] = a.descricao; });
          selectedFaltas = selectedFaltas.map(s => ({ id: s.id, descricao: lookup[String(s.id)] || s.descricao }));
          renderFaltas();
          debouncedCheck.run();
        }).catch(() => {
          renderFaltas();
          debouncedCheck.run();
        });
      } else {
        renderFaltas();
        debouncedCheck.run();
      }
    } else {
      renderFaltas();
      debouncedCheck.run();
    }

    // Autocomplete handlers
    if (faltaSearch && faltaList) {
      // handle input with debounce
      let localDebounce = debounce(function () {
        const q = faltaSearch.value.trim();
        if (!q || q.length < 3) {
          closeDropdown();
          return;
        }
        fetchFaltas(q).then(results => {
          // If input changed while fetching, ignore if too short
          if (!faltaSearch.value || faltaSearch.value.trim().length < 3) {
            closeDropdown();
            return;
          }
          faltaList.innerHTML = '';
          if (!results || !results.length) {
            const d = document.createElement('div');
            d.textContent = 'Nenhum resultado encontrado.';
            faltaList.appendChild(d);
            setDropdownVisible(true);
            return;
          }
          console.log('fetchFaltas results count=', results.length);
          results.forEach(item => {
            const div = document.createElement('div');
            div.textContent = `${item.id} - ${item.descricao}`;
            div.dataset.id = String(item.id);
            div.dataset.descricao = item.descricao || '';
            div.addEventListener('click', function () {
              const id = this.dataset.id;
              const descricao = this.dataset.descricao || '';
              console.log('item selecionado id=', id, 'descricao=', descricao);
              if (!selectedFaltas.find(s => String(s.id) === String(id))) {
                selectedFaltas.push({ id: id, descricao: descricao });
                selectedFaltas = dedupeById(selectedFaltas);
                renderFaltas();
                debouncedCheck.run();
              }
              faltaSearch.value = '';
              closeDropdown();
            });
            faltaList.appendChild(div);
          });
          setDropdownVisible(true);
        });
      }, DEBOUNCE_MS);

      faltaSearch.addEventListener('input', function () {
        localDebounce.run();
      });

      // accessibility & keyboard support (Enter selects first)
      faltaSearch.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          const first = faltaList && faltaList.querySelector('div[data-id]');
          if (first) first.click();
        }
      });

      // close dropdown on outside click
      document.addEventListener('click', function (e) {
        if (e.target === faltaSearch) return;
        if (!faltaList.contains(e.target)) closeDropdown();
      });
    }

    // Removing selected falta on click of remove icon
    if (faltaSelectedContainer) {
      faltaSelectedContainer.addEventListener('click', function (e) {
        if (e.target && e.target.classList.contains('remove')) {
          const id = e.target.dataset.id;
          selectedFaltas = selectedFaltas.filter(s => String(s.id) !== String(id));
          renderFaltas();
          debouncedCheck.run();
        }
      });
    }

    // Monitor changes on hidden (in case other scripts change it)
    if (faltaHidden) {
      faltaHidden.addEventListener('change', function () {
        // sync selectedFaltas if hidden changed externally (basic)
        const ids = String(faltaHidden.value || '').split(',').map(s => s.trim()).filter(Boolean);
        if (ids.length === 0 && selectedFaltas.length === 0) return;
        const same = ids.length === selectedFaltas.length && ids.every((v, i) => String(selectedFaltas[i].id) === String(v));
        if (!same) {
          selectedFaltas = ids.map(id => ({ id: id, descricao: '' }));
          if (ids.length) {
            fetchFaltas(ids.join(' ')).then(arr => {
              const lookup = {};
              (arr || []).forEach(a => { lookup[String(a.id)] = a.descricao; });
              selectedFaltas = selectedFaltas.map(s => ({ id: s.id, descricao: lookup[String(s.id)] || s.descricao }));
              renderFaltas();
              debouncedCheck.run();
            }).catch(() => {
              renderFaltas();
              debouncedCheck.run();
            });
          } else {
            renderFaltas();
            debouncedCheck.run();
          }
        }
      });
    }

    // TIPOS handling (buttons -> pills)
    if (tipoSelectedContainer && tipoButtons && tipoButtons.length) {
      // initialize from hidden
      if (tipoHidden && tipoHidden.value && String(tipoHidden.value).trim()) {
        selectedTipos = String(tipoHidden.value).split(',').map(s => s.trim()).filter(Boolean);
      } else {
        selectedTipos = [];
      }
      renderTipos();

      // attach handlers to buttons
      tipoButtons.forEach(btn => {
        if (btn.dataset.trfBtnInit) return;
        btn.dataset.trfBtnInit = '1';
        btn.addEventListener('click', function () {
          const tipo = this.dataset.tipo;
          if (!tipo) return;
          selectedTipos.push(tipo);
          renderTipos();
        });
      });

      // remove tipo pill
      tipoSelectedContainer.addEventListener('click', function (e) {
        if (e.target && e.target.classList.contains('remove')) {
          const idx = parseInt(e.target.dataset.idx, 10);
          if (!isNaN(idx)) {
            selectedTipos.splice(idx, 1);
            renderTipos();
          }
        }
      });

      // Helper: determine if current RFO is an elogio
      function isElogio() {
        const formTipo = (form && form.dataset && form.dataset.tipo) ? String(form.dataset.tipo).toLowerCase() : '';
        if (formTipo && formTipo.indexOf('elogio') !== -1) return true;
        const radio = document.querySelector('input[name="tipo_rfo"]:checked');
        if (radio && String(radio.value).toLowerCase().indexOf('elogio') !== -1) return true;
        return false;
      }

      // UI adjuster: hide fieldsets and remove required attributes when Elogio
      function applyTipoMode() {
        const elog = isElogio();
        if (elog) {
          // hide classification and medida blocks
          if (fsClassificacao) fsClassificacao.style.display = 'none';
          if (fsMedida) fsMedida.style.display = 'none';
          // remove required on medida select to avoid browser blocking
          if (medidaSelect) medidaSelect.removeAttribute('required');
          // clear any selected types/faltas so validation won't require them
          selectedTipos = [];
          selectedFaltas = [];
          renderTipos();
          renderFaltas();
          // show a blue informative message (insert or reuse an element)
          let note = document.getElementById('elogio-note');
          if (!note) {
            note = document.createElement('div');
            note.id = 'elogio-note';
            note.style.background = '#e9f7ff';
            note.style.borderLeft = '4px solid #007bff';
            note.style.padding = '10px';
            note.style.margin = '8px 0 16px 0';
            note.style.color = '#0b63c6';
            note.style.fontWeight = '600';
            note.textContent = 'RFO TRATA-SE DE UM ELOGIO';
            // insert before the first fieldset if possible
            if (fsClassificacao && fsClassificacao.parentNode) fsClassificacao.parentNode.insertBefore(note, fsClassificacao);
            else if (fsMedida && fsMedida.parentNode) fsMedida.parentNode.insertBefore(note, fsMedida);
            else form.insertBefore(note, form.firstChild);
          }
        } else {
          // show classification and medida blocks
          if (fsClassificacao) fsClassificacao.style.display = '';
          if (fsMedida) fsMedida.style.display = '';
          // restore required on medida select (if element exists)
          if (medidaSelect) medidaSelect.setAttribute('required', 'required');
          // remove the elogio note if exists
          const note = document.getElementById('elogio-note');
          if (note) note.remove();
        }
      }

      // initial apply
      applyTipoMode();

      // If radios exist, watch for changes to apply mode dynamically
      const tipoRadios = qsa('input[name="tipo_rfo"]');
      if (tipoRadios && tipoRadios.length) {
        tipoRadios.forEach(r => r.addEventListener('change', function () {
          // update dataset so other parts can read it
          form.dataset.tipo = (r && r.value) ? String(r.value).toLowerCase() : '';
          applyTipoMode();
        }));
      }

      // validate on submit — now conditional on whether RFO is Elogio
      form.addEventListener('submit', function (e) {
        const elog = isElogio();
        if (!elog) {
          if (!selectedTipos || selectedTipos.length === 0) {
            e.preventDefault();
            alert('Por favor, adicione ao menos um Tipo de Falta antes de salvar o tratamento.');
            return false;
          }
          if (!selectedFaltas || selectedFaltas.length === 0) {
            e.preventDefault();
            alert('A descrição da falta é obrigatória. Adicione pelo menos um item/descrição.');
            return false;
          }
        } else {
          // Elogio: ensure hidden fields don't block server-side assumptions
          if (tipoHidden) tipoHidden.value = '';
          if (faltaHidden) faltaHidden.value = '';
          if (medidaSelect) medidaSelect.removeAttribute('required');
        }
        if (tipoHidden) tipoHidden.value = selectedTipos.join(',');
        if (faltaHidden) faltaHidden.value = selectedFaltas.map(i => i.id).join(',');
        return true;
      });
    }

    // LISTENERS: radio Reincidencia change -> re-check
    const reincRadios = qsa('input[name="reincidencia"]');
    if (reincRadios && reincRadios.length) {
      reincRadios.forEach(r => r.addEventListener('change', function () {
        // Delay a little to allow radio to set before checking
        setTimeout(() => debouncedCheck.run(), 120);
      }));
    }

    // initial check
    debouncedCheck.run();
  }

  // Initialize when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();