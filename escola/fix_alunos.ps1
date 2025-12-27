# fix_alunos.ps1
# Salve este arquivo na raiz do projeto e execute:
# PowerShell -ExecutionPolicy Bypass -File .\fix_alunos.ps1

$arquivo = 'blueprints\alunos.py'

if (-not (Test-Path $arquivo)) {
    Write-Host "ARQUIVO NÃO ENCONTRADO: $arquivo"
    exit 1
}

# 1) Criar backup
$ts = Get-Date -Format "yyyyMMddHHmmss"
$bak = "$arquivo.bak.$ts"
Copy-Item -Force $arquivo $bak
Write-Host "Backup criado:" $bak

# 2) Ler conteúdo
try {
    $texto = Get-Content -Raw -LiteralPath $arquivo -Encoding UTF8
} catch {
    Write-Host "Erro ao ler o arquivo:" $_.Exception.Message
    exit 1
}

# 3) Substituir sequência backslash+três-aspas -> aspas-triplas
$texto_corrigido = $texto -replace '\\\"\"\"', '"""'

if ($texto_corrigido -ne $texto) {
    try {
        Set-Content -LiteralPath $arquivo -Value $texto_corrigido -Encoding UTF8
        Write-Host "Substituição aplicada: \\\"\\\"\\\" -> \"\"\""
    } catch {
        Write-Host "Erro ao gravar arquivo:" $_.Exception.Message
        exit 1
    }
} else {
    Write-Host "Nenhuma ocorrência de \\\"\\\"\\\" encontrada. Nada alterado."
}

# 4) Exibir linhas 72..86 (contexto) para verificação
Write-Host "`n== Contexto (linhas 72..86) de $arquivo =="
$lines = Get-Content -LiteralPath $arquivo -Encoding UTF8
$start = 71
$end = 85
for ($i = $start; $i -le $end; $i++) {
    if ($i -lt $lines.Count) {
        "{0,4}: {1}" -f ($i+1), $lines[$i]
    }
}

Write-Host "`nPronto. Agora reinicie a aplicação com: py app.py"