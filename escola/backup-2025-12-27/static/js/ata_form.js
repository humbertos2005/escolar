/* static/js/ata_form.js - original features preserved + autocomplete for #aluno
   Backup do arquivo anterior será criado automaticamente ao aplicar o patch.
*/
(function () {
  function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
  function qsa(sel, ctx) { return Array.from((ctx || document).querySelectorAll(sel)); }

  /* ---------- participantes (mantido) ---------- */
  function createParticipantRow(part) {
    part = part || { name: '', cargo: '' };
    var row = document.createElement('div');
    row.className = 'participant-row mb-2';
    var nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.className = 'form-control participant-name mb-1';
    nameInput.placeholder = 'Nome';
    nameInput.value = part.name || '';
    var roleInput = document.createElement('input');
    roleInput.type = 'text';
    roleInput.className = 'form-control participant-role mb-1';
    roleInput.placeholder = 'Cargo';
    roleInput.value = part.cargo || '';
    var rowControls = document.createElement('div');
    rowControls.style.display = 'flex';
    rowControls.style.gap = '8px';
    rowControls.style.alignItems = 'center';
    var inputsWrap = document.createElement('div');
    inputsWrap.style.flex = '1';
    inputsWrap.appendChild(nameInput);
    inputsWrap.appendChild(roleInput);
    var removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-danger btn-sm remove-participant';
    removeBtn.textContent = '-';
    removeBtn.title = 'Remover participante';
    removeBtn.addEventListener('click', function () {
      row.remove();
      updateHidden();
    });
    rowControls.appendChild(inputsWrap);
    rowControls.appendChild(removeBtn);
    row.appendChild(rowControls);
    nameInput.addEventListener('input', updateHidden);
    roleInput.addEventListener('input', updateHidden);
    return row;
  }

  function renderParticipants(initialParts) {
    var container = qs('#participants-container');
    if (!container) return;
    container.innerHTML = '';
    if (!initialParts || !Array.isArray(initialParts) || initialParts.length === 0) {
      return;
    }
    initialParts.forEach(function (p) {
      var r = createParticipantRow({ name: p.name || p.nome || '', cargo: p.cargo || p.role || p.position || '' });
      container.appendChild(r);
    });
    updateHidden();
  }

  function collectParticipants() {
    var container = qs('#participants-container');
    if (!container) return [];
    var rows = qsa('.participant-row', container);
    var out = [];
    rows.forEach(function (r) {
      var name = (qs('.participant-name', r) && qs('.participant-name', r).value || '').trim();
      var cargo = (qs('.participant-role', r) && qs('.participant-role', r).value || '').trim();
      if (name || cargo) {
        out.push({ name: name, cargo: cargo });
      }
    });
    return out;
  }

  function updateHidden() {
    var hidden = qs('#participants_json');
    if (!hidden) return;
    try {
      hidden.value = JSON.stringify(collectParticipants());
    } catch (e) {
      hidden.value = '[]';
    }
  }

  /* ---------- Autocomplete aluno (com fetch de dados completos ao selecionar) ---------- */
  function normalizeStr(s) { return (s || '').toString().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }

  function makeAlunosIndex(alunos) {
    if (!Array.isArray(alunos)) return [];
    return alunos.map(function (a) {
      var nome = a.nome || a.name || a.aluno_nome || a.aluno || '';
      return {
        raw: a,
        id: a.id || a.aluno_id || a.pk || null,
        display: nome,
        displayNorm: normalizeStr(nome),
        serie: a.serie || a.serie_val || a.serie_turma || '',
        turma: a.turma || a.turma_val || '',
        responsavel: a.responsavel || a.responsavel_val || a.resp || ''
      };
    });
  }

  function buildSuggestionItem(hit, query) {
    var item = document.createElement('div');
    item.className = 'autocomplete-suggestion p-2';
    item.style.cursor = 'pointer';
    var idx = hit.displayNorm.indexOf(normalizeStr(query));
    if (idx >= 0) {
      var before = hit.display.slice(0, idx);
      var match = hit.display.slice(idx, idx + query.length);
      var after = hit.display.slice(idx + query.length);
      item.innerHTML = '<strong>' + escapeHtml(before) + '</strong><span style="text-decoration:underline;">' + escapeHtml(match) + '</span>' + escapeHtml(after);
    } else {
      item.textContent = hit.display;
    }
    var meta = document.createElement('div');
    meta.className = 'text-muted small';
    var metaParts = [];
    if (hit.serie) metaParts.push(hit.serie);
    if (hit.turma) metaParts.push(hit.turma);
    if (hit.responsavel) metaParts.push(hit.responsavel);
    if (metaParts.length) meta.textContent = metaParts.join(' • ');
    item.appendChild(meta);
    item._hit = hit;
    return item;
  }

  function escapeHtml(s) { return (s+'').replace(/[&<>"']/g, function (m) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m]; }); }

  function attachAlunoAutocomplete() {
    var input = qs('#aluno');
    var hiddenId = qs('#aluno_id');
    var hiddenNome = qs('#aluno_nome');
    var seriesEl = qs('#serie');
    var turmaEl = qs('#turma');
    var respEl = qs('#responsavel');
    var suggBox = qs('#aluno-suggestions');

    if (!input || !suggBox) return;

    var alunosIndex = makeAlunosIndex(window.ALUNOS || []);
    var activeIndex = -1;
    var currentList = [];

    function clearSuggestions() {
      suggBox.innerHTML = '';
      suggBox.classList.add('d-none');
      activeIndex = -1;
      currentList = [];
    }

    function showSuggestions(list, query) {
      suggBox.innerHTML = '';
      if (!list || list.length === 0) { clearSuggestions(); return; }
      list.slice(0, 8).forEach(function (hit) {
        var el = buildSuggestionItem(hit, query);
        el.addEventListener('mousedown', function (ev) {
          ev.preventDefault();
          selectHit(hit);
        });
        suggBox.appendChild(el);
      });
      suggBox.classList.remove('d-none');
      activeIndex = -1;
      currentList = Array.from(suggBox.querySelectorAll('.autocomplete-suggestion'));
    }

    function fillFieldsFromData(data) {
      if (!data) return;
      if (seriesEl) {
        var s = data.serie || data.serie_turma || data.serie || '';
        // se serie_turma vier no formato "S / T", mantém apenas parte antes do separador
        if (s && s.indexOf('/') !== -1) s = s.split('/')[0].trim();
        seriesEl.value = s || '';
      }
      if (turmaEl) {
        var t = data.turma || '';
        // se serie_turma contiver "S / T", tentar pegar parte após '/'
        if ((!t || t === '') && data.serie_turma && data.serie_turma.indexOf('/') !== -1) {
          t = data.serie_turma.split('/')[1].trim();
        }
        turmaEl.value = t || '';
      }
      if (respEl) {
        respEl.value = data.responsavel || data.responsavel_nome || data.nome_responsavel || '';
      }
    }

    function selectHit(hit) {
      if (!hit) return;
      input.value = hit.display || '';
      if (hiddenId) hiddenId.value = hit.id || '';
      if (hiddenNome) hiddenNome.value = hit.display || '';
      // primeiramente, preencher com o que já temos no index (se houver)
      if (seriesEl) seriesEl.value = hit.serie || '';
      if (turmaEl) turmaEl.value = hit.turma || '';
      if (respEl) respEl.value = hit.responsavel || '';
      clearSuggestions();
      input.focus();

      // Agora, solicitar dados completos ao servidor para garantir série/turma/responsável
      if (hit.id) {
        var url = '/formularios/atas/api/student/' + encodeURIComponent(hit.id);
        fetch(url, { credentials: 'same-origin' })
          .then(function (r) { if (!r.ok) throw new Error('status ' + r.status); return r.json(); })
          .then(function (data) {
            fillFieldsFromData(data || {});
          })
          .catch(function (err) {
            // falha não crítica — mantemos os valores parciais já preenchidos
            console.debug('Falha ao buscar dados do aluno:', err);
          });
      }
    }

    var debounceTimer = null;
    input.addEventListener('input', function (e) {
      var q = (input.value || '').trim();
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        if (q.length < 3) { clearSuggestions(); return; }
        var qn = normalizeStr(q);
        var matches = alunosIndex.filter(function (a) {
          return a.displayNorm.indexOf(qn) !== -1;
        });
        showSuggestions(matches, q);
      }, 180);
    });

    input.addEventListener('keydown', function (ev) {
      if (suggBox.classList.contains('d-none')) return;
      var items = currentList;
      if (!items || items.length === 0) return;
      if (ev.key === 'ArrowDown') {
        ev.preventDefault();
        activeIndex = (activeIndex + 1) % items.length;
        updateActive();
      } else if (ev.key === 'ArrowUp') {
        ev.preventDefault();
        activeIndex = (activeIndex - 1 + items.length) % items.length;
        updateActive();
      } else if (ev.key === 'Enter') {
        ev.preventDefault();
        if (activeIndex >= 0 && items[activeIndex]) {
          var hit = items[activeIndex]._hit;
          selectHit(hit);
        }
      } else if (ev.key === 'Escape') {
        clearSuggestions();
      }
    });

    function updateActive() {
      currentList.forEach(function (el, i) {
        if (i === activeIndex) {
          el.classList.add('bg-primary', 'text-white');
        } else {
          el.classList.remove('bg-primary', 'text-white');
        }
      });
      if (activeIndex >= 0 && currentList[activeIndex]) {
        currentList[activeIndex].scrollIntoView({ block: 'nearest' });
      }
    }

    input.addEventListener('blur', function () { setTimeout(clearSuggestions, 150); });
  }

  /* ---------- inicialização geral ---------- */
  function init() {
    var addBtn = qs('#add-participant');
    var container = qs('#participants-container');
    var form = qs('#ata-form');

    if (!container) return;

    var initial = [];
    try { initial = window.ATA_PARTICIPANTS || []; } catch (e) { initial = []; }
    renderParticipants(initial);

    if (addBtn) {
      addBtn.addEventListener('click', function () {
        var row = createParticipantRow();
        container.appendChild(row);
        var input = row.querySelector('.participant-name');
        if (input) input.focus();
        updateHidden();
      });
    }

    if (form) {
      form.addEventListener('submit', function (e) {
        updateHidden();
      });
    }

    updateHidden();

    // inicializar autocomplete do aluno
    try { attachAlunoAutocomplete(); } catch (e) { /* falha não crítica */ }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();