# ADR 0001 — Execução local, um operador

**Status:** aceita · 19/09/2026

**Decisão.** Aplicação para um usuário no próprio computador Windows. Serviço Python único
em `127.0.0.1`, interface servida na mesma origem. Uma análise pesada por vez.

**Motivo.** R$ 0/mês de hospedagem e licença do núcleo; viabilidade antes de investir em nuvem.

**Consequências.**
- Disponibilidade depende do PC ligado e do app aberto; não há SLA.
- Acesso pela rede **não** é uma mudança de endereço: exige autenticação multiusuário,
  TLS e nova validação de segurança (FUT-06/FUT-07).
- `tenant_id` existe para a migração, mas não promete isolamento multiusuário.
