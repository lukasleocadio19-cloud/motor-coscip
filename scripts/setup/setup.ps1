# Prepara o ambiente local: Python 3.12 isolado, dependências e build da interface.
# Node.js só é necessário para construir a interface, não para rodar o produto.
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\..\.."
Set-Location $root

$py = (Get-Command py -ErrorAction SilentlyContinue)
if ($py) { py -3.12 -m venv .venv } else { python -m venv .venv }
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"

if (Get-Command npm -ErrorAction SilentlyContinue) {
    npm install --no-audit --no-fund
    npm run build
} else {
    Write-Warning "npm não encontrado: a interface não foi compilada (apps/api/coscip_api/static)."
}

.\.venv\Scripts\python -c "import sqlite3; print('SQLite embarcado:', sqlite3.sqlite_version)"
Write-Host "Pronto. Inicie com scripts\start\start.ps1"
