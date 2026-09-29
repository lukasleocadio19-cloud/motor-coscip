# Contrato de delegação e modelo de saída

## 1. Papéis

- **Orquestrador**: fixa ato, regime, módulos e dependências; recebe a conclusão.
- **Analista de processo**: controla o dossiê, executa o roteiro LE/CA/AE, confronta evidências e decide cada requisito.
- **Coletor de NT**: responde questão normativa delimitada. Não aprova, não indefere e não altera a classificação-base.

## 2. Quando delegar

Use subagentes quando houver duas ou mais NTs independentes ou acervo extenso que possa ser dividido sem perder dependências. Não delegue antes de fechar ocupação, área, altura, população, risco e versão dos documentos necessários ao pacote.

Um coletor por:

- NT individual; ou
- conjunto inseparável, como parte geral/específica do mesmo sistema.

O analista principal retém classificação, conflitos, precedência e conclusão.

## 3. Entrada obrigatória do coletor

```yaml
processo:
  tipo: LE | CA | AE
  regime_temporal: "..."
  fatos_comprovados:
    - campo: "..."
      valor: "..."
      unidade: "..."
      fonte: "arquivo/prancha/página"
questao: "pergunta testável"
fontes_autorizadas:
  - "skill do grupo e arquivos/NTs exatos"
evidencias_disponiveis:
  - "arquivo/prancha/página relevante"
saida_exigida:
  - aplicabilidade
  - regras
  - testes
  - evidencias_esperadas
  - lacunas
```

## 4. Saída obrigatória do coletor

```yaml
questao: "..."
aplicabilidade:
  resultado: aplica | nao_aplica | indeterminada
  fundamento: "..."
regras:
  - requisito: "obrigação atômica"
    fonte:
      documento: "NT x-xx"
      edicao: "..."
      item: "..."
      tabela_anexo: "..."
      pagina: "..."
    entradas_necessarias: ["..."]
    teste: "procedimento reproduzível"
    evidencia_esperada: "..."
interfaces: ["outras NTs ou fatos dependentes"]
lacunas: ["dado ou fonte ausente"]
conflitos: ["fontes divergentes"]
confianca: alta | media | baixa
```

O coletor deve citar a fonte incorporada, distinguir transcrição de síntese, evitar citações longas e informar quando a tabela/figura exige inspeção visual.

## 5. Controle de qualidade do analista

Ao receber os pacotes:

1. conferir se a edição é a vigente incorporada;
2. validar pelo menos a localização normativa de cada regra material;
3. eliminar regras fora do escopo;
4. resolver dependências e duplicidades;
5. preservar conflitos sem votação entre agentes;
6. aplicar os testes às evidências do processo;
7. produzir a matriz consolidada.

## 6. Saída final

### Identificação

Tipo de processo, objeto, endereço, requerente, responsáveis, versão analisada, regime temporal e atos anteriores.

### Documentos

Inventário com corrente/superado/ausente/ilegível e inconsistências.

### Enquadramento

Ocupação/divisão, risco, ATC, altura, pavimentos, população, uso misto, riscos/estruturas especiais e competência.

### Matriz requisito-evidência

Uma linha por obrigação, com fonte, evidência, teste, resultado e justificativa.

### Achados

Separar:

1. não conformidades;
2. pendências documentais;
3. contradições;
4. itens não aplicáveis comprovados;
5. pontos que exigem CAT/decisão superior/verificação manual.

### Exigências propostas

Para cada uma: localização, fato, fonte, teste falho e correção/evidência requerida.

### Conclusão

Estado operacional, condicionantes, limites e lista de verificações não executadas.

## 7. Testes de aceitação

### LE

O resultado deriva as medidas do Decreto, aciona as NTs corretas, reproduz cálculos e prova coerência do Quadro Resumo com o desenho.

### CA

O resultado identifica a linha de base aprovada e vincula cada medida/riscos do LE a evidência de execução válida, distinguindo falta documental de divergência material.

### AE

O resultado fixa a versão do evento, recalcula público, verifica setores/saídas/estruturas/riscos/FARE e separa condições permanentes das temporárias.

### Todos

Nenhuma conclusão favorável pode conter requisito aplicável sem fonte, teste ou evidência suficiente.
