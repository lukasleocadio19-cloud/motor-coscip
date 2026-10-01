# Matriz de roteamento entre habilidades

Esta matriz traduz para ativação modular a lógica operacional consolidada no relatório técnico de 2026. Os gatilhos são cumulativos.

## Roteamento principal

| Condição observada | Módulo obrigatório | Saída necessária |
| --- | --- | --- |
| Qualquer processo documental técnico | Atos administrativos + analista de processo | Modalidade/competência + roteiro específico, inventário, matriz requisito-evidência, achados e recomendação |
| Qualquer processo técnico | Grupo 1 | Regime, classificação, procedimento e gatilhos |
| Medida exigida pelo Decreto/LE | Grupo 2 | Aplicabilidade, cálculo, representação e documentos |
| Equipamento, produto ou atividade da série 3 | Grupo 3 | Subanálise do risco e interfaces |
| Edificação/estrutura/atividade da série 4 | Grupo 4 | Requisitos próprios e interfaces |
| Reunião de público ou evento da série 5 | Grupo 5 | População, saídas, estruturas, medidas e documentos |

## Gatilhos do Grupo 3

| Fato | NT de destino |
| --- | --- |
| Cozinha profissional | 3-01 |
| GLP/GN usado na edificação ou área de risco | 3-02 |
| Motogerador | 3-03 |
| Subestação elétrica | 3-04 |
| Caldeira ou vaso de pressão | 3-05 |
| Líquido inflamável ou combustível armazenado | 3-06 |
| Heliponto ou heliporto | 3-07 |
| Estação ou infraestrutura de recarga de veículo elétrico | Grupo 3 + atos administrativos; aplicar a orientação vigente localizada, sem inventar NT 3-08 |

## Gatilhos do Grupo 4

| Fato | NT de destino |
| --- | --- |
| Quiosque ou área de exposição/venda | 4-01 |
| Restrição de liberdade | 4-02 |
| Bem tombado | 4-03 |
| Fabricação, armazenagem ou comércio de munição/explosivo/pirotecnia | 4-04 |
| Manipulação, armazenamento ou comércio de GLP/GN | 4-05 |
| Posto de serviço ou abastecimento | 4-06 |
| Garagem | 4-07 |
| Pátio de armazenagem | 4-08 |
| Túnel | 4-09 |
| Canteiro de obras | 4-10 |
| Estrutura temporária médica Covid-19 | 4-11 |

## Gatilhos do Grupo 5

| Fato | NT de destino |
| --- | --- |
| Centro esportivo, de evento ou exibição | 5-01 |
| Evento pirotécnico | 5-02 |
| Carro alegórico, trio elétrico ou carro de som | 5-03 |
| Evento temporário de reunião de público | 5-04 |
| Atendimento médico de evento | 5-05 |

## Interfaces que não podem ser perdidas

- Restaurante com cozinha e GLP: Grupos 1, 2 e 3.
- Shopping com quiosques e garagem: Grupos 1, 2 e 4; Grupo 3 se houver gás, cozinha, gerador ou outro risco.
- Evento temporário com gerador e pirotecnia: Grupos 1, 2, 3 e 5; Grupo 4 se houver armazenamento/comércio de explosivos.
- Posto com loja, depósito e gerador: Grupos 1, 2, 3 e 4.
- Centro de eventos permanente com montagem temporária: Grupo 5 para o local e para a configuração; Grupos 2 a 4 conforme medidas e riscos.

## Regra de retorno

Cada módulo deve devolver `conforme`, `não conforme`, `pendente` ou `não aplicável`, com fonte e evidência. O orquestrador não pode converter `pendente` bloqueante em conformidade.
