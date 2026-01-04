/* Pequeno script que, quando incluído numa página de edição/criação de aluno,
   envia o campo data_matricula para a rota POST /alunos/<id>/matricula
   após o submit do formulário. Não impede o comportamento normal do form. */
document.addEventListener("DOMContentLoaded", function () {
  const form = document.querySelector("form.form-aluno") || document.querySelector("form");
  if (!form) return;
  form.addEventListener("submit", function () {
    try {
      const alunoIdInput = form.querySelector("input[name='id']") || form.querySelector("input[name='aluno_id']");
      const alunoId = alunoIdInput ? alunoIdInput.value : null;
      const dataInput = form.querySelector("input[name='data_matricula']");
      const dataMat = dataInput ? dataInput.value : null;
      if (!alunoId || !dataMat) return; // nothing to do

      setTimeout(async () => {
        try {
          await fetch(`/alunos/${alunoId}/matricula`, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ data_matricula: dataMat })
          });
        } catch (e) {
          console.warn("Falha ao salvar data_matricula (background)", e);
        }
      }, 400);
    } catch (e) {
      console.warn("matricula background error", e);
    }
  }, { passive: true });
});
