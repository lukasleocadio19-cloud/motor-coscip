# ADR 0007 — Pacote portátil do Windows (Python embeddable)

**Status:** aceita · 29/09/2026 · plano de correção F0.3

**Contexto.** A máquina principal do usuário não tem Python nem Node e não consegue
instalá-los; tem só Git. O motor precisa rodar "em qualquer computador".

**Decisão.** A cada tag `v*`, o workflow `release.yml` (em `windows-latest`) monta
`MotorCoscip-<versão>-win64.zip` com `tools/package/portatil.py` e anexa à Release do GitHub
junto com `SHA256SUMS`:

- `python/`: **Python embeddable 3.12 (amd64) oficial** do python.org. A versão e o SHA-256
  ficam fixados em `scripts/package/python-embed.json`; arquivo com hash diferente é recusado.
  Enquanto o hash não estiver fixado, o workflow confere a assinatura **Sigstore** do python.org
  (identidade do gerente da versão 3.12), mostra o hash e para, para que seja fixado depois de
  conferido — nunca empacota um Python não conferido.
- `python312._pth` habilita `Lib\site-packages`, as pastas do código em `app\` (a mesma lista
  do `pyproject.toml`) e `import site`.
- Dependências: `pip install --require-hashes --only-binary=:all: --target` a partir de
  `requirements/runtime.lock` (lock universal com hash, gerado por `uv pip compile`).
- `app/`: código, `normative/` (textos das NTs, pacote e catálogo), interface já compilada,
  `scripts/mcp` e os runbooks.
- `iniciar.cmd`, `mcp.cmd`, `verificar.cmd`: tudo roda da pasta descompactada, sem admin.
- O workflow testa (pytest), monta, descompacta numa pasta temporária fora do repositório e roda
  o autoteste com o Python do pacote antes de publicar.
- `scripts\mcp\instalar.ps1 -Portatil <pasta>` registra o MCP apontando para o `python.exe` do
  pacote.

**Alternativas.** Instalador MSI/PyInstaller (mais peças, antivírus reclama de executável
empacotado); pacote NuGet `python` (layout não embeddable, hash igualmente a fixar).

**Consequências.**
- O pacote é só Windows 64 bits. Linux/macOS usam o `.venv` normal.
- Dependência nova só entra no pacote depois de regenerar os locks (`tools/ci/check_lock.py`
  falha na CI se o lock estiver desatualizado).
- O teste na máquina principal (descompactar e rodar `verificar.cmd`) é manual, do usuário.
- Atualização lado a lado (SAFE-03) continua pendente: cada versão é uma pasta nova; os dados
  ficam em `%LOCALAPPDATA%\MotorCoscip`, fora do pacote.
