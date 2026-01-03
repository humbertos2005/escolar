<#
  Inserir/remover com segurança o bloco <style id='rfo-console-style'>...</style> em um template HTML.
  Cria backup antes de alterar o arquivo.
  Modos:
    - DryRun : simula alteração sem gravar
    - Remove : remove o bloco se existir

  Uso:
    .\scripts\add-rfo-style.ps1 -TemplatePath "escola/templates/base.html" -DryRun
    .\scripts\add-rfo-style.ps1 -TemplatePath "escola/templates/base.html"
    .\scripts\add-rfo-style.ps1 -TemplatePath "escola/templates/base.html" -Remove
#>

param(
  [string]$TemplatePath = 'escola/templates/base.html',
  [string]$MarkerId = 'rfo-console-style',
  [string]$BackupDir = 'backups',
  [switch]$DryRun,
  [switch]$Remove
)

# Resolve arquivo
try {
  $resolved = Resolve-Path -Path $TemplatePath -ErrorAction Stop
} catch {
  Write-Error "Arquivo nao encontrado: $TemplatePath"
  exit 2
}
$fullPath = $resolved.Path

# prepara backup
$timestamp = (Get-Date).ToString('yyyyMMddHHmmss')
$backupFolder = Join-Path -Path (Get-Location) -ChildPath $BackupDir
if (-not (Test-Path $backupFolder)) {
  try { New-Item -ItemType Directory -Path $backupFolder -Force | Out-Null } catch { Write-Error "Nao foi possivel criar pasta de backup: $backupFolder"; exit 3 }
}
$backupFile = Join-Path $backupFolder ("{0}.{1}.bak" -f (Split-Path $fullPath -Leaf), $timestamp)

Write-Host "Criando backup em: $backupFile"
try {
  Copy-Item -Path $fullPath -Destination $backupFile -Force -ErrorAction Stop
} catch {
  Write-Error "Falha ao criar backup: $_"
  exit 4
}

# le arquivo como UTF8
try {
  $content = Get-Content -Raw -Encoding UTF8 -Path $fullPath
} catch {
  Write-Error "Falha ao ler arquivo: $_"
  exit 5
}

# -----------------------
# Funcoes utilitarias
# -----------------------
function Get-StringIndexIgnoreCase {
  param(
    [string]$Source,
    [string]$Value
  )
  if ($null -eq $Source -or $null -eq $Value) { return -1 }
  return $Source.ToLower().IndexOf($Value.ToLower())
}

function Remove-StyleBlockIfPresent {
  param([string]$text, [string]$marker)
  $lower = $text.ToLower()
  $dq = [char]34  # "
  $sq = [char]39  # '
  $markerLower = $marker.ToLower()

  $markerDouble = ("id=" + $dq + $markerLower + $dq).ToLower()
  $markerSingle = ("id=" + $sq + $markerLower + $sq).ToLower()

  $pos = $lower.IndexOf($markerDouble)
  if ($pos -lt 0) { $pos = $lower.IndexOf($markerSingle) }
  if ($pos -lt 0) { return @{ found = $false; newText = $text } }

  # encontrar abertura da tag <style anterior ao marcador
  $startTagPos = $lower.LastIndexOf("<style", $pos)
  if ($startTagPos -lt 0) {
    # não achamos abertura - aborta remoção
    return @{ found = $false; newText = $text }
  }

  # encontrar fechamento </style> após o marcador
  $endTagPos = $lower.IndexOf("</style>", $pos)
  if ($endTagPos -lt 0) {
    # sem fechamento - aborta
    return @{ found = $false; newText = $text }
  }

  $endTagPos = $endTagPos + 8  # comprimento de </style>
  $before = $text.Substring(0, $startTagPos)
  $after = $text.Substring($endTagPos)
  $new = $before + "`n" + $after
  return @{ found = $true; newText = $new }
}

# -----------------------
# Remocao (opcao Remove)
# -----------------------
if ($Remove) {
  $res = Remove-StyleBlockIfPresent -text $content -marker $MarkerId
  if (-not $res.found) {
    Write-Host "Bloco com id='$MarkerId' nao encontrado - nada a remover."
    exit 0
  }

  if ($DryRun) {
    Write-Host "DRYRUN: bloco seria removido. Preview (inicial):"
    $preview = if ($res.newText.Length -gt 1000) { $res.newText.Substring(0,1000) + '...(truncated)' } else { $res.newText }
    Write-Output $preview
    exit 0
  }

  try {
    $tmp = "$fullPath.tmp.$timestamp"
    Set-Content -Path $tmp -Value $res.newText -Encoding utf8
    Move-Item -Path $tmp -Destination $fullPath -Force
    Write-Host "Remocao concluida. Backup: $backupFile"
    exit 0
  } catch {
    Write-Error "Erro ao gravar arquivo modificado: $_"
    exit 6
  }
}

# -----------------------
# Insercao (padrao)
# -----------------------
# verifica se ja existe (por id entre aspas simples ou duplas)
$exists = $false
$lowerContent = $content.ToLower()
if ($lowerContent.Contains(("id=" + [char]34 + $MarkerId.ToLower() + [char]34))) { $exists = $true }
if ($lowerContent.Contains(("id=" + [char]39 + $MarkerId.ToLower() + [char]39))) { $exists = $true }
if ($exists) {
  Write-Warning "Arquivo ja contem um bloco com id='$MarkerId'. Abortando para evitar duplicacao."
  exit 0
}

$styleBlock = @'
<style id="rfo-console-style">
.rfo-console-btn{display:inline-flex!important;align-items:center;gap:.5rem;padding:.45rem .9rem;border-radius:.45rem;font-weight:600;font-size:.95rem;text-decoration:none!important;transition:transform .12s ease,box-shadow .12s ease,opacity .12s ease;cursor:pointer;border:1px solid transparent;box-shadow:0 2px 6px rgba(11,22,40,0.06);}
.rfo-console-btn:focus{outline:3px solid rgba(24,144,255,0.15);outline-offset:2px;}
.rfo-console-btn--primary{background:linear-gradient(180deg,#2b8de6,#1673d3);color:#fff!important;}
.rfo-console-btn--secondary{background:transparent;color:#1673d3!important;border-color:rgba(22,115,211,0.12);box-shadow:none;}
.rfo-console-btn:hover{transform:translateY(-1px);}
.rfo-console-icon{width:1rem;height:1rem;display:inline-block;flex:0 0 auto;}
.rfo-console-label{display:inline-block;vertical-align:middle;}
@media (max-width:420px){.rfo-console-label{display:none;}}
</style>
'@

# localizar lugar de insercao: antes de </head>, senao antes de </body>, senao final do arquivo
$headIdx = Get-StringIndexIgnoreCase -Source $content -Value "</head>"
$bodyIdx = Get-StringIndexIgnoreCase -Source $content -Value "</body>"
if ($headIdx -ge 0) {
  Write-Host 'Inserindo bloco antes de </head>.'
  $newContent = $content.Substring(0,$headIdx) + "`n" + $styleBlock + "`n" + $content.Substring($headIdx)
} elseif ($bodyIdx -ge 0) {
  Write-Host 'Tag </head> nao encontrada - inserindo antes de </body>.'
  $newContent = $content.Substring(0,$bodyIdx) + "`n" + $styleBlock + "`n" + $content.Substring($bodyIdx)
} else {
  Write-Host 'Tags </head> e </body> nao encontradas - anexando bloco ao final do arquivo.'
  $newContent = $content + "`n" + $styleBlock + "`n"
}

if ($DryRun) {
  Write-Host "DRYRUN: nao sera gravado. Preview inicial:"
  $preview = if ($newContent.Length -gt 1200) { $newContent.Substring(0,1200) + '...(truncated)' } else { $newContent }
  Write-Output $preview
  Write-Host "DRYRUN finalizado. Backup criado: $backupFile"
  exit 0
}

# gravar de forma segura
try {
  $tmpFile = "$fullPath.tmp.$timestamp"
  Set-Content -Path $tmpFile -Value $newContent -Encoding utf8
  Move-Item -Path $tmpFile -Destination $fullPath -Force
  Write-Host "Insercao concluida. Backup: $backupFile"
  exit 0
} catch {
  Write-Error "Erro ao gravar arquivo modificado: $_"
  if (Test-Path $tmpFile) { Remove-Item $tmpFile -ErrorAction SilentlyContinue }
  exit 7
}