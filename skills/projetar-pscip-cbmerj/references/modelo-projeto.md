# Projeto de segurança contra incêndio e pânico — controle

> RASCUNHO sem valor normativo. Elaborado com o motor COSCIP para revisão do responsável técnico.

Copie este arquivo para a pasta do projeto e mantenha-o atualizado. Não apague linhas: mude a
situação. "Fonte" é sempre quem informou (usuário, planta, ferramenta) ou o item da norma.

## 1. Dados da edificação

| Dado | Valor | Fonte / data |
|---|---|---|
| Empreendimento e endereço | | |
| Ocupação (divisão NT 1-04) | | confirmada pelo usuário em … |
| Ocupação única? | | |
| Área total construída (m²) | | |
| Pavimentos | | |
| Altura (m) | | |
| Situação (nova / existente / anterior ao Decreto) | | |
| Riscos específicos | | |

## 2. Enquadramento

| Item | Resultado | Base |
|---|---|---|
| Risco (NT 1-04) | | |
| Tabela e coluna do Anexo III | | campo `conferencia` do enquadramento |
| Distância máxima até a saída | | NT 2-08, Anexo C |
| Exceções da NT 1-04 conferidas com o usuário | | |

## 3. Medidas de segurança

Uma linha por medida devolvida em `medidas`. Situação: a fazer · calculada · lida na NT ·
desenhada · conferida na planta · pendente com o responsável técnico.

| Medida | Célula e observações | Como tratar | Resultado (com citação) | Situação |
|---|---|---|---|---|
| Extintores | | `dimensionar_extintores` | | |
| Saídas de emergência | | `dimensionar_saidas` | | |
| … | | | | |

## 4. Premissas do projetista (confirmar com o usuário)

| Premissa | Valor | Confirmada por / data |
|---|---|---|
| | | |

## 5. Pendências

| Pendência | Origem (ferramenta, NT, análise da planta) | Quem resolve |
|---|---|---|
| | | |

## 6. Arquivos gerados

| Arquivo | Conteúdo |
|---|---|
| `….dxf` | plantas, legenda e corte esquemático |
| `….coscip.json` | operações que geram o DXF (para retomar) |
| `….md` | memorial de cálculo |

## 7. O que o motor não cobriu neste projeto

Liste aqui, sem suavizar: sistemas sem cálculo, tabelas sem conferência visual, partes só lidas na
NT.
