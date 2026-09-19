# Desenvolvimento: API na porta 8765 + Vite em http://localhost:5173 com proxy /v1.
$root = Resolve-Path "$PSScriptRoot\..\.."
$env:COSCIP_API_PORT = "8765"
Start-Process -NoNewWindow "$root\.venv\Scripts\python.exe" -ArgumentList @(
    "-m", "coscip_api.launcher", "--port", "8765", "--dev-origin", "http://localhost:5173"
)
Set-Location $root
npm run dev
