# Empacotamento

**Pacote portátil do Windows** (ADR 0007, plano de correção F0.3): feito pelo workflow
`.github/workflows/release.yml` a cada tag `v*` (ou manualmente, "Run workflow", para um
pacote de teste sem Release). O script é `tools/package/portatil.py`.

- `python-embed.json`: versão, URL e SHA-256 do Python embeddable oficial. Hash vazio = o
  workflow confere a assinatura Sigstore, mostra o hash e para; fixe-o aqui e rode de novo.
- Dependências: `requirements/runtime.lock` (regenerar com o comando do cabeçalho do lock
  quando mudar o `pyproject.toml`; a CI acusa lock desatualizado).
- Uso: descompactar a pasta inteira, `verificar.cmd`, depois `iniciar.cmd` ou `mcp.cmd`.
  Registrar no Claude Desktop: `app\scripts\mcp\instalar.ps1 -Portatil <pasta> -RegistrarClaudeDesktop`.

Ainda pendente (plano §13):

- Chromium para PDF (REP-02);
- avisos de licença agregados (ezdxf MIT, Shapely BSD, GEOS LGPL, SQLite domínio público,
  Three.js MIT…);
- atualização lado a lado com rollback que não abre banco migrado incompatível (SAFE-03).
