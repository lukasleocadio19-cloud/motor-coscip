# Encerramento controlado: jobs em andamento são retomados/isolados na próxima abertura.
$root = Resolve-Path "$PSScriptRoot\..\.."
& "$root\.venv\Scripts\python.exe" -m coscip_api.launcher --stop
