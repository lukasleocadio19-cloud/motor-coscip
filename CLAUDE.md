# Motor CAD/COSCIP

Antes de trabalhar, leia `C:\Users\USER\Downloads\proxima-sessao.md`: é o **único registro** do
projeto (estado, status por ID, histórico, pendências, cuidados). Atualize esse mesmo arquivo ao
final; não crie cópia nem outro registro. O plano completo (referência) está em `docs/plano/`.

- Python sempre pelo `.venv` do projeto (3.12). Rodar `pytest`, `ruff check .` e `npm run build` antes de concluir.
- Dados reais (corpus em `Downloads\coscip-corpus`) nunca entram no repositório.
- Nenhum resultado tem valor normativo até a homologação das regras (NT 2-01).
- A unidade do desenho sempre exige confirmação humana: `$INSUNITS` foi errado em 5 de 5 projetos reais.
