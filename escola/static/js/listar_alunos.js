(function(){
    // pegar rotas do elemento #routes (atributos data-*)
    const routesEl = document.getElementById('routes');
    const visualizarBase = routesEl ? routesEl.dataset.visualizarUrl : '/visualizar_aluno/0';
    const uploadBase = routesEl ? routesEl.dataset.uploadUrl : '/upload_foto/0';
    const excluirSelecionadosUrl = routesEl ? routesEl.dataset.excluirSelecionadosUrl : '/visualizacoes/alunos/excluir_selecionados';

    function buildUrl(base, id) {
        return base.replace('/0', '/' + id);
    }

    // Funções utilitárias
    function fetchJson(url) {
        return fetch(url).then(r => {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });
    }

    // --- INÍCIO: funcionalidades existentes (visualizar / upload) ---
    function openViewModalById(alunoId) {
        const url = buildUrl(visualizarBase, alunoId);
        fetchJson(url)
        .then(data => {
            if (data.error) { alert(data.error); return; }
            const a = data.aluno;
            const photoHtml = a.photo_url ? '<div style="margin-bottom:10px;"><img src="'+a.photo_url+'" alt="Foto do Aluno" style="max-width:320px;max-height:320px;display:block;margin:0 auto 16px auto;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.07);"></div>' : '';
            const html = photoHtml +
                '<table style="width:100%;">' +
                '<tr><td><strong>Nome:</strong></td><td>'+ (a.nome||'-') +'</td></tr>' +
                '<tr><td><strong>Matrícula:</strong></td><td>'+ (a.matricula||'-') +'</td></tr>' +
                '<tr><td><strong>Série:</strong></td><td>'+ (a.serie||'-') +'</td></tr>' +
                '<tr><td><strong>Turma:</strong></td><td>'+ (a.turma||'-') +'</td></tr>' +
                '<tr><td><strong>Telefone:</strong></td><td>'+ (a.telefone||'-') +'</td></tr>' +
                '<tr><td><strong>E-mail:</strong></td><td>'+ (a.email||'-') +'</td></tr>' +
                '<tr><td><strong>Endereço:</strong></td><td>'+ ((a.rua? a.rua + (a.numero? ", "+a.numero : "") : '-') ) +'</td></tr>' +
                '</table>';
            const body = document.getElementById('view-aluno-body');
            if (body) body.innerHTML = html;
            const modal = document.getElementById('modal-view-aluno');
            if (modal) modal.style.display = 'flex';
        })
        .catch(err => { alert('Erro ao carregar dados do aluno.'); console.error(err); });
    }

    function openUploadModalById(alunoId) {
        const inputId = document.getElementById('upload-aluno-id');
        if (inputId) inputId.value = alunoId;
        const url = buildUrl(visualizarBase, alunoId);
        fetchJson(url)
        .then(data => {
            const a = data.aluno || {};
            const current = document.getElementById('current-photo');
            if (current) {
                current.innerHTML = a.photo_url ? ('<p>Foto atual:</p><img src="'+a.photo_url+'" alt="Foto atual" style="max-width:220px;">') : '<p>Sem foto cadastrada.</p>';
            }
            const modal = document.getElementById('modal-upload-photo');
            if (modal) modal.style.display = 'flex';
        })
        .catch(()=> {
            const current = document.getElementById('current-photo');
            if (current) current.innerHTML = '<p>Sem foto cadastrada.</p>';
            const modal = document.getElementById('modal-upload-photo');
            if (modal) modal.style.display = 'flex';
        });
    }

    // Delegação de eventos para botões na tabela (visualizar / upload)
    document.addEventListener('click', function(e) {
        // botão visualizar
        const viewBtn = e.target.closest && e.target.closest('.btn-view');
        if (viewBtn) {
            const id = viewBtn.dataset.alunoId;
            if (id) openViewModalById(id);
            return;
        }
        // botão upload foto
        const uploadBtn = e.target.closest && e.target.closest('.btn-upload');
        if (uploadBtn) {
            const id = uploadBtn.dataset.alunoId;
            if (id) openUploadModalById(id);
            return;
        }
    });

    // fechar modais existentes
    const closeView = document.getElementById('close-view-modal');
    if (closeView) closeView.addEventListener('click', function(){ const m = document.getElementById('modal-view-aluno'); if (m) m.style.display='none'; });

    const btnSairModalView = document.getElementById('btn-sair-modal-view');
    if (btnSairModalView) btnSairModalView.addEventListener('click', function(){
        const m = document.getElementById('modal-view-aluno');
        if (m) m.style.display = 'none';
    });

    const closeUpload = document.getElementById('close-upload-modal');
    if (closeUpload) closeUpload.addEventListener('click', function(){ const m = document.getElementById('modal-upload-photo'); if (m) m.style.display='none'; });

    const btnCancelUpload = document.getElementById('btn-cancel-upload');
    if (btnCancelUpload) btnCancelUpload.addEventListener('click', function(){ const m = document.getElementById('modal-upload-photo'); if (m) m.style.display='none'; });

    // enviar foto
    const btnSubmitPhoto = document.getElementById('btn-submit-photo');
    if (btnSubmitPhoto) {
        btnSubmitPhoto.addEventListener('click', function(){
            const alunoIdEl = document.getElementById('upload-aluno-id');
            const alunoId = alunoIdEl ? alunoIdEl.value : null;
            const fileInput = document.getElementById('photo-file');
            if (!fileInput || !fileInput.files || fileInput.files.length === 0) { alert('Selecione um arquivo.'); return; }
            const fd = new FormData();
            fd.append('photo', fileInput.files[0]);
            const url = buildUrl(uploadBase, alunoId);
            fetch(url, { method: 'POST', body: fd })
            .then(r => r.json())
            .then(resp => {
                if (resp.success) {
                    alert('Foto enviada com sucesso.');
                    const m = document.getElementById('modal-upload-photo'); if (m) m.style.display='none';
                } else {
                    alert('Erro ao enviar foto: ' + (resp.error || ''));
                }
            }).catch(err => { alert('Erro ao enviar foto.'); console.error(err); });
        });
    }
    // --- FIM: funcionalidades existentes ---

    // --- INÍCIO: seleção em massa e exclusão ---
    // Elementos de controle (podem não existir em outras páginas)
    const btnSelecionarTodos = document.getElementById('btn-selecionar-todos');
    const btnExcluirSelecionados = document.getElementById('btn-excluir-selecionados');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const confirmModal = document.getElementById('confirmExcluirAlunosModal');
    const confirmList = document.getElementById('confirmExcluirAlunosList');
    const confirmExtra = document.getElementById('confirmExcluirAlunosExtra');
    const confirmProceed = document.getElementById('confirmExcluirProceed');
    const confirmCancel = document.getElementById('confirmExcluirCancel');
    const confirmClose = document.getElementById('close-confirm-modal');

    // helpers para checkboxes de alunos
    function getAlunoCheckboxes() {
        return Array.from(document.querySelectorAll('input.select-aluno'));
    }
    function getSelectedAlunoCheckboxes() {
        return getAlunoCheckboxes().filter(cb => cb.checked);
    }

    function updateDeleteButtonVisibility() {
        const any = getSelectedAlunoCheckboxes().length > 0;
        if (btnExcluirSelecionados) {
            if (any) btnExcluirSelecionados.classList.remove('d-none'); else btnExcluirSelecionados.classList.add('d-none');
        }
    }

    // Alterna seleção via botão "Selecionar Todos" (inverte estado atual)
    if (btnSelecionarTodos) {
        btnSelecionarTodos.addEventListener('click', function() {
            const cbs = getAlunoCheckboxes();
            if (cbs.length === 0) return;
            const allChecked = cbs.every(cb => cb.checked);
            cbs.forEach(cb => cb.checked = !allChecked);
            if (selectAllCheckbox) selectAllCheckbox.checked = !allChecked;
            updateDeleteButtonVisibility();
        });
    }

    // Checkbox no header sincroniza seleção
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const checked = !!selectAllCheckbox.checked;
            getAlunoCheckboxes().forEach(cb => cb.checked = checked);
            updateDeleteButtonVisibility();
        });
    }

    // Atualiza header checkbox e botão excluir ao alterar qualquer checkbox de aluno
    document.addEventListener('change', function (e) {
        if (e.target && e.target.matches('input.select-aluno')) {
            const cbs = getAlunoCheckboxes();
            if (selectAllCheckbox) selectAllCheckbox.checked = (cbs.length > 0 && cbs.every(cb => cb.checked));
            updateDeleteButtonVisibility();
        }
    });

    // Mostrar modal de confirmação quando clicar em Excluir Selecionados
    if (btnExcluirSelecionados && confirmModal) {
        btnExcluirSelecionados.addEventListener('click', function() {
            const selected = getSelectedAlunoCheckboxes();
            if (selected.length === 0) return;

            // preencher lista de nomes (limitado para evitar modal gigante)
            const MAX = 100;
            confirmList.innerHTML = '';
            selected.slice(0, MAX).forEach(cb => {
                const nome = cb.dataset.nome || cb.getAttribute('data-nome') || ('ID ' + (cb.dataset.id || cb.getAttribute('data-id')));
                const li = document.createElement('li');
                li.textContent = nome;
                confirmList.appendChild(li);
            });
            confirmExtra.textContent = selected.length > MAX ? `E mais ${selected.length - MAX}...` : '';

            // mostrar modal (usa o estilo do projeto)
            confirmModal.style.display = 'flex';
        });

        // cancelar / fechar modal
        if (confirmCancel) confirmCancel.addEventListener('click', function(){ confirmModal.style.display='none'; });
        if (confirmClose) confirmClose.addEventListener('click', function(){ confirmModal.style.display='none'; });

        // ação confirmar exclusão
        if (confirmProceed) {
            confirmProceed.addEventListener('click', function() {
                const selected = getSelectedAlunoCheckboxes();
                const ids = selected.map(cb => parseInt(cb.dataset.id || cb.getAttribute('data-id'), 10)).filter(Boolean);
                if (ids.length === 0) { confirmModal.style.display='none'; return; }

                // feedback visual
                confirmProceed.disabled = true;
                confirmProceed.textContent = 'Excluindo...';

                fetch(excluirSelecionadosUrl, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: ids })
                }).then(r => r.json())
                .then(data => {
                    // data.expected: { deleted: [ids], errors: { id: message } }
                    if (data && Array.isArray(data.deleted)) {
                        data.deleted.forEach(id => {
                            const row = document.querySelector(`#aluno-row-${id}`) || document.querySelector(`tr[data-aluno-id="${id}"]`);
                            if (row) row.remove();
                        });
                        showTemporaryAlert(`${data.deleted.length} aluno(s) excluído(s) com sucesso.`, 'success', 5000);
                    }
                    if (data && data.errors && Object.keys(data.errors).length > 0) {
                        const msgs = Object.entries(data.errors).map(([id, msg]) => `ID ${id}: ${msg}`);
                        showTemporaryAlert('Alguns erros ocorreram: ' + msgs.join('; '), 'danger', 8000);
                    }
                }).catch(err => {
                    console.error('Erro ao excluir alunos:', err);
                    showTemporaryAlert('Erro na requisição de exclusão. Veja console.', 'danger', 8000);
                }).finally(() => {
                    confirmProceed.disabled = false;
                    confirmProceed.textContent = 'Excluir';
                    confirmModal.style.display = 'none';
                    // atualizar visibilidade do botão excluir
                    updateDeleteButtonVisibility();
                });
            });
        }
    }
    // --- FIM: seleção em massa e exclusão ---

    // função de alerta temporário (insere no topo do conteúdo)
    function showTemporaryAlert(message, type='info', timeout=4000) {
        try {
            const container = document.querySelector('.container') || document.querySelector('.table-container') || document.body;
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.style.margin = '12px 0';
            alert.innerHTML = `${message} <button type="button" class="close-alert" aria-label="Fechar" style="margin-left:12px;">&times;</button>`;
            container.prepend(alert);
            const closeBtn = alert.querySelector('.close-alert');
            if (closeBtn) closeBtn.addEventListener('click', () => alert.remove());
            if (timeout > 0) setTimeout(() => { try { alert.remove(); } catch(e){} }, timeout);
        } catch(e) {
            console.warn('Não foi possível mostrar alert temporário', e);
        }
    }

})();