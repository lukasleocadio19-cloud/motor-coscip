---
name: cbmerj-atos-administrativos
description: "Verificar atos administrativos, tramitação, competência, protocolo digital, assinatura eletrônica, procedimento assistido, recursos e modalidades de solicitação dos processos de segurança contra incêndio e pânico do CBMERJ. Usar com $orquestrar-analise-cbmerj e $analisar-processo-cbmerj em PSCIP/LE, CA, CA parcial, AE/EvRP, modificação, segunda via, parecer, TAC, notificação, auto de infração, recurso, desinterdição e processos digitais; usar também para validar DWG/DWF, Termo de Aceite, ART/RRT/TRT, unidade competente e vigência de AAST/Notas DGST."
---

# CBMERJ - Atos Administrativos e Tramitação

Aplicar este módulo ao rito e à prova documental. Não dimensionar medidas dos
Grupos 2 a 5 e não permitir que AAST ou Nota DGST afaste Decreto ou NT.

## Iniciar

1. Ler [references/indice-atos.md](references/indice-atos.md).
2. Localizar a fonte primária em
   [references/fontes-oficiais.md](references/fontes-oficiais.md).
3. Fixar data de protocolo, ato solicitado, fase, unidade, status do portal e atos anteriores.
4. Aplicar [references/controle-vigencia-e-hierarquia.md](references/controle-vigencia-e-hierarquia.md)
   antes de extrair requisito, prazo ou competência.
5. Conferir novamente a página oficial em toda análise posterior à data de captura ou quando
   houver consulta pública, ato transitório ou conflito entre fontes.
6. Registrar a vigência como `confirmada`, `vigencia_aparente`,
   `vigencia_transitoria_aparente`, `superacao_parcial`, `revogacao_expressa` ou
   `requer_validacao_DGST`.

## Selecionar o fluxo

- Projeto/LE: conferir requerimento, legitimidade, emolumento, quadro resumo,
  responsabilidade técnica, arquivo CAD, atos anteriores, classificação e medidas.
- CA/CA parcial/CA assistido: conferir LE aplicável, implantação real, evidência de
  execução e funcionamento, responsabilidade de execução/manutenção/ensaio e limites
  materiais do certificado.
- AE/EvRP: fixar modalidade, público, duração, montagem, licenças, RTs, plano de
  emergência e documentos temporários, sem confundir o rito com PSCIP permanente.
- Modificação, segunda via, parecer, TAC, notificação, auto de infração, recurso e
  desinterdição: identificar ato de entrada, autoridade competente, prazo, efeito,
  documento de saída e evento de encerramento.
- Recurso: aplicar a Lei estadual nº 5.427/2009 e a NT 1-01 cabível; não citar a Lei
  federal nº 9.784/1999 como regência direta sem fundamento específico.
- Estação de recarga de veículo elétrico: separar as exigências obrigatórias dos itens
  2.1 a 2.5 das recomendações dos itens 3.1 a 3.10 da Nota CHEMG nº 326/2025; usar
  [references/recarga-ve-aplicacao.md](references/recarga-ve-aplicacao.md).

## Consultas especializadas

- Fluxo digital, CAD, Termo de Aceite e assinatura:
  [references/fluxo-digital-e-cad.md](references/fluxo-digital-e-cad.md).
- Documentos, entrada, saída e bloqueios por solicitação:
  [references/matriz-tipos-processo.md](references/matriz-tipos-processo.md).
- Recursos e prazos:
  [references/lei-5427-recursos.md](references/lei-5427-recursos.md).
- Competência DGST/SST/DGDP:
  [references/competencia-dgst-sst.md](references/competencia-dgst-sst.md).

## Executar

1. Construir manifesto do lote documental com hash, arquivo, tipo, páginas, versão,
   assinatura, responsável, escopo, data de upload e relação com o ato.
2. Validar a cadeia `requerente → responsável legal → pessoa jurídica → vínculo com o
   imóvel → endereço → ato solicitado`.
3. Validar DAEM e pagamento por número/código de barras, receita, contribuinte, endereço,
   valor, vencimento e data de pagamento.
4. Validar ART/RRT/TRT separadamente para PSCIP, levantamento/projeto arquitetônico,
   execução, instalação, manutenção, ensaio e laudo. Não aceitar o tipo documental como
   prova suficiente de atribuição ou escopo.
5. Para assinatura eletrônica, executar validação pelo código, hash, QR ou URL oficial;
   inspeção visual da imagem da assinatura não prova autenticidade.
6. No Portal do Requerente, distinguir Termo de Responsabilidade/Termo de Aceite de
   declaração do RT e controlar o prazo de upload de sete dias.
7. Em documento anterior, comparar endereço, área, ocupação, finalidade, responsável,
   abrangência e medidas com o objeto atual; não tratar coincidência de endereço como
   identidade de objeto.
8. Retornar ao orquestrador fatos, conformidades, pendências, competência, prazo,
   vigência e bloqueios. Não emitir decisão administrativa.

## Saída

| Campo | Conteúdo |
| --- | --- |
| Ato/fase | Solicitação e estado processual |
| Competência | Unidade e fundamento |
| Lote | Arquivos, versões, assinaturas e uploads |
| Legitimidade | Responsável, representação e vínculo |
| Emolumento | Receita, valor, pagamento e consistência |
| Responsabilidades | ART/RRT/TRT por objeto e etapa |
| Digital | Termo, prazo, DWG/DWF, layouts e assinatura |
| Atos anteriores | Abrangência e compatibilidade |
| Vigência | Estado de cada ato aplicado |
| Resultado | Conforme, não conforme, pendente ou não aplicável |
| Fonte | Ato, item e página |
| Saneamento | Documento, correção ou decisão necessária |

Usar `pendente` quando faltar validação de assinatura, atribuição profissional,
representação legal, vínculo, pagamento, competência ou vigência.
