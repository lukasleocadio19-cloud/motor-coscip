---
name: cbmerj-grupo-4-estruturas-especiais
description: "Analisar edificações e estruturas especiais pelas NTs do Grupo 4 do CBMERJ: quiosques, restrição de liberdade, bens tombados, explosivos, GLP/GN para manipulação/armazenamento/comércio, postos, garagens, pátios, túneis, canteiros e estruturas temporárias médicas. Usar diretamente ou quando $orquestrar-analise-cbmerj identificar uma dessas condições."
---

# CBMERJ - Grupo 4

Executar somente as NTs correspondentes às edificações, estruturas ou atividades especiais presentes. Aplicar o Grupo 4 em conjunto com a classificação do Grupo 1, as medidas do Grupo 2 e os riscos do Grupo 3.

## Iniciar

1. Ler [references/indice-grupo-4.md](references/indice-grupo-4.md).
2. Fixar a versão normativa e conferir o portal oficial se a consulta for posterior a 23/07/2026.
3. Delimitar fisicamente a estrutura especial, sua ocupação, áreas de apoio, acessos e interfaces com o restante do complexo.
4. Identificar capacidade, estoque, veículos, usuários, restrições operacionais e características construtivas.
5. Vincular cada entrada a planta, implantação, cortes, memorial, laudos e responsabilidade técnica.

## Selecionar referências

- [NT 4-01](references/nt-4-01-quiosques-e-areas-de-exposicao-ou-venda.md): quiosques e áreas de exposição/venda; conferir imagens.
- [NT 4-02](references/nt-4-02-restricao-de-liberdade.md): edificações destinadas à restrição de liberdade.
- [NT 4-03](references/nt-4-03-edificacoes-tombadas.md): edificações tombadas e soluções compatíveis com preservação.
- [NT 4-04](references/nt-4-04-municoes-explosivos-e-artefatos-pirotecnicos.md): fabricação, armazenagem e comércio de munições, explosivos e artefatos pirotécnicos; conferir imagens.
- [NT 4-05](references/nt-4-05-gas-manipulacao-armazenamento-e-comercializacao.md): manipulação, armazenamento e comercialização de GLP/GN; conferir imagens.
- [NT 4-06](references/nt-4-06-postos-de-servicos-e-abastecimento.md): postos de serviços e abastecimento; conferir imagens.
- [NT 4-07](references/nt-4-07-garagens.md): edificações e estruturas para garagens; conferir imagens.
- [NT 4-08](references/nt-4-08-patios-para-armazenagens.md): pátios para armazenagens diversas; conferir imagens.
- [NT 4-09](references/nt-4-09-tuneis.md): túneis; conferir imagens.
- [NT 4-10](references/nt-4-10-canteiro-de-obras.md): canteiros de obras.
- [NT 4-11](references/nt-4-11-estruturas-temporarias-atendimento-medico-covid-19.md): estruturas temporárias médicas para enfrentamento da Covid-19.

A NT 4-11 só entra quando o objeto real coincide com sua finalidade específica. Não presumir revogação por contexto histórico nem ampliar sua incidência para qualquer instalação de saúde; se a vigência formal ou o cabimento forem determinantes, confirmar no catálogo oficial atual.

## Executar por estrutura

1. Confirmar o gatilho e a abrangência espacial da NT.
2. Identificar parâmetros próprios: capacidade/estoque, tipo de veículo ou produto, usuários, comprimento, ventilação, resistência ao fogo, afastamentos e acessos.
3. Recalcular limites, distâncias, população e medidas específicas.
4. Conferir implantação, setorização, circulação, saídas, acesso operacional, compartimentação e interferências.
5. Comparar planta, cortes, detalhes, memoriais, inventários, licenças correlatas, laudos e ART/RRT/TRT.
6. Conferir imagens quando houver esquema, tabela complexa ou detalhe construtivo.
7. Acionar Grupo 3 para equipamentos/produtos específicos e Grupo 5 para evento ou reunião de público.
8. Quando a NT remeter materialmente a ABNT, Inmetro, fabricante ou outra fonte externa, registrar referência e edição, obter a fonte autorizada e nunca reconstruir a regra por memória. Sem o conteúdo necessário, retornar `dependência_externa_não_disponível` e bloquear conformidade integral.

Pesquisas úteis:

```bash
rg -n -i "quantidade|capacidade|distância|afastamento|área de armazenamento" references/nt-4-05-gas-manipulacao-armazenamento-e-comercializacao.md
rg -n -i "ilha|tanque|descarga|abastecimento|canaleta" references/nt-4-06-postos-de-servicos-e-abastecimento.md
rg -n -i "ventilação|vaga|subsolo|saída|rampa" references/nt-4-07-garagens.md
rg -n -i "comprimento|ventilação|saída|hidrante|comunicação" references/nt-4-09-tuneis.md
```

## Retornar ao orquestrador

Para cada estrutura:

| Campo | Conteúdo |
| --- | --- |
| Estrutura | Edificação, área ou atividade especial |
| Gatilho | Fato que tornou a NT aplicável |
| Abrangência | Limites físicos e interfaces |
| Entradas | Capacidade, estoque, usuários, dimensões e evidências |
| Regra/cálculo | Limite, distância, medida e resultado recalculado |
| Projeto | Implantação, circulação, setorização e acesso operacional |
| Documentos | Memorial, inventário, licença, laudo e responsabilidade técnica |
| Resultado | Conforme, não conforme, pendente ou não aplicável |
| Interface | Grupos 2, 3 ou 5 que alteram a conclusão |
| Fonte | NT, item/tabela e página |
| Saneamento | Correção ou documento necessário |

Não emitir conclusão global de aprovação. Quando a abrangência, capacidade, estoque, geometria ou documentação estiver indeterminada, retornar `pendente`.
