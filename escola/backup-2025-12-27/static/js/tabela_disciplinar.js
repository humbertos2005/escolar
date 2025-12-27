// JS para templates/formularios/tabela_disciplinar.html
// Requer: endpoints existentes:
// - /disciplinar/buscar_alunos_json?q=...            (já presente)
// - /formularios/api/bimestres                       (criado)
// - /formularios/api/config                           (GET/POST)
// - /formularios/api/aluno_pontuacao?aluno_id=&bimestre=

document.addEventListener('DOMContentLoaded', function() {
    const alunoSearch = document.getElementById('aluno_search');
    const alunoSuggestions = document.getElementById('aluno_suggestions');
    const alunoIdInput = document.getElementById('aluno_id');
    const serieInput = document.getElementById('aluno_serie');
    const turmaInput = document.getElementById('aluno_turma');
    const bimestreSelect = document.getElementById('bimestre_select');
    const pontAnterior = document.getElementById('pontuacao_anterior');
    const pontAtual = document.getElementById('pontuacao_atual');
    const displayPont = document.getElementById('display_pontuacao');
    const displayClass = document.getElementById('display_classificacao');
    const infoAcrescimo = document.getElementById('info_acrescimo');

    const simMedida = document.getElementById('sim_medida');
    const simQtd = document.getElementById('sim_qtd');
    const simAplicar = document.getElementById('sim_aplicar');

    const btnEdit = document.getElementById('btn_edit_valores');
    const btnSalvar = document.getElementById('btn_salvar_valores');
    const btnCancelar = document.getElementById('btn_cancelar_edicao');

    const medidaInputs = {
        'advertencia_oral': document.getElementById('val_advertencia_oral'),
        'advertencia_escrita': document.getElementById('val_advertencia_escrita'),
        'suspensao_dia': document.getElementById('val_suspensao_dia'),
        'acao_educativa_dia': document.getElementById('val_acao_educativa_dia'),
        'elogio_individual': document.getElementById('val_el_individual'),
        'elogio_coletivo': document.getElementById('val_el_coletivo')
    };

    // Inicializadores (sem usar Jinja dentro do arquivo .js)
    loadBimestres();
    loadConfig();
    populateMedidasSelect();

    function loadBimestres() {
        fetch('/formularios/api/bimestres')
        .then(r => r.json())
        .then(data => {
            bimestreSelect.innerHTML = '';
            data.forEach(b => {
                const opt = document.createElement('option');
                opt.value = `${b.ano}|${b.numero}`;
                opt.textContent = `${b.ano} - ${b.numero}º Bimestre`;
                bimestreSelect.appendChild(opt);
            });
        })
        .catch(()=> {
            // fallback simples: anos atuais / bimestres 1..4
            const year = new Date().getFullYear();
            for (let i=1;i<=4;i++){
                const opt = document.createElement('option');
                opt.value = `${year}|${i}`;
                opt.textContent = `${year} - ${i}º Bimestre`;
                bimestreSelect.appendChild(opt);
            }
        });
    }

    function loadConfig() {
        fetch('/formularios/api/config')
        .then(r => r.json())
        .then(cfg => {
            medidaInputs.advertencia_oral.value = Number(cfg.advertencia_oral).toFixed(2);
            medidaInputs.advertencia_escrita.value = Number(cfg.advertencia_escrita).toFixed(2);
            medidaInputs.suspensao_dia.value = Number(cfg.suspensao_dia).toFixed(2);
            medidaInputs.acao_educativa_dia.value = Number(cfg.acao_educativa_dia).toFixed(2);
            medidaInputs.elogio_individual.value = Number(cfg.elogio_individual).toFixed(2);
            medidaInputs.elogio_coletivo.value = Number(cfg.elogio_coletivo).toFixed(2);
            // set medidas select options
            populateMedidasSelect();
        })
        .catch(()=> {
            // defaults hardcoded
            medidaInputs.advertencia_oral.value = (-0.1).toFixed(2);
            medidaInputs.advertencia_escrita.value = (-0.3).toFixed(2);
            medidaInputs.suspensao_dia.value = (-0.5).toFixed(2);
            medidaInputs.acao_educativa_dia.value = (-1.0).toFixed(2);
            medidaInputs.elogio_individual.value = (0.5).toFixed(2);
            medidaInputs.elogio_coletivo.value = (0.3).toFixed(2);
            populateMedidasSelect();
        });
    }

    function populateMedidasSelect() {
        simMedida.innerHTML = '<option value="">-- selecione --</option>';
        const mapping = [
            ['Advertência Oral','ADVERTENCIA ORAL'],
            ['Advertência Escrita','ADVERTENCIA ESCRITA'],
            ['Suspensão (dias)','SUSPENSAO'],
            ['Ação Educativa (dias)','ACAO EDUCATIVA'],
            ['Elogio Individual','ELOGIO INDIVIDUAL'],
            ['Elogio Coletivo','ELOGIO COLETIVO']
        ];
        mapping.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m[1];
            opt.textContent = m[0];
            simMedida.appendChild(opt);
        });
    }

    // Autocomplete aluno (usa endpoint disciplinar/buscar_alunos_json)
    let acTimeout = null;
    alunoSearch.addEventListener('input', function() {
        const q = this.value.trim();
        alunoSuggestions.style.display = 'none';
        alunoSuggestions.innerHTML = '';
        alunoIdInput.value = '';
        serieInput.value = '';
        turmaInput.value = '';
        pontAnterior.value = '';
        pontAtual.value = '';
        displayPont.textContent = '-';
        displayClass.textContent = '-';
        infoAcrescimo.textContent = '';
        if (acTimeout) clearTimeout(acTimeout);
        if (q.length < 1) return;
        acTimeout = setTimeout(() => {
            fetch(`/disciplinar/buscar_alunos_json?q=${encodeURIComponent(q)}`)
            .then(r => r.json())
            .then(items => {
                alunoSuggestions.innerHTML = '';
                if (!items || items.length === 0) { alunoSuggestions.style.display='none'; return; }
                items.forEach(it => {
                    const div = document.createElement('div');
                    div.className = 'item';
                    div.textContent = it.value;
                    div.dataset.id = it.id;
                    div.dataset.matricula = it.matricula || '';
                    div.dataset.nome = it.nome || '';
                    div.dataset.serie = (it.data && it.data.serie) ? it.data.serie : '';
                    div.dataset.turma = (it.data && it.data.turma) ? it.data.turma : '';
                    div.addEventListener('click', function() {
                        alunoSearch.value = this.textContent;
                        alunoIdInput.value = this.dataset.id;
                        serieInput.value = this.dataset.serie;
                        turmaInput.value = this.dataset.turma;
                        alunoSuggestions.style.display='none';
                        carregarPontuacao(this.dataset.id);
                    });
                    alunoSuggestions.appendChild(div);
                });
                alunoSuggestions.style.display = 'block';
            }).catch((err)=>{ 
                // console.log('autocomplete error', err);
                alunoSuggestions.style.display='none'; 
            });
        }, 250);
    });

    document.addEventListener('click', function(e){
        // fechar sugestões se clicar fora do input e fora do container de sugestões
        if (e.target !== alunoSearch && !alunoSuggestions.contains(e.target)) {
            alunoSuggestions.style.display = 'none';
        }
    });

    // Carrega pontuação do aluno para o bimestre selecionado
    function carregarPontuacao(aluno_id) {
        const b = bimestreSelect.value;
        if (!aluno_id || !b) return;
        const [ano, numero] = b.split('|');
        fetch(`/formularios/api/aluno_pontuacao?aluno_id=${aluno_id}&ano=${ano}&bimestre=${numero}`)
        .then(r => r.json())
        .then(data => {
            pontAnterior.value = Number(data.pontuacao_inicial).toFixed(2);
            const atual = Number(data.pontuacao_atual);
            pontAtual.value = atual.toFixed(2);
            displayPont.textContent = atual.toFixed(2);
            displayClass.textContent = classificacaoPorPontos(atual);
            if (data.acrescimo_info) {
                infoAcrescimo.textContent = data.acrescimo_info;
            } else {
                infoAcrescimo.textContent = '';
            }
        })
        .catch(()=> {
            pontAnterior.value = '8.00';
            pontAtual.value = '8.00';
            displayPont.textContent = '8.00';
            displayClass.textContent = classificacaoPorPontos(8.0);
        });
    }

    bimestreSelect.addEventListener('change', function(){
        if (alunoIdInput.value) carregarPontuacao(alunoIdInput.value);
    });

    // Simulador
    simAplicar.addEventListener('click', function(){
        const medida = simMedida.value;
        const qtd = Number(simQtd.value) || 0;
        if (!medida || !alunoIdInput.value) { alert('Selecione aluno e medida.'); return; }
        const atual = Number(pontAtual.value) || Number(pontAnterior.value) || 8.0;
        const delta = calcularDeltaSimulado(medida, qtd);
        const novo = Math.min(10.0, Math.max(0.0, atual + delta));
        pontAtual.value = novo.toFixed(2);
        displayPont.textContent = novo.toFixed(2);
        displayClass.textContent = classificacaoPorPontos(novo);
    });

    function calcularDeltaSimulado(medida, qtd) {
        // Usa os campos carregados
        qtd = Number(qtd) || 0;
        switch (medida) {
            case 'ADVERTENCIA ORAL':
                return qtd * (Number(medidaInputs['advertencia_oral'].value || -0.1));
            case 'ADVERTENCIA ESCRITA':
                return qtd * (Number(medidaInputs['advertencia_escrita'].value || -0.3));
            case 'SUSPENSAO':
                return qtd * (Number(medidaInputs['suspensao_dia'].value || -0.5));
            case 'ACAO EDUCATIVA':
                return qtd * (Number(medidaInputs['acao_educativa_dia'].value || -1.0));
            case 'ELOGIO INDIVIDUAL':
                return qtd * (Number(medidaInputs['elogio_individual'].value || 0.5));
            case 'ELOGIO COLETIVO':
                return qtd * (Number(medidaInputs['elogio_coletivo'].value || 0.3));
            default:
                return 0;
        }
    }

    function classificacaoPorPontos(p) {
        p = Number(p);
        if (p >= 10.0) return 'Excepcional (10,0)';
        if (p >= 9.0) return 'Ótimo (9,0 - 9,99)';
        if (p >= 7.0) return 'Bom (7,0 - 8,99)';
        if (p >= 5.0) return 'Regular (5,0 - 6,99)';
        if (p >= 2.0) return 'Insuficiente (2,0 - 4,99)';
        return 'Incompatível (abaixo de 2,0)';
    }

    // Edição dos valores de medidas (UI)
    btnEdit.addEventListener('click', function(e){
        e.preventDefault();
        for (const k in medidaInputs) {
            medidaInputs[k].readOnly = false;
            medidaInputs[k].classList.remove('valor-medida');
        }
        btnEdit.style.display='none';
        btnSalvar.style.display='inline-block';
        btnCancelar.style.display='inline-block';
    });

    btnCancelar.addEventListener('click', function(e){
        e.preventDefault();
        loadConfig();
        for (const k in medidaInputs) {
            medidaInputs[k].readOnly = true;
        }
        btnEdit.style.display='inline-block';
        btnSalvar.style.display='none';
        btnCancelar.style.display='none';
    });

    btnSalvar.addEventListener('click', function(e){
        e.preventDefault();
        const payload = {
            advertencia_oral: Number(medidaInputs.advertencia_oral.value) || -0.1,
            advertencia_escrita: Number(medidaInputs.advertencia_escrita.value) || -0.3,
            suspensao_dia: Number(medidaInputs.suspensao_dia.value) || -0.5,
            acao_educativa_dia: Number(medidaInputs.acao_educativa_dia.value) || -1.0,
            elogio_individual: Number(medidaInputs.elogio_individual.value) || 0.5,
            elogio_coletivo: Number(medidaInputs.elogio_coletivo.value) || 0.3
        };
        fetch('/formularios/api/config', {
            method: 'POST',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify(payload)
        }).then(r => r.json())
        .then(resp => {
            if (resp.success) {
                alert('Valores salvos com sucesso.');
                for (const k in medidaInputs) {
                    medidaInputs[k].readOnly = true;
                }
                btnEdit.style.display='inline-block';
                btnSalvar.style.display='none';
                btnCancelar.style.display='none';
            } else {
                alert('Erro ao salvar valores.');
            }
        }).catch(()=> alert('Erro ao salvar valores.'));
    });

});