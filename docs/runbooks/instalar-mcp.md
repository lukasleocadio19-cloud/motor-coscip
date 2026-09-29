# Instalar o MCP "coscip-plantas" em outro computador (Windows)

O MCP dá ao Claude ferramentas para **ler plantas DXF/DWG** com precisão: imagem com grade em
metros, textos e símbolos com coordenadas, medidas, confirmação da unidade, pavimentos e a
análise do motor com citação das NTs. Tudo roda no computador; nada tem valor normativo.

## Pré-requisitos

| Item | Como obter | Obrigatório? |
|---|---|---|
| Windows 10/11 | — | sim |
| Git e acesso ao repositório privado `lukasleocadio19-cloud/motor-coscip` | `winget install Git.Git` e `winget install GitHub.cli`, depois `gh auth login` | sim |
| Python **3.12** | `winget install --id Python.Python.3.12 -e --scope user` | sim |
| Textos das NTs (.md) | já vêm no repositório (`normative/fontes`) | — |
| ODA File Converter | opendesign.com → ODA File Converter (aceitar a licença) | só para abrir `.dwg` |
| Claude Desktop ou Claude Code | claude.ai/download | para usar |

Node.js **não** é necessário para o MCP (só para compilar a interface do app).

## Passo a passo

```powershell
gh repo clone lukasleocadio19-cloud/motor-coscip
cd motor-coscip
powershell -ExecutionPolicy Bypass -File scripts\mcp\instalar.ps1 -RegistrarClaudeDesktop
```

O instalador:

1. acha o Python 3.12 e cria `.venv` na pasta do repositório;
2. instala o motor e as dependências (`pip install -e .`);
3. roda o autoteste (`python -m coscip_mcp --verificar`);
4. com `-RegistrarClaudeDesktop`, acrescenta `coscip-plantas` em
   `%APPDATA%\Claude\claude_desktop_config.json` **preservando** o que já existe e guardando
   uma cópia `.bak`; com `-RegistrarClaudeCode`, registra no Claude Code (escopo do usuário).

Depois, **reinicie o Claude Desktop**. No Claude Code, abrindo a pasta do repositório, o
`.mcp.json` já registra o servidor (aprovar quando o Claude Code perguntar).

## Textos das NTs

Os 52 textos das NTs (grupos 1–5, nunca o grupo 5 legado) e o Decreto 42/2018 compilado vêm
no repositório, em `normative/fontes`; o MCP os encontra sozinho. Para usar outra pasta:
`instalar.ps1 -Normas "<pasta>"`. **O repositório é a fonte única** (plano de correção, F1): as
skills CBMERJ são geradas daqui (`tools/skills/pack.py`), nunca o contrário. Correção de texto
se faz em `normative/fontes` (ver o README da pasta).

## DWG

Com o ODA File Converter instalado no local padrão (`C:\Program Files\ODA\…`), `abrir_planta`
aceita `.dwg`: converte uma **cópia** para DXF e registra os hashes (ADR 0006). Em outro local:
`instalar.ps1 -Oda "<caminho>\ODAFileConverter.exe"`. **Licença:** o conversor gratuito é para
uso não comercial de não membros da ODA.

## Conferir e usar

```powershell
.venv\Scripts\python -m coscip_mcp --verificar
```

No Claude: *"abra a planta C:\...\projeto.dxf e me mostre"*. O fluxo que a ferramenta ensina ao
Claude: abrir → ver → confirmar a unidade **com uma medida que você informar** → definir
pavimentos → analisar com o enquadramento do processo.

## Atualizar e remover

- Atualizar: `git pull` e rodar `scripts\mcp\instalar.ps1` de novo.
- Remover: apagar a entrada `coscip-plantas` do `claude_desktop_config.json` (ou
  `claude mcp remove coscip-plantas`) e a pasta do repositório. DXF convertidos de DWG ficam em
  `%TEMP%\coscip-mcp` (pode apagar).

## Sigilo

O arquivo da planta não sai do computador, mas o que as ferramentas devolvem (textos, medidas,
imagens) vai para o modelo do Claude. Confirme se o sigilo do processo permite.
