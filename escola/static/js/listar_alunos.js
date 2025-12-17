(function(){
    // pegar rotas do elemento #routes (atributos data-*)
    const routesEl = document.getElementById('routes');
    const visualizarBase = routesEl ? routesEl.dataset.visualizarUrl : '/visualizar_aluno/0';
    const uploadBase = routesEl ? routesEl.dataset.uploadUrl : '/upload_foto/0';

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

    function openViewModalById(alunoId) {
        const url = buildUrl(visualizarBase, alunoId);
        fetchJson(url)
        .then(data => {
            if (data.error) { alert(data.error); return; }
            const a = data.aluno;
            const photoHtml = a.photo_url ? '<div style="margin-bottom:10px;"><img src="'+a.photo_url+'" alt="Foto do Aluno"></div>' : '';
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

    // Delegação de eventos para botões na tabela
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

    // fechar modais
    const closeView = document.getElementById('close-view-modal');
    if (closeView) closeView.addEventListener('click', function(){ const m = document.getElementById('modal-view-aluno'); if (m) m.style.display='none'; });

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

})();