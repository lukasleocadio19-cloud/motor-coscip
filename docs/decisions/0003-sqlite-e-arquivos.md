# ADR 0003 — SQLite + pasta local de dados

**Status:** aceita · 19/09/2026

**Decisão.** SQLite com FKs, WAL, `synchronous=FULL`, escrita serializada; geometria em WKB;
decimais normativos como texto. Arquivos em pasta privada não sincronizada, com nomes gerados
pela aplicação e SHA-256.

**Consequências.**
- Nunca guardar o banco ativo em rede, OneDrive ou Dropbox (o launcher avisa).
- Filesystem e SQLite não formam uma transação: temporário → `fsync` → rename → registro no banco;
  reconciliação na abertura.
- Backup pela API de backup do SQLite + cópia verificada dos artefatos referenciados.
- Migração para PostgreSQL/PostGIS exige implementação e testes, não só trocar a URL.
