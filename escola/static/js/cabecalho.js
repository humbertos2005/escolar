// (arquivo opcional) preview simples de imagem ao selecionar (criar em static/js/cabecalho.js e referenciar se quiser)
document.addEventListener('DOMContentLoaded', function(){
    function preview(fileInput, targetSelector){
        const input = document.querySelector(fileInput);
        const target = document.querySelector(targetSelector);
        if (!input || !target) return;
        input.addEventListener('change', function(){
            const f = input.files[0];
            if (!f) return;
            const reader = new FileReader();
            reader.onload = function(e){
                target.innerHTML = '<img src="'+e.target.result+'" style="max-width:220px;">';
            };
            reader.readAsDataURL(f);
        });
    }
    preview('input[name="logo_estado"]', '#preview-logo-estado');
    preview('input[name="logo_escola"]', '#preview-logo-escola');
});