<#
.SYNOPSIS
  Gera os zips das skills CBMERJ a partir do repositório (plano de correção, F1.1).

.DESCRIPTION
  O repositório é a fonte das skills (skills/ + normative/fontes). Os zips saem em
  dist\skills\<nome>.zip, prontos para enviar em claude.ai -> Configurações -> Skills.
  Precisa de Python 3.12: o .venv do repositório ou o python.exe do pacote portátil
  (-Python). Sem Python neste computador: baixe o artefato "skills-cbmerj" do workflow
  "Skills" no GitHub (Actions).

.EXAMPLE
  scripts\skills\empacotar.ps1
  scripts\skills\empacotar.ps1 -Python D:\MotorCoscip-0.2.0-win64\python\python.exe -Transicao
#>
param([string]$Python = "", [switch]$Transicao)
$ErrorActionPreference = "Stop"
$root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $root
if (-not $Python) { $Python = Join-Path $root ".venv\Scripts\python.exe" }
if (-not (Test-Path $Python)) {
    throw "Python não encontrado ($Python). Sem Python: baixe o artefato 'skills-cbmerj' do workflow Skills no GitHub."
}
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONPATH = "$root;$root\packages\normative"
$argsPack = @("-m", "tools.skills.pack")
if ($Transicao) { $argsPack += "--transicao" }
& $Python @argsPack
if ($LASTEXITCODE -ne 0) { throw "falha ao empacotar" }
