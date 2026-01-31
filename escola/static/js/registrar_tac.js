document.addEventListener('DOMContentLoaded', function(){
  const partesContainer = document.getElementById('participantes_container');
  const btnAddParticipante = document.getElementById('btn-add-participante');
  if (btnAddParticipante && partesContainer) {
    btnAddParticipante.addEventListener('click', function(e){
      e.preventDefault();
      e.stopPropagation();
      // Adiciona apenas UMA nova linha de participante
      const row = document.createElement('div');
      row.className = 'row mb-2 participante-row';
      row.innerHTML = '<div class="col-md-6"><input type="text" name="participante_nome[]" class="form-control" value=""></div>' +
        '<div class="col-md-5"><input type="text" name="participante_cargo[]" class="form-control" value=""></div>' +
        '<div class="col-md-1"><button type="button" class="btn btn-outline-danger btn-remove-participante">X</button></div>';
      partesContainer.appendChild(row);
    });

    partesContainer.addEventListener('click', function(e){
      if (e.target && e.target.classList.contains('btn-remove-participante')){
        e.target.closest('.participante-row').remove();
      }
    });
  }
});