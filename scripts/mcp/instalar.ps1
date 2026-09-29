<#
.SYNOPSIS
  Instala o MCP "coscip-plantas" (Motor COSCIP) neste computador.

.DESCRIPTION
  Com -Portatil <pasta>: usa o python.exe do pacote portátil (sem .venv, sem pip) e pula 1-2.
  1. Encontra o Python 3.12 (py -3.12 ou -Python).
  2. Cria/atualiza o ambiente .venv do repositório e instala o motor.
  3. Roda o autoteste (python -m coscip_mcp --verificar).
  4. Opcional: registra o servidor no Claude Desktop e/ou no Claude Code.

.EXAMPLE
  scripts\mcp\instalar.ps1
  scripts\mcp\instalar.ps1 -RegistrarClaudeDesktop -Normas "D:\normas-cbmerj"
  scripts\mcp\instalar.ps1 -Portatil D:\MotorCoscip-0.2.0-win64 -RegistrarClaudeDesktop
  scripts\mcp\instalar.ps1 -RegistrarClaudeCode -Oda "C:\Program Files\ODA\ODAFileConverter 25.12.0\ODAFileConverter.exe"
#>
param(
    [string]$Python = "",
    [string]$Portatil = "",        # pasta descompactada do MotorCoscip-<versão>-win64.zip
    [string]$Normas = "",          # só se quiser outra pasta: o repositório já traz normative\fontes
    [string]$Oda = "",             # ODAFileConverter.exe, se não estiver no local padrão
    [switch]$RegistrarClaudeDesktop,
    [switch]$RegistrarClaudeCode,
    [string]$ConfigDesktop = "$env:APPDATA\Claude\claude_desktop_config.json"
)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $root

function Passo($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

if ($Portatil) {
    # Pacote portátil (F0.3): Python e dependências já vêm dentro da pasta.
    $venvPy = Join-Path (Resolve-Path $Portatil).Path "python\python.exe"
    if (-not (Test-Path $venvPy)) { throw "python.exe não encontrado em $Portatil\python" }
    Passo "Pacote portátil: $venvPy"
} else {
# --- 1. Python 3.12 ---------------------------------------------------------------------
Passo "Python 3.12"
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    $criar = $null
    if ($Python) {
        $criar = @($Python)
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $criar = @("py", "-3.12") }
    }
    if (-not $criar) {
        Write-Host "Python 3.12 não encontrado. Instale com:" -ForegroundColor Yellow
        Write-Host "  winget install --id Python.Python.3.12 -e --scope user"
        Write-Host "e rode este script de novo (ou informe -Python <caminho do python.exe 3.12>)."
        exit 1
    }
    $exe = $criar[0]
    $args0 = @()
    if ($criar.Count -gt 1) { $args0 = $criar[1..($criar.Count - 1)] }
    & $exe @args0 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "falha ao criar .venv" }
}
$versao = & $venvPy -c "import sys; print('%d.%d' % sys.version_info[:2])"
if ($versao -ne "3.12") {
    throw "o .venv usa Python $versao; o motor exige 3.12. Apague a pasta .venv e rode de novo."
}
Write-Host "ok: $venvPy (Python $versao)"

# --- 2. Motor e dependências ------------------------------------------------------------
Passo "Instalando o motor e as dependências (pode levar alguns minutos na primeira vez)"
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -e . --quiet
if ($LASTEXITCODE -ne 0) { throw "falha no pip install" }
Write-Host "ok"
}

# --- 3. Autoteste -----------------------------------------------------------------------
Passo "Autoteste"
$env:PYTHONIOENCODING = "utf-8"
if ($Normas) { $env:COSCIP_NORMAS_DIR = $Normas }
if ($Oda) { $env:COSCIP_ODA_PATH = $Oda }
& $venvPy -m coscip_mcp --verificar
if ($LASTEXITCODE -ne 0) { throw "autoteste falhou" }

# --- 4. Registro no Claude (opcional) ---------------------------------------------------
$ambiente = @{}
if ($Normas) { $ambiente["COSCIP_NORMAS_DIR"] = $Normas }
if ($Oda) { $ambiente["COSCIP_ODA_PATH"] = $Oda }

if ($RegistrarClaudeDesktop) {
    Passo "Registrando no Claude Desktop: $ConfigDesktop"
    # Mescla em Python: preserva as preferências do aplicativo, faz cópia .bak e grava sem BOM.
    $argsReg = @("-m", "coscip_mcp.registro", "--config", $ConfigDesktop, "--python", $venvPy)
    foreach ($k in $ambiente.Keys) { $argsReg += @("--env", "$k=$($ambiente[$k])") }
    & $venvPy @argsReg
    if ($LASTEXITCODE -ne 0) { throw "falha ao registrar no Claude Desktop" }
    Write-Host "ok: feche e abra o Claude Desktop para carregar o servidor 'coscip-plantas'"
}

if ($RegistrarClaudeCode) {
    Passo "Registrando no Claude Code (escopo do usuário)"
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Write-Host "comando 'claude' não encontrado; dentro do repositório o .mcp.json já registra o servidor." -ForegroundColor Yellow
    } else {
        $extras = @()
        foreach ($k in $ambiente.Keys) { $extras += @("-e", "$k=$($ambiente[$k])") }
        & claude mcp add --scope user @extras coscip-plantas -- $venvPy -m coscip_mcp
        Write-Host "ok"
    }
}

Passo "Pronto"
Write-Host "Servidor: $venvPy -m coscip_mcp"
Write-Host "No Claude Code, dentro desta pasta, o .mcp.json já o registra (aprovar ao abrir)."
