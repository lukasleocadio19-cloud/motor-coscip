# ADR 0006 — DWG lido pelo ODA File Converter (uso local)

**Status:** aceita · 25/09/2026 · complementa a ADR 0002

**Contexto.** A IA precisa ler plantas que chegam em DWG. O DWG é formato fechado; ler o
binário com código próprio levaria meses e ficaria incompleto. O usuário escolheu a ODA.

**Decisão.** O MCP local aceita `.dwg`: `coscip_cad.dwg.dwg_to_dxf` converte **uma cópia**
com o ODA File Converter instalado no computador (DXF 2018, com auditoria) e o motor segue
lendo o DXF. O conversor é localizado em `COSCIP_ODA_PATH` ou em
`C:\Program Files\ODA\ODAFileConverter*\`. O DXF derivado fica em cache pelo SHA-256 do DWG
(`COSCIP_MCP_CACHE`, padrão na pasta temporária), fora do repositório.

**Registro de origem (ADR 0002).** SHA-256 do DWG e do DXF, versão do DWG (cabeçalho AC10xx),
ferramenta, versão, tempo; o id da planta no MCP segue o DWG. Handles do DXF derivado não são
tratados como handles do DWG.

**Licença.** O ODA File Converter gratuito restringe não membros a **uso não comercial**. Esta
decisão vale para o uso local e para testes. O produto vendido exige assinatura da ODA (Drawings
SDK ou licença comercial do conversor) ou o serviço da Autodesk (Design Automation). A
instalação e o aceite da licença são feitos pelo usuário.

**Consequências.**
- O app (upload `ANALYTIC_DXF`) continua recusando DWG como na ADR 0002; só o MCP converte.
- Os testes simulam o conversor; a conversão real depende do ODA instalado e de um DWG real.
