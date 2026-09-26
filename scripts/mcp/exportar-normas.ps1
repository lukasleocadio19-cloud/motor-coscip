<#
.SYNOPSIS
  Copia os textos das NTs (grupos 1 a 5) e do Decreto 42/2018 das skills CBMERJ do Claude
  para uma pasta, para usar o MCP em outro computador (instalar.ps1 -Normas <pasta>).

.EXAMPLE
  scripts\mcp\exportar-normas.ps1 -Destino "E:\normas-cbmerj"
#>
param([Parameter(Mandatory = $true)][string]$Destino)
$ErrorActionPreference = "Stop"
$raiz = Get-ChildItem "$env:APPDATA\Claude\local-agent-mode-sessions\skills-plugin\*\*\skills" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $raiz) { throw "skills CBMERJ não encontradas neste computador" }
# Lista explícita: um curinga pegaria também o grupo 5 legado, que não deve ser usado.
$grupos = "cbmerj-grupo-1-generalidades", "cbmerj-grupo-2-medidas-seguranca",
          "cbmerj-grupo-3-riscos-especificos", "cbmerj-grupo-4-estruturas-especiais",
          "cbmerj-grupo-5-eventos"
New-Item -ItemType Directory -Force $Destino | Out-Null
$n = 0
foreach ($g in $grupos) {
    foreach ($f in Get-ChildItem (Join-Path $raiz.FullName "$g\references") -Filter "nt-*.md") {
        Copy-Item $f.FullName $Destino -Force; $n++
    }
}
$decreto = Join-Path $raiz.FullName "orquestrar-analise-cbmerj\references\decreto-42-2018-coscip-compilado.md"
if (Test-Path $decreto) { Copy-Item $decreto $Destino -Force; $n++ }
Write-Host "$n arquivos copiados para $Destino"
Write-Host "No outro computador: scripts\mcp\instalar.ps1 -Normas `"<pasta copiada>`" -RegistrarClaudeDesktop"
