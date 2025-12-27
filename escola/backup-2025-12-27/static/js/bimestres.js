// Pequena validação no cliente: garante que inicio <= fim para cada bimestre
document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('form');
  if (!form) return;

  form.addEventListener('submit', function (e) {
    for (let n = 1; n <= 4; n++) {
      const inicio = document.getElementById('inicio_' + n).value;
      const fim = document.getElementById('fim_' + n).value;
      if (inicio && fim) {
        if (new Date(inicio) > new Date(fim)) {
          e.preventDefault();
          alert(`${n}º Bimestre: a data de início não pode ser posterior à data de fim.`);
          return;
        }
      }
    }
  });
});