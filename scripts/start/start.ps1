# Inicia o motor em 127.0.0.1 (porta livre) e abre o navegador.
# Fechar a aba não encerra jobs; use scripts\stop\stop.ps1.
param([switch]$NoBrowser, [string]$DevOrigin)
$root = Resolve-Path "$PSScriptRoot\..\.."
$argsList = @()
if ($NoBrowser) { $argsList += "--no-browser" }
if ($DevOrigin) { $argsList += @("--dev-origin", $DevOrigin) }
& "$root\.venv\Scripts\python.exe" -m coscip_api.launcher @argsList
