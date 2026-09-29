---
name: emitir-bilhete-cbmerj
description: "Redigir, revisar, reordenar e reduzir o bilhete de exigências dos processos de segurança contra incêndio e pânico do CBMERJ — LE/PSCIP, CA, CAA, CAS, CVA, AE/EvRP, modificação, fiscalização e recurso. Usar SEMPRE que o usuário pedir bilhete, exigências, pendências para o solicitante, texto para devolver o processo, ou pedir para caber no limite de caracteres do sistema. Converter a matriz consolidada de $orquestrar-analise-cbmerj e $analisar-processo-cbmerj em documento externo com citação normativa rastreável. Chamada por $orquestrar-analise-cbmerj após a consolidação e os bloqueios."
---

# Emissão de bilhete de exigências CBMERJ

Transformar achados internos em documento endereçado ao solicitante. O bilhete é a face externa da análise: comunica o que está errado, sob qual norma, e o que fazer.

Esta habilidade **não produz achados novos**. Consome a matriz já consolidada. Se um item do bilhete não puder ser rastreado até um achado da matriz, o item não entra — retorna ao orquestrador.

## Contrato com o orquestrador

Chamada após a etapa 8 (consolidação) e 9 (bloqueios) de `$orquestrar-analise-cbmerj`.

**Entrada esperada:**

| Campo | Conteúdo |
| --- | --- |
| Identificação | Processo, requerimento, interessado, endereço, RT |
| Matriz consolidada | ID, tema, fato, regra, fonte, evidência, resultado, severidade, saneamento |
| Enquadramento | Ocupação, ATC, altura, pavimentos, risco — e o que ainda está indeterminado |
| Matriz de medidas | Medidas exigidas, dispensadas e condicionadas, com a fonte |
| Conformidades | Itens regulares que convém informar ao solicitante |
| Limite do campo | 8.000 caracteres, salvo informação em contrário |
| Ato pretendido | Define o fecho e o vocabulário |

**Saída:**

1. o bilhete, pronto para colar no sistema;
2. a nota de rastreabilidade — **interna, não enviada** — declarando quais citações foram verificadas em fonte primária e quais vieram de prática institucional ou não foram confirmadas.

**Limites do papel:**

- não criar exigência ausente da matriz;
- não converter `pendente` em `não conforme`, nem o contrário;
- não deferir, indeferir, emitir, autorizar nem antecipar o ato decisório;
- não suprimir achado bloqueante para caber no limite de caracteres;
- não inventar item, subitem, anexo ou alínea de NT.

## Ciclo

### 1. Selecionar o que entra

Entram no bilhete os achados com resultado `não conforme` e `pendente`.

Não entram: `conforme`, `não aplicável`, severidade, nível de confiança, nome de módulo ou habilidade, estado de leitura de CAD, rastro de ferramenta, deliberação interna.

Todo achado `bloqueante` entra obrigatoriamente. Se o limite de caracteres não comportar todos os bloqueantes, o limite não é o problema — avisar o usuário e não cortar.

### 2. Agrupar por tema, não por documento

Um defeito que aparece em três documentos é **um** item, com as três fontes no corpo do fato. Um documento com quatro defeitos distintos rende quatro itens, ou um item com incisos `(i) (ii) (iii) (iv)` quando o pedido de saneamento for único.

Regra prática: se o "Solicita-se" for o mesmo, é um item só.

### 3. Ordenar

Ordem padrão, do enquadramento para a forma:

1. enquadramento — ATC, altura, pavimentos, ocupação, risco;
2. Quadro Resumo;
3. matriz de medidas exigidas;
4. cada medida de segurança, na ordem da matriz do Decreto;
5. memorial descritivo;
6. documentação, assinatura e vínculo com o imóvel;
7. responsabilidade técnica e carimbos;
8. arquivo digital.

Ordem alternativa, quando o vício formal impede a própria admissão do pedido: assinatura, representação e documentação primeiro. Perguntar ao usuário quando houver vício de assinatura, em vez de escolher sozinho.

### 4. Redigir cada item

Ler [references/anatomia-do-bilhete.md](references/anatomia-do-bilhete.md) antes de escrever o primeiro item.

Forma canônica:

```
N. Título do defeito — Norma, dispositivo: Fato observado, com a divergência
explicitada e as fontes nomeadas. Solicita-se providência específica.
```

### 5. Citar o item da NT — obrigatório

O padrão do bilhete do CBMERJ cita **o item exigente**, não apenas a norma. `NT 2-01:2020` sozinho não atende; `NT 2-01:2020, item 7.3, Tabela 5` atende.

Ordem de trabalho:

1. Conferir a edição em [references/edicoes-vigentes.md](references/edicoes-vigentes.md). Repetir `:2019` por hábito é o erro mais comum — boa parte das NTs já está em 2ª ou 3ª edição.
2. Procurar o tema em [references/banco-de-citacoes.md](references/banco-de-citacoes.md).
3. Se não estiver no banco, **localizar o item na própria NT**:

```bash
python3 scripts/localizar_item.py "distancia maxima a ser percorrida" --nt 2-01
```

O script varre as conversões oficiais mantidas em `$cbmerj-grupo-N-*/references/nt-*.md` e devolve item, edição e página do PDF. Ler o trecho antes de citar: o item imediatamente acima da linha nem sempre é o que fundamenta a exigência.

4. Confirmada a fonte, promover a citação no banco.

**Nunca inventar item por dedução ou analogia.** Se, depois da busca, o item não for localizado, não emitir o bilhete com a NT solta: marcar a lacuna de forma visível para o analista completar —

```
NT 2-07:2019, item [A CONFERIR]
```

— e listar a pendência na nota de rastreabilidade. Um bilhete com marcador é corrigível; um bilhete com item inventado é insustentável se o solicitante conferir.

Nunca escrever apenas "conforme COSCIP" quando artigo, item, tabela ou anexo estiverem disponíveis.

### 6. Verificar antes de exigir

Antes de escrever "Solicita-se projetar/dimensionar/apresentar X", confirmar que X é exigido no enquadramento do caso, conferindo a matriz de medidas do Decreto.

Erro recorrente: exigir medida que o Quadro Resumo ou o carimbo declara mas que a matriz não impõe. Quando projeto e norma divergem sobre a **existência** da exigência, o item correto é a compatibilização — corrigir o carimbo ou projetar integralmente —, não a imposição da medida.

### 7. Fechar

Blocos finais, nesta ordem, conforme o caso:

1. nota sobre o Quadro Resumo da prancha 01 e dispensa do PDF separado, quando houver Quadro Resumo a corrigir;
2. informação sobre itens regulares que o solicitante não precisa refazer — DAEM, receita, taxa paga, documento aceito;
3. ressalva final de nova análise.

Texto padrão da ressalva, em [references/anatomia-do-bilhete.md](references/anatomia-do-bilhete.md).

### 8. Medir e reduzir

O limite é de **8.000 caracteres**. Medir sempre, mesmo quando o texto parecer curto:

```bash
python3 scripts/contar_bilhete.py bilhete.txt --limite 8000
```

O script devolve caracteres, bytes UTF-8, contagem por item e os itens mais longos. **Caracteres e bytes divergem** — texto em português tem cerca de 3,5% mais bytes que caracteres por causa da acentuação. Se não souber como o sistema conta, dimensionar pelo maior dos dois.

Para reduzir, seguir a ordem de cortes de [references/protocolo-de-reducao.md](references/protocolo-de-reducao.md). Nunca reduzir suprimindo item bloqueante, dispositivo normativo ou o "Solicita-se".

### 9. Entregar

Entregar o bilhete em texto corrido, pronto para colar. Depois, separadamente e identificado como interno:

- contagem final de caracteres e bytes;
- o que foi cortado, caso o usuário queira reverter;
- citações não verificadas em fonte primária.

Não gerar arquivo salvo se o usuário não pedir.

## Revisão de bilhete existente

Quando o usuário colar um bilhete pronto pedindo revisão, redução ou acréscimo de item:

1. preservar a numeração e a redação do que ele já validou — ele é o analista;
2. inserir item novo na posição que ele indicar; se não indicar, propor a posição e dizer que renumerou;
3. ao reduzir, mostrar a contagem antes e depois;
4. apontar, sem corrigir por conta própria, citação que pareça incorreta.

## Limites

- Não afirmar que a exigência decorre de norma que não foi lida.
- Não descrever no bilhete o método de análise, ferramenta, conversão de arquivo ou dificuldade técnica do analista.
- Não usar linguagem que anteceda a decisão da autoridade — "indeferido", "aprovado", "reprovado".
- Não transportar para o bilhete o achado que dependa de leitura ainda não concluída sem marcá-lo como pendência de esclarecimento.
- Não citar dado pessoal além do necessário para identificar a divergência.
