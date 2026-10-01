# Matriz de cobertura da análise

Preencher uma linha para cada requisito acionado pelo Decreto, NT, ato administrativo, LE, projeto aprovado ou condição anterior.

| Campo | Conteúdo obrigatório |
| --- | --- |
| ID da regra | Identificador estável |
| Gatilho | Fato que tornou a regra aplicável |
| Fonte | Documento, edição, artigo/item/tabela/anexo/página |
| Responsável | Administrativo, analista, Grupo 1–5 ou coletor |
| Entrada | Dado necessário ao teste |
| Método | Como reproduzir o teste |
| Evidência esperada | Documento, página, prancha, detalhe, cálculo ou validação |
| Evidência localizada | Localização exata ou ausência |
| Estado | Conforme, não conforme, pendente ou não aplicável |
| Dependência | Regras/achados que precisam ser resolvidos antes |
| Saneamento | Correção ou documento necessário |

## Auditorias obrigatórias

1. **Cobertura normativa:** toda medida, risco, estrutura, evento e regra administrativa acionados têm uma linha.
2. **Cobertura documental:** todo arquivo do Termo de Aceite ou manifesto foi localizado, identificado e lido no nível necessário.
3. **Cobertura reversa:** toda afirmação relevante do requerimento, Quadro Resumo, memorial ou prancha tem fonte/evidência e foi confrontada.
4. **Cobertura de atos anteriores:** cada ato teve vigência, objeto e condições de sobrevivência testados.
5. **Cobertura de responsabilidade:** cada assinatura e documento técnico está ligado a pessoa/empresa, papel, vínculo e escopo.
6. **Cobertura visual/CAD:** tabela, imagem, OLE, xref, fonte ou geometria determinante não ficou mascarada por extração incompleta.
7. **Cobertura de dependência externa:** toda remissão material a ABNT, Inmetro, fabricante ou outra fonte registra referência/edição e disponibilidade; fonte necessária ausente produz `dependência_externa_não_disponível`.

Falhar em qualquer auditoria produz `pendente` bloqueante, com a lacuna nomeada. Não transformar ausência de prova em conformidade.
