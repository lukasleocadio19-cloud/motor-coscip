# Arquitetura local

```
Navegador no PC (127.0.0.1)
        │  mesma origem: interface estática + /v1
        ▼
FastAPI ─ sessão local ─ Host/Origin/CSRF
        │
        ├── SQLite (WAL) ── metadados, fila persistente, auditoria, consumo
        ├── Pasta de dados ── originais imutáveis, derivados, manifestos SHA-256
        └── Supervisor ── reclama job (lease + token) ──► worker em processo separado
                                                          (manifesto + pasta do job)
DXF → inventário/entidades → modelo confirmado → regras → evidências → relatório
                                                    + IA opcional com teto de gasto
```

## Fronteiras

| Componente | Pode | Não pode |
|---|---|---|
| Navegador | chamar `/v1` com sessão e CSRF | receber caminhos de disco ou chaves de API |
| API | ler/escrever banco e storage | aceitar caminho arbitrário enviado pela página |
| Supervisor | publicar resultados validados | publicar com token de tentativa vencido |
| Worker | ler a entrada copiada e escrever em `out/` | acessar banco, chaves ou perfil do usuário |
| IA | receber trechos autorizados | escrever, navegar, acessar arquivos |

Separação de processo **não** é sandbox. Antes de receber arquivos externos recorrentes,
homologar identidade restrita/VM (SAFE-05).

## Fluxo de importação (implementado)

1. `POST /revisions/{id}/uploads` → sessão; `PUT …/parts/{n}` em streaming com SHA-256 por parte.
2. `POST /uploads/{id}/complete` → concatena em arquivo temporário, `fsync`, renomeia para chave imutável.
3. `POST /revisions/{id}/seal` → manifesto congelado com hash.
4. `POST /revisions/{id}/imports` → `Execution` + intenção de job **na mesma transação**.
5. Supervisor reclama o job, copia a entrada para `jobs/staging/<job>/<tentativa>/in`, inicia o worker.
6. Worker grava `inventory.json`, `entities.jsonl` e `result.json` em `out/`.
7. Supervisor valida esquema, hash de entrada e token; publica o inventário e o `Drawing`.
8. Sem unidade declarada → `WAITING_INPUT` (o worker não fica reservado esperando).

Na inicialização, jobs com lease vencido voltam à fila com `WORKER_INTERRUPTED`; temporários
órfãos são removidos. Interrupção nunca é marcada como sucesso.

## Abstrações para migração futura

`LocalFileStorage`, `JobQueue`, `DxfReader`, repositórios SQLAlchemy e provedores de IA.
Só os adaptadores locais existem; AWS, ODA e PostGIS não são implementados antecipadamente.
