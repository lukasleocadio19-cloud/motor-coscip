# Motor CAD/COSCIP

Antes de trabalhar, leia `docs/proxima-sessao.md`: é o **único registro** do projeto (estado,
status por ID, histórico, pendências, cuidados). Atualize esse mesmo arquivo ao final; não crie
cópia nem outro registro. A arquitetura-alvo está em `docs/arquitetura-v2.md` e o plano completo
(referência) em `docs/plano/`.

- Python sempre pelo `.venv` do projeto (3.12). Rodar `pytest`, `ruff check .` e `npm run build` antes de concluir.
- Dados reais (corpus em `Downloads\coscip-corpus`) nunca entram no repositório.
- Nenhum resultado tem valor normativo até a homologação das regras e dos checks (NT 2-01).
- A unidade do desenho sempre exige confirmação humana: `$INSUNITS` foi errado em 5 de 5 projetos reais.
- Arquitetura v2: os três status (`compliance`, `evidence`, `review`) nunca se fundem, ausência
  de evidência nunca vira conformidade e citação que não confere impede o check.
