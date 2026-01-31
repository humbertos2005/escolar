document.addEventListener('DOMContentLoaded', function() {
  const btn = document.getElementById('btn-add-participante');
  if (!btn) return;

  // Remove todos os eventos antigos: substitui o botão por um clone novo
  const clone = btn.cloneNode(true);
  btn.parentNode.replaceChild(clone, btn);

  // Adiciona apenas um evento limpo
  clone.addEventListener('click', function(e){
    e.preventDefault();
    const partesContainer = document.getElementById('participantes_container');
    const row = document.createElement('div');
    row.className = 'row mb-2 participante-row';
    row.innerHTML = '<div class="col-md-6"><input type="text" name="participante_nome[]" class="form-control" value=""></div>' +
      '<div class="col-md-5"><input type="text" name="participante_cargo[]" class="form-control" value=""></div>' +
      '<div class="col-md-1"><button type="button" class="btn btn-outline-danger btn-remove-participante">X</button></div>';
    partesContainer.appendChild(row);
  });

  document.getElementById('participantes_container').addEventListener('click', function(e){
    if (e.target && e.target.classList.contains('btn-remove-participante')){
      e.target.closest('.participante-row').remove();
    }
  });
});

document.addEventListener('DOMContentLoaded', function() {
  const btnObrig = document.getElementById('btn-add-obrigacao');
  if (!btnObrig) return;

  // Remove eventos antigos
  const cloneObrig = btnObrig.cloneNode(true);
  btnObrig.parentNode.replaceChild(cloneObrig, btnObrig);

  // Evento único
  cloneObrig.addEventListener('click', function(e){
    e.preventDefault();
    const container = document.getElementById('obrigacoes_container');
    const row = document.createElement('div');
    row.className = 'input-group mb-2 obrigacao-row';
    row.innerHTML = '<input type="text" name="obrigacao[]" class="form-control" value="">' +
      '<button type="button" class="btn btn-outline-danger btn-remove-obrigacao">Remover</button>';
    container.appendChild(row);
  });

  document.getElementById('obrigacoes_container').addEventListener('click', function(e){
    if (e.target && e.target.classList.contains('btn-remove-obrigacao')){
      e.target.closest('.obrigacao-row').remove();
    }
  });
});