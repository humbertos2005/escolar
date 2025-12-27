// Contador de caracteres
const relatoTextarea = document.getElementById('relato_observador');
const charCounter = document.querySelector('.char-counter');

function updateCharCounter() {
    if (!relatoTextarea || !charCounter) return;
    const length = relatoTextarea.value.length;
    charCounter.textContent = `${length}/500 caracteres`;
    charCounter.style.color = length > 450 ? '#e74c3c' : '#7f8c8d';
}

// Função genérica de Autocomplete
function autocomplete(inp, hidden_inp, info_display_id, fetch_url, callback) {
    // prevent double-binding for the same input element
    if (!inp || inp._autocompleteBound) return;
    inp._autocompleteBound = true;

    let currentFocus;

    inp.addEventListener('input', function() {
        const val = this.value;
        closeAllLists();
        if (!val || val.length < 3) {
            if (callback) callback(null, null);
            return false;
        }
        currentFocus = -1;
        const a = document.createElement('DIV');
        a.setAttribute('id', this.id + 'autocomplete-list');
        a.setAttribute('class', 'autocomplete-items');
        this.parentNode.appendChild(a);

        fetch(fetch_url + '?q=' + encodeURIComponent(val))
            .then(response => response.json())
            .then(function(arr) {
                if (!arr || arr.length === 0) {
                    const b = document.createElement('DIV');
                    b.innerHTML = 'Nenhum resultado encontrado.';
                    b.style.color = '#7f8c8d';
                    a.appendChild(b);
                    return;
                }
                arr.forEach(function(item) {
                    const b = document.createElement('DIV');
                    b.innerHTML = item.value;
                    b.dataset.id = item.id;
                    b.dataset.data = JSON.stringify(item.data);
                    b.addEventListener('click', function(e) {
                        inp.value = item.value;
                        if (hidden_inp) hidden_inp.value = item.id;
                        if (callback) {
                            callback(item.id, item.data);
                        }
                        closeAllLists();
                    });
                    a.appendChild(b);
                });
            })
            .catch(error => console.error('Erro ao buscar dados:', error));
    });

    inp.addEventListener('keydown', function(e) {
        let x = document.getElementById(this.id + 'autocomplete-list');
        if (x) x = x.getElementsByTagName('div');
        if (e.keyCode === 40) { // Seta para baixo
            currentFocus++;
            addActive(x);
        } else if (e.keyCode === 38) { // Seta para cima
            currentFocus--;
            addActive(x);
        } else if (e.keyCode === 13) { // Enter
            e.preventDefault();
            if (currentFocus > -1 && x && x[currentFocus]) {
                x[currentFocus].click();
            }
        }
    });

    function addActive(x) {
        if (!x) return false;
        removeActive(x);
        if (currentFocus >= x.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = (x.length - 1);
        x[currentFocus].classList.add('autocomplete-active');
        x[currentFocus].scrollIntoView({ block: 'nearest' });
    }

    function removeActive(x) {
        for (let i = 0; i < x.length; i++) {
            x[i].classList.remove('autocomplete-active');
        }
    }

    function closeAllLists(elmnt) {
        const x = document.getElementsByClassName('autocomplete-items');
        for (let i = 0; i < x.length; i++) {
            if (elmnt !== x[i] && elmnt !== inp) {
                if (x[i] && x[i].parentNode) x[i].parentNode.removeChild(x[i]);
            }
        }
    }
    document.addEventListener('click', function (e) {
        closeAllLists(e.target);
    });
}

// Callback genérico para exibir info em um elemento específico
function buildAlunoInfoCallback(infoElement) {
    return function(alunoId, itemData) {
        if (!infoElement) return;
        if (alunoId && itemData && itemData.serie) {
            infoElement.innerHTML = `<strong>Série/Turma:</strong> ${itemData.serie} - ${itemData.turma}`;
            infoElement.classList.add('show');
        } else {
            infoElement.innerHTML = '';
            infoElement.classList.remove('show');
        }
    };
}

// Compatibilidade: função ainda disponível para quem a chamava antes (mantida)
function exibirInfoAluno(alunoId, itemData) {
    const displayP = document.getElementById('aluno-info');
    if (!displayP) return;
    if (alunoId && itemData && itemData.serie) {
        displayP.innerHTML = `<strong>Série/Turma:</strong> ${itemData.serie} - ${itemData.turma}`;
        displayP.classList.add('show');
    } else {
        displayP.innerHTML = '';
        displayP.classList.remove('show');
    }
}

// Expor inicializador global para uso em elementos dinâmicos
window.initAlunoSearch = function(inputEl, hiddenEl, infoEl) {
    if (!inputEl) return;
    // idempotency: don't reinitialize same element
    if (inputEl._alunoSearchInit) {
        // but update bound hidden/info references if provided
        if (hiddenEl) inputEl._boundHidden = hiddenEl;
        if (infoEl) inputEl._boundInfo = (typeof infoEl === 'string') ? document.getElementById(infoEl) : infoEl;
        return;
    }

    // infoEl pode ser um elemento DOM ou um id string; normaliza para elemento
    let infoElement = null;
    if (typeof infoEl === 'string') {
        infoElement = document.getElementById(infoEl);
    } else if (infoEl instanceof HTMLElement) {
        infoElement = infoEl;
    } else {
        // tenta encontrar elemento .aluno-info associado ao input
        const entry = inputEl.closest('.aluno-entry');
        if (entry) infoElement = entry.querySelector('.aluno-info');
    }

    const callback = buildAlunoInfoCallback(infoElement);

    // keep references on input element for other code to use
    inputEl._boundHidden = hiddenEl || inputEl._boundHidden || null;
    inputEl._boundInfo = infoElement || inputEl._boundInfo || null;

    // mark initialized
    inputEl._alunoSearchInit = true;

    // attach autocomplete behavior
    autocomplete(inputEl, inputEl._boundHidden, null, AUTOCOMPLETE_ALUNOS_URL, callback);
};

// Aliases para compatibilidade com possíveis nomes usados pelo template
window.setupAlunoSearch = window.initAlunoSearch;
window.bindAlunoSearch = window.initAlunoSearch;

// Inicializações ao carregar o DOM
document.addEventListener('DOMContentLoaded', function() {
    // Inicializa contador de caracteres
    if (relatoTextarea && charCounter) {
        relatoTextarea.addEventListener('input', updateCharCounter);
        updateCharCounter();
    }

    // Inicializa Autocomplete para todos os inputs .aluno-search presentes
    try {
        document.querySelectorAll('.aluno-search').forEach(function(inp){
            const parent = inp.closest('.aluno-entry') || document.getElementById('alunos-container');
            const hidden = parent ? parent.querySelector('.aluno-id') : null;
            const info = parent ? parent.querySelector('.aluno-info') : null;
            window.initAlunoSearch(inp, hidden, info);
        });
    } catch(e){}

    // Define data atual como padrão, se o campo estiver vazio
    const hoje = new Date().toISOString().split('T')[0];
    const dataOcorrenciaInput = document.getElementById('data_ocorrencia');
    if (dataOcorrenciaInput && !dataOcorrenciaInput.value) {
        dataOcorrenciaInput.value = hoje;
    }

    // Lógica para os botões de rádio "Advertência Oral"
    document.querySelectorAll('.radio-buttons label').forEach(function(label) {
        label.addEventListener('click', function() {
            // Remove 'active' de todos os labels no mesmo grupo
            this.closest('.radio-buttons').querySelectorAll('label').forEach(function(otherLabel) {
                otherLabel.classList.remove('active');
            });
            // Adiciona 'active' ao label clicado
            this.classList.add('active');
            // Marca o input de rádio correspondente
            this.querySelector('input[type="radio"]').checked = true;
        });
    });
    // Garante que o botão de rádio selecionado no carregamento da página tenha a classe 'active'
    const selectedRadio = document.querySelector('.radio-buttons input[type="radio"]:checked');
    if (selectedRadio) {
        selectedRadio.closest('label').classList.add('active');
    }

    // Handler de submissão do formulário para UX (spinner e desabilitar botão)
    const formRFO = document.querySelector('.form-rfo');
    if (formRFO) {
        formRFO.addEventListener('submit', function(event) {
            const submitButton = formRFO.querySelector('button[type="submit"]');
            if (submitButton) {
                // Adiciona um pequeno delay para o spinner aparecer antes da navegação
                setTimeout(() => {
                    submitButton.disabled = true;
                    submitButton.innerHTML = 'Registrando... <i class="fas fa-spinner fa-spin"></i>';
                }, 50);
            }
        });
    }

    // Observe adições dinâmicas dentro do container de alunos e inicialize novos inputs
    try {
        const container = document.getElementById('alunos-container');
        if (container && window.MutationObserver) {
            const mo = new MutationObserver(function(mutations) {
                mutations.forEach(function(m) {
                    m.addedNodes.forEach(function(node) {
                        if (node.nodeType !== 1) return;
                        // se o nó adicionado for um wrapper que contém .aluno-search
                        const found = [];
                        if (node.matches && node.matches('.aluno-search')) found.push(node);
                        if (node.querySelectorAll) {
                            node.querySelectorAll('.aluno-search').forEach(function(i){ found.push(i); });
                        }
                        found.forEach(function(inp){
                            const parent = inp.closest('.aluno-entry') || container;
                            const hidden = parent ? parent.querySelector('.aluno-id') : null;
                            const info = parent ? parent.querySelector('.aluno-info') : null;
                            // small timeout to allow other scripts to attach if needed
                            setTimeout(function(){ window.initAlunoSearch(inp, hidden, info); }, 30);
                        });
                    });
                });
            });
            mo.observe(container, { childList: true, subtree: true });
        }
    } catch(e){}
});



