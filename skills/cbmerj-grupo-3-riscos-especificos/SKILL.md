---
name: cbmerj-grupo-3-riscos-especificos
description: "Analisar riscos específicos pelas NTs do Grupo 3 do CBMERJ: cozinha profissional, GLP/GN em edificações, motogeradores, subestações elétricas, caldeiras e vasos de pressão, líquidos inflamáveis/combustíveis, helipontos/heliportos e orientação vigente para recarga de veículos elétricos. Usar diretamente ou quando $orquestrar-analise-cbmerj identificar um desses riscos."
---

# CBMERJ - Grupo 3

Executar somente os riscos específicos efetivamente presentes. Receber do Grupo 1 o enquadramento da edificação e do Grupo 2 as medidas gerais acionadas; não substituir a análise desses módulos.

## Iniciar

1. Ler [references/indice-grupo-3.md](references/indice-grupo-3.md).
2. Fixar a versão normativa e conferir o portal oficial se a consulta for posterior a 23/07/2026.
3. Inventariar cada fonte de risco por ambiente, equipamento, produto, capacidade, quantidade e forma de abastecimento.
4. Vincular cada entrada a planta, detalhe, memorial, laudo, ficha técnica ou responsabilidade técnica.
5. Tratar cada risco como subanálise independente antes de consolidar interfaces.
6. Para estação ou infraestrutura de recarga de veículo elétrico, abrir `$cbmerj-atos-administrativos`, aplicar a síntese operacional da Nota CHEMG/DGST vigente e registrar seu estado. Separar requisitos obrigatórios de recomendações; não tratar minuta ou futura NT 3-08 como norma vigente.

## Selecionar referências

- [NT 3-01](references/nt-3-01-cozinha-profissional.md): cozinha profissional, equipamentos, exaustão e proteção.
- [NT 3-02](references/nt-3-02-gas-glp-gn-uso-em-edificacoes.md): GLP/GN para uso em edificações e áreas de risco; conferir imagens.
- [NT 3-03](references/nt-3-03-motogeradores.md): motogeradores, combustível, ventilação e isolamento; conferir imagens.
- [NT 3-04](references/nt-3-04-subestacoes-eletricas.md): subestações elétricas.
- [NT 3-05](references/nt-3-05-caldeiras-e-vasos-de-pressao.md): caldeiras e vasos de pressão.
- [NT 3-06](references/nt-3-06-liquidos-inflamaveis-e-combustiveis.md): classificação, armazenamento, distâncias e proteção de líquidos; conferir imagens.
- [NT 3-07](references/nt-3-07-heliponto-e-heliporto.md): helipontos e heliportos; conferir imagens.

## Executar por risco

1. Confirmar o gatilho e a finalidade do sistema.
2. Identificar localização, quantidade/capacidade, arranjo, ventilação, afastamentos, contenção, fontes de ignição e acesso operacional.
3. Recalcular limites, distâncias e dimensionamentos exigidos pela NT; não aceitar apenas valores declarados.
4. Conferir a correspondência entre planta, cortes, detalhes, memorial, ficha técnica, laudo e ART/RRT/TRT.
5. Verificar interferências com rotas de fuga, compartimentação, sistemas hidráulicos, detecção, exaustão e acesso de viaturas.
6. Conferir imagens quando houver esquema, tabela complexa ou detalhe construtivo.
7. Acionar Grupo 4 se o uso for armazenamento/comercialização, posto, área especial ou estrutura abrangida por NT própria.
8. Acionar Grupo 5 se o risco estiver inserido em reunião de público ou evento.
9. Não permitir que a ocupação predominante oculte risco acessório: cozinha, GLP, gerador, subestação e estoque de líquidos devem ser inventariados por ambiente.
10. Quando a NT ou o ato remeter materialmente a ABNT, Inmetro, fabricante ou outra fonte externa, registrar referência e edição, obter a fonte autorizada e nunca reconstruir a regra por memória. Sem o conteúdo necessário, retornar `dependência_externa_não_disponível` e bloquear conformidade integral.

Pesquisas úteis:

```bash
rg -n -i "central|recipiente|capacidade|afastamento|ventilação" references/nt-3-02-gas-glp-gn-uso-em-edificacoes.md
rg -n -i "tanque|combustível|ventilação|exaustão|bacia" references/nt-3-03-motogeradores.md
rg -n -i "classe|capacidade|distância|contenção|espuma" references/nt-3-06-liquidos-inflamaveis-e-combustiveis.md
```

## Retornar ao orquestrador

Para cada risco:

| Campo | Conteúdo |
| --- | --- |
| Risco | Sistema, equipamento, produto ou atividade |
| Gatilho | Fato que tornou a NT aplicável |
| Entradas | Quantidade, capacidade, localização e evidências |
| Regra/cálculo | Limite, distância, proteção e resultado recalculado |
| Projeto | Implantação, detalhes, ventilação, contenção e acesso |
| Documentos | Memorial, laudo, ficha e responsabilidade técnica |
| Resultado | Conforme, não conforme, pendente ou não aplicável |
| Interface | Grupos 2, 4 ou 5 que alteram a conclusão |
| Fonte | NT, item/tabela e página |
| Saneamento | Correção ou documento necessário |

Não emitir conclusão global de aprovação. Quando faltar quantidade, capacidade, classe do produto, desenho ou documento determinante, retornar `pendente` e indicar a entrada ausente.
