document.addEventListener('DOMContentLoaded', function () {
  // Botão/aba "Tratar" (ajuste o id conforme seu template)
  const btnTratar = document.querySelector('#rfo-tab-tratar') || document.querySelector('.btn-tratar-external');
  const container = document.getElementById('tratar-container');
  if (!container) return;

  function getFirstOcorrenciaId() {
    // Tente extrair data-id da primeira linha da tabela de RFOs
    let firstRow = document.querySelector('.table-rfo tbody tr[data-id]') || document.querySelector('.rfo-row[data-id]');
    if (firstRow) return firstRow.getAttribute('data-id');
    // fallback: tentar encontrar input hidden com primeiro id (caso o template o forneça)
    const hidden = document.querySelector('input[name="first_rfo_id"]');
    if (hidden) return hidden.value;
    return null;
  }

  function loadTratar(ocorrId) {
    if (!ocorrId) {
      container.innerHTML = '<div class="alert alert-warning">Nenhum RFO disponível para tratar.</div>';
      return;
    }
    container.innerHTML = '<div class="loading">Carregando formulário de tratamento...</div>';
    fetch(`/disciplinar/tratar_rfo/${ocorrId}?partial=1`, {
      credentials: 'same-origin',
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(resp => resp.ok ? resp.text() : Promise.reject(resp.statusText))
    .then(html => {
      container.innerHTML = html;
      // se o script de tratamento expõe uma inicialização, chamá-la
      if (window.initTratarRfo) {
        try { window.initTratarRfo(container); } catch (e) { console.error(e); }
      }
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `<div class="alert alert-danger">Erro ao carregar formulário: ${err}</div>`;
    });
  }

  if (btnTratar) {
    btnTratar.addEventListener('click', function (ev) {
      ev.preventDefault();
      const id = getFirstOcorrenciaId();
      loadTratar(id);
    });
  }

  // Se a URL já tiver focus=tratar (ex.: link externo), carregar automaticamente
  if (location.search.indexOf('focus=tratar') !== -1) {
    const id = getFirstOcorrenciaId();
    loadTratar(id);
  }
});