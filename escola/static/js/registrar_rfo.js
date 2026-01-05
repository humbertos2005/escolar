// registrar_rfo.js - Versão limpa e funcional

// Contador de caracteres
function updateCharCounter() {
    const relatoTextarea = document.getElementById('relato_observador');
    const charCounter = document.querySelector('.char-counter');
    
    if (! relatoTextarea || !charCounter) return;
    
    const length = relatoTextarea.value. length;
    charCounter.textContent = `${length}/500 caracteres`;
    charCounter.style.color = length > 450 ? '#e74c3c' : '#7f8c8d';
}

// Função de Autocomplete - CORRIGIDA
function autocomplete(inp, hidden_inp, fetch_url, callback) {
    if (!inp || inp._autocompleteBound) return;
    inp._autocompleteBound = true;

    let currentFocus = -1;

    function closeAllLists() {
        const items = document.getElementsByClassName('autocomplete-items');
        Array.from(items).forEach(item => {
            if (item.parentNode) item.parentNode.removeChild(item);
        });
        currentFocus = -1;
    }

    inp.addEventListener('input', function() {
        const val = this.value. trim();
        closeAllLists();
        
        if (! val || val.length < 3) {
            if (callback) callback(null, null);
            return;
        }

        const listDiv = document.createElement('DIV');
        listDiv.setAttribute('id', this.id + '-autocomplete-list');
        listDiv.setAttribute('class', 'autocomplete-items');
        this.parentNode.appendChild(listDiv);

        fetch(fetch_url + '?q=' + encodeURIComponent(val))
            .then(response => response. json())
            .then(arr => {
                if (! arr || arr.length === 0) {
                    listDiv.innerHTML = '<div style="padding: 10px;color:#999;">Nenhum resultado encontrado</div>';
                    return;
                }

                arr.forEach(item => {
                    const itemDiv = document.createElement('DIV');
                    itemDiv.innerHTML = item.value;
                    itemDiv.dataset.id = item.id;
                    itemDiv.dataset.data = JSON.stringify(item. data);

                    // CRÍTICO: mousedown previne conflito com blur
                    itemDiv.addEventListener('mousedown', function(e) {
                        e. preventDefault();
                        e.stopPropagation();

                        inp.value = item.value;
                        if (hidden_inp) hidden_inp.value = item.id;
                        if (callback) callback(item.id, item.data);
                        
                        closeAllLists();
                    });

                    listDiv.appendChild(itemDiv);
                });
            })
            .catch(error => {
                console. error('Erro ao buscar:', error);
                listDiv.innerHTML = '<div style="padding:10px;color:#dc3545;">Erro ao buscar</div>';
            });
    });

    inp.addEventListener('keydown', function(e) {
        const list = document.getElementById(this.id + '-autocomplete-list');
        if (! list) return;
        
        const items = list. getElementsByTagName('div');
        if (!items. length) return;

        if (e.keyCode === 40) { // Seta baixo
            currentFocus++;
            if (currentFocus >= items.length) currentFocus = 0;
            setActive(items);
            e.preventDefault();
        } else if (e.keyCode === 38) { // Seta cima
            currentFocus--;
            if (currentFocus < 0) currentFocus = items.length - 1;
            setActive(items);
            e.preventDefault();
        } else if (e.keyCode === 13) { // Enter
            e.preventDefault();
            if (currentFocus > -1) {
                items[currentFocus].dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
            }
        } else if (e.keyCode === 27) { // Escape
            closeAllLists();
        }
    });

    function setActive(items) {
        Array.from(items).forEach((item, index) => {
            item.classList.toggle('autocomplete-active', index === currentFocus);
        });
        if (items[currentFocus]) {
            items[currentFocus]. scrollIntoView({ block: 'nearest' });
        }
    }

    document.addEventListener('click', function(e) {
        if (e.target !== inp) closeAllLists();
    });
}

// Callback para exibir info do aluno
function buildAlunoInfoCallback(infoElement) {
    return function(alunoId, itemData) {
        if (!infoElement) return;
        
        if (alunoId && itemData && itemData.serie) {
            infoElement.innerHTML = `<strong>Série/Turma:</strong> ${itemData.serie} - ${itemData.turma}`;
            infoElement.classList.add('show');
        } else {
            infoElement.innerHTML = '';
            infoElement.classList. remove('show');
        }
    };
}

// Inicializador global para elementos dinâmicos
window.initAlunoSearch = function(inputEl, hiddenEl, infoEl) {
    if (!inputEl || inputEl._alunoSearchInit) return;
    inputEl._alunoSearchInit = true;

    let infoElement = infoEl;
    if (typeof infoEl === 'string') {
        infoElement = document.getElementById(infoEl);
    } else if (! infoElement) {
        const entry = inputEl.closest('.aluno-entry');
        if (entry) infoElement = entry.querySelector('.aluno-info');
    }

    const callback = buildAlunoInfoCallback(infoElement);
    autocomplete(inputEl, hiddenEl, AUTOCOMPLETE_ALUNOS_URL, callback);
};

// Toggle Tipo RFO (Falta Disciplinar / Elogio)
function toggleTipoRfo() {
    const tipoEl = document.querySelector('input[name="tipo_rfo"]:checked');
    if (!tipoEl) return;

    const advBlock = document.getElementById('advertencia-oral-block');
    const subtipoBlock = document.getElementById('subtipo-elogio-block');
    
    if (! advBlock || !subtipoBlock) return;

    if (tipoEl.value === 'Elogio') {
        advBlock.style.display = 'none';
        advBlock.querySelectorAll('input').forEach(i => i.removeAttribute('required'));
        
        subtipoBlock.style. display = 'block';
        const radios = subtipoBlock. querySelectorAll("input[name='subtipo_elogio']");
        if (radios. length && !Array.from(radios).some(r => r.checked)) {
            radios[0].checked = true;
        }
    } else {
        subtipoBlock.style.display = 'none';
        
        advBlock.style.display = 'block';
        const advRadios = advBlock.querySelectorAll("input[name='advertencia_oral']");
        if (advRadios.length && !Array.from(advRadios).some(r => r.checked)) {
            advRadios[0].checked = true;
        }
        advRadios.forEach(r => r.setAttribute('required', 'required'));
    }
}

// Fix encoding "Série"
function fixSerieEncoding() {
    document.querySelectorAll('.aluno-info, . info-display').forEach(el => {
        if (! el) return;
        try {
            let html = el.innerHTML;
            if (html && /Série/. test(html)) {
                html = html.replace(/Série/g, 'Série');
                el.innerHTML = html;
            }
        } catch (e) {}
    });
}

// Inicialização ao carregar página
document.addEventListener('DOMContentLoaded', function() {
    
    // Contador de caracteres
    const relatoTextarea = document.getElementById('relato_observador');
    if (relatoTextarea) {
        relatoTextarea.addEventListener('input', updateCharCounter);
        updateCharCounter();
    }

    // Inicializar autocomplete nos campos existentes
    document.querySelectorAll('.aluno-search').forEach(inp => {
        const parent = inp.closest('.aluno-entry');
        const hidden = parent ?  parent.querySelector('.aluno-id') : null;
        const info = parent ? parent.querySelector('.aluno-info') : null;
        window.initAlunoSearch(inp, hidden, info);
    });

    // Data padrão
    const hoje = new Date().toISOString().split('T')[0];
    const dataInput = document.getElementById('data_ocorrencia');
    if (dataInput && ! dataInput.value) {
        dataInput.value = hoje;
    }

    // Radio buttons com classe active
    document.querySelectorAll('. radio-buttons label').forEach(label => {
        label.addEventListener('click', function() {
            this.closest('.radio-buttons').querySelectorAll('label').forEach(l => {
                l.classList.remove('active');
            });
            this.classList.add('active');
        });
    });

    const selectedRadio = document.querySelector('. radio-buttons input[type="radio"]:checked');
    if (selectedRadio) {
        selectedRadio.closest('label').classList.add('active');
    }

    // Toggle tipo RFO
    document.querySelectorAll('input[name="tipo_rfo"]').forEach(radio => {
        radio.addEventListener('change', toggleTipoRfo);
    });
    setTimeout(toggleTipoRfo, 100);

    // Spinner ao submeter
    const formRFO = document.querySelector('. form-rfo');
    if (formRFO) {
        formRFO.addEventListener('submit', function() {
            const btn = this.querySelector('button[type="submit"]');
            if (btn) {
                setTimeout(() => {
                    btn. disabled = true;
                    btn. innerHTML = 'Registrando...  <i class="fas fa-spinner fa-spin"></i>';
                }, 50);
            }
        });
    }

    // Observar adições dinâmicas de alunos
    const container = document.getElementById('alunos-container');
    if (container && window.MutationObserver) {
        const observer = new MutationObserver(mutations => {
            mutations.forEach(m => {
                m.addedNodes.forEach(node => {
                    if (node.nodeType !== 1) return;
                    
                    const inputs = [];
                    if (node.matches && node.matches('.aluno-search')) inputs.push(node);
                    if (node.querySelectorAll) {
                        node.querySelectorAll('.aluno-search').forEach(i => inputs.push(i));
                    }

                    inputs.forEach(inp => {
                        const parent = inp.closest('.aluno-entry');
                        const hidden = parent ? parent.querySelector('.aluno-id') : null;
                        const info = parent ? parent. querySelector('.aluno-info') : null;
                        setTimeout(() => window.initAlunoSearch(inp, hidden, info), 50);
                    });
                });
            });
            fixSerieEncoding();
        });
        observer.observe(container, { childList: true, subtree: true });
    }

    // Fix encoding inicial
    fixSerieEncoding();
});