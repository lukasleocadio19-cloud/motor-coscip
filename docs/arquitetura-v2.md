# Motor CAD/COSCIP — Arquitetura Complementar v2

**Documento complementar ao `proxima-sessao.md`**  
**Objetivo:** definir a refatoração estrutural necessária para transformar o Motor CAD/COSCIP em um sistema de análise de processos completo, auditável e de saída simples, incorporando planta CAD, documentação técnica, regras normativas, LLM, Jev/TypeSafe, cruzamento de evidências e revisão humana.

> Este documento **não substitui** `proxima-sessao.md`.  
> O arquivo `proxima-sessao.md` continua sendo o registro único de estado, histórico, pendências e continuidade do projeto.  
> Este documento descreve a **arquitetura-alvo e o plano de construção** para a próxima evolução do sistema.

---

# 1. Objetivo da refatoração

O sistema atual já possui fundações fortes:

- leitura e preparação de arquivos CAD;
- conversão DWG → DXF;
- extração de entidades, layers, textos e blocos;
- confirmação de unidade;
- recortes de pavimentos;
- medição e geometria;
- análise indicativa;
- base normativa com fontes versionadas e SHA-256;
- DSL de regras;
- regras de extintores, hidrantes, acionadores, iluminação e saídas;
- início da incorporação das Tabelas do Anexo III do Decreto 42/2018;
- revisão humana append-only;
- relatórios HTML imutáveis;
- histórico e rastreabilidade das decisões.

O problema principal a resolver agora não é ausência de capacidade técnica, mas **complexidade da experiência de análise**.

A arquitetura atual tende a misturar:

1. dados informados pelo analista;
2. inferências automáticas;
3. heurísticas;
4. resultados geométricos;
5. regras normativas;
6. falta de evidência;
7. resultados inconclusivos;
8. pendências;
9. necessidade de revisão humana.

A nova arquitetura deve separar essas responsabilidades.

O sistema deverá responder sempre a cinco perguntas:

1. **O que o COSCIP exige que seja verificado neste processo?**
2. **Qual evidência é necessária para cada verificação?**
3. **Onde essa evidência foi encontrada?**
4. **O que a regra normativa conclui a partir dela?**
5. **O que o analista precisa efetivamente revisar ou solicitar?**

---

# 2. Princípio central da nova arquitetura

A análise não deve mais começar perguntando:

> “O que consigo encontrar nesta planta?”

Ela deve começar perguntando:

> “Considerando o enquadramento deste processo, o que precisa ser verificado segundo o COSCIP, as NTs e demais regras aplicáveis?”

O núcleo da arquitetura passa a ser o **Plano de Verificação COSCIP**.

Fluxo-alvo:

```text
PROCESSO
│
├── dados da edificação
├── plantas CAD
├── ART / RRT
├── memoriais
├── laudos
├── certificados
├── declarações
├── fichas técnicas
├── relatórios fotográficos
└── demais documentos
        │
        ▼
ENQUADRAMENTO
        │
        ▼
COMPILADOR NORMATIVO
        │
        ▼
PLANO DE VERIFICAÇÃO
        │
        ├── checks de planta
        ├── checks documentais
        ├── checks geométricos
        ├── checks de consistência
        ├── checks cruzados
        └── checks de revisão humana
        │
        ▼
COLETA DE EVIDÊNCIAS
        │
        ├── CAD
        ├── documentos
        ├── LLM
        ├── Jev
        ├── cálculo
        └── confirmação humana
        │
        ▼
MOTOR DE REGRAS
        │
        ▼
ACHADOS
        │
        ▼
CONSOLIDADOR
        │
        ├── pendências
        ├── dados ausentes
        ├── divergências
        ├── inconclusivos
        └── itens conformes
        │
        ▼
REVISÃO HUMANA
        │
        ▼
PARECER FINAL
```

---

# 3. Mudança conceitual obrigatória

## 3.1 Não usar uma única propriedade “status”

O sistema precisa separar três dimensões diferentes.

### A. Status normativo (`compliance_status`)

```text
COMPLIANT
NON_COMPLIANT
NOT_APPLICABLE
UNDETERMINED
```

Significados:

- `COMPLIANT`: evidência suficiente e regra atendida;
- `NON_COMPLIANT`: evidência suficiente e regra não atendida;
- `NOT_APPLICABLE`: check não aplicável ao enquadramento;
- `UNDETERMINED`: não existe base suficiente para concluir.

### B. Qualidade da evidência (`evidence_status`)

```text
SUFFICIENT
PARTIAL
MISSING
CONFLICTING
UNVERIFIED
```

### C. Estado de revisão (`review_status`)

```text
NOT_REQUIRED
PENDING
CONFIRMED
CONTESTED
DATA_REQUESTED
```

Esses três campos não podem ser fundidos.

Exemplo correto:

```json
{
  "compliance_status": "UNDETERMINED",
  "evidence_status": "MISSING",
  "review_status": "PENDING"
}
```

Isso é diferente de simplesmente registrar “REVISÃO”.

---

# 4. Novo modelo de domínio

A nova arquitetura deve ser centrada em três entidades principais:

1. `Check`
2. `Evidence`
3. `Finding`

---

# 5. Entidade Check

Um `Check` representa **uma pergunta normativa verificável**.

Exemplo:

```yaml
id: HID-DOC-004
version: 1
title: Características técnicas da motobomba
system: HIDRANTES
category: DOCUMENT
scope: PROCESS
severity: MAJOR

question:
  type: required_fields

required_evidence:
  - ART
  - RRT
  - MEMORIAL
  - CURVE
  - DATASHEET

required_fields:
  - manufacturer
  - model
  - flow_l_min
  - pressure_mca
  - rpm
  - impeller_diameter_mm
  - power_kw

normative_basis:
  - source_id: NT-2-04
    item: "5.1.21"
  - source_id: NT-2-04
    item: "5.1.22"

result_rules:
  missing_required_field: UNDETERMINED
  conflicting_values: UNDETERMINED
  all_present_and_consistent: COMPLIANT

human_review:
  required_if:
    - semantic_confidence_below: 0.90
    - conflicting_values
```

O catálogo de checks deve ser:

- versionado;
- testável;
- determinístico;
- auditável;
- separado da interface;
- separado da LLM;
- separado do Jev.

---

# 6. Tipos de Check

A arquitetura deve suportar pelo menos:

```text
DOCUMENT_PRESENCE
DOCUMENT_FIELD
DOCUMENT_SCOPE
CAD_PRESENCE
CAD_COUNT
CAD_DISTANCE
CAD_COVERAGE
CAD_DIMENSION
CALCULATION
NORMATIVE_TABLE
CROSS_DOCUMENT
CAD_DOCUMENT_CROSS
CONSISTENCY
MANUAL_CONFIRMATION
QUALITY_GATE
```

---

# 7. Entidade Evidence

`Evidence` representa **qualquer fato utilizado para responder a um check**.

Exemplo:

```json
{
  "id": "evidence-...",
  "process_id": "...",
  "source_type": "DOCUMENT",
  "source_id": "document-...",
  "source_version": 3,
  "source_hash": "...",
  "locator": {
    "page": 4,
    "bbox": [0.12, 0.41, 0.88, 0.52]
  },
  "field": "pump_flow_l_min",
  "raw_value": "200 L/min",
  "normalized_value": 200,
  "unit": "L/min",
  "extraction_method": "LLM",
  "semantic_validation": "JEV",
  "confidence": 0.97,
  "created_at": "...",
  "immutable": true
}
```

Toda evidência deve guardar:

- origem;
- versão;
- hash;
- local exato;
- método de extração;
- valor bruto;
- valor normalizado;
- confiança;
- modelo utilizado;
- schema utilizado;
- timestamp.

---

# 8. Entidade Finding

`Finding` é o resultado da execução de um `Check`.

Exemplo:

```json
{
  "check_id": "HID-DOC-004",
  "check_version": 1,
  "compliance_status": "UNDETERMINED",
  "evidence_status": "PARTIAL",
  "review_status": "PENDING",
  "severity": "MAJOR",
  "summary": "ART não identifica completamente a motobomba.",
  "missing": [
    "manufacturer",
    "model",
    "rpm",
    "impeller_diameter_mm",
    "power_kw"
  ],
  "evidence_ids": ["..."],
  "normative_citations": ["..."],
  "generated_action": "Apresentar ART complementar ou substitutiva..."
}
```

O texto da pendência não deve ser a fonte da verdade.

A fonte da verdade é o `Finding` estruturado.

O texto final é apenas uma representação dele.

---

# 9. Criar um Processo como entidade de primeiro nível

Hoje o sistema é fortemente centrado no desenho.

A nova arquitetura deve ser centrada no **Processo**.

Estrutura:

```text
Process
├── metadata
├── building_context
├── occupancy_context
├── risk_context
├── normative_context
├── drawings[]
├── documents[]
├── verification_plan
├── analyses[]
├── findings[]
├── reviews[]
└── reports[]
```

---

# 10. Documentos que o sistema deverá aceitar

O sistema deve aceitar documentos PDF e, futuramente, formatos nativos quando necessário.

Categorias mínimas:

```text
ART
RRT
TRT
MEMORIAL_DESCRITIVO
MEMORIAL_CALCULO
LAUDO
CERTIFICADO
DECLARACAO
CURVA_BOMBA
FICHA_TECNICA
CATALOGO
RELATORIO_FOTOGRAFICO
PROJETO_PDF
COMPROVANTE
TERMO
ATESTADO
OUTRO
```

O sistema não deve depender exclusivamente da classificação manual.

Fluxo:

```text
upload
↓
hash
↓
extração de texto
↓
segmentação
↓
classificação documental
↓
extração estruturada
↓
evidências
↓
checks
```

---

# 11. Motor Documental

Criar um novo pacote dedicado.

Estrutura sugerida:

```text
packages/
  documents/
    coscip_documents/
      __init__.py
      models.py
      classifier.py
      extractor.py
      chunker.py
      normalization.py
      evidence_builder.py
      registry.py
      validators.py
```

No backend:

```text
apps/api/coscip_api/documents/
    service.py
    schemas.py
    routers.py
    jobs.py
```

---

# 12. Pipeline documental

## Etapa 1 — Ingestão

Ao receber um arquivo:

- calcular SHA-256;
- gravar imutavelmente;
- detectar MIME;
- validar estrutura;
- registrar origem;
- registrar versão;
- criar job de processamento.

## Etapa 2 — Extração de texto

Preferir:

1. texto embutido no PDF;
2. parsing estrutural;
3. OCR somente quando necessário.

Nunca substituir silenciosamente uma fonte por OCR.

Registrar:

```text
TEXT_NATIVE
TEXT_EXTRACTED
OCR
MANUAL
```

## Etapa 3 — Segmentação

Segmentar por:

- página;
- título;
- seção;
- tabela;
- campo;
- bloco semântico.

## Etapa 4 — Classificação

Classificar:

- tipo documental;
- sistema relacionado;
- finalidade;
- conteúdo principal;
- provável relação com checks.

## Etapa 5 — Extração estruturada

Extrair fatos em schemas específicos.

Exemplo `ARTSchema`:

```python
class ARTSchema:
    professional_name: str | None
    professional_registration: str | None
    contractor: str | None
    owner: str | None
    address: str | None
    activity_codes: list[str]
    activity_description: list[str]
    systems: list[str]
    equipment: list[Equipment]
    issue_date: date | None
    art_number: str | None
```

---

# 13. Papel da LLM

A LLM deve ser usada principalmente como **extrator semântico estruturado**.

A LLM pode:

- identificar campos;
- interpretar texto livre;
- relacionar títulos e valores;
- extrair tabelas semanticamente difíceis;
- apontar trechos candidatos;
- resumir escopo documental;
- identificar termos equivalentes;
- sugerir normalização.

A LLM não deve:

- definir sozinha se algo atende ao COSCIP;
- inventar requisito normativo;
- substituir regra determinística;
- declarar aprovação/reprovação final;
- alterar evidência sem rastreabilidade.

Toda saída deve respeitar JSON Schema/Pydantic.

Exemplo:

```text
PDF
↓
LLM
↓
JSON estruturado
↓
validação
↓
Evidence[]
```

---

# 14. Papel do Jev / TypeSafe

O Jev deve atuar em decisões probabilísticas fechadas.

Casos de uso:

## 14.1 Classificação documental

```text
ART / RRT / Memorial / Laudo / Certificado / Outro
```

## 14.2 Correspondência semântica

Pergunta:

> Esta descrição da ART abrange o sistema de hidrantes?

Saída probabilística.

## 14.3 Correspondência entre entidades

Exemplo:

> A bomba mencionada na ART é provavelmente a mesma bomba da curva apresentada?

## 14.4 Ambiguidade

> A informação é suficientemente clara para uso automático?

## 14.5 Contradição

> Existem sinais de que dois documentos descrevem equipamentos diferentes?

## 14.6 Roteamento

```text
AUTO_ACCEPT
HUMAN_REVIEW
REQUEST_DATA
```

## 14.7 Classificação CAD

- layer;
- bloco;
- símbolo;
- ambiente;
- elemento.

O Jev nunca deverá ser a autoridade normativa.

---

# 15. Provider abstraction para IA

Criar:

```text
packages/ai/coscip_ai/
    provider.py
    llm_provider.py
    jev_provider.py
    schemas.py
    thresholds.py
    audit.py
    budget.py
```

Interfaces sugeridas:

```python
class StructuredExtractionProvider(Protocol):
    def extract(self, *, schema, content, context) -> ExtractionResult:
        ...

class DecisionProvider(Protocol):
    def decide(self, *, state, questions) -> DecisionResult:
        ...
```

Jev deve implementar `DecisionProvider`.

A LLM deve implementar `StructuredExtractionProvider`.

---

# 16. Registro obrigatório de chamadas de IA

Criar tabela:

```text
ai_runs
```

Campos:

```text
id
provider
model
operation_type
schema_version
question_set_version
input_hash
input_reference
output_hash
raw_output
normalized_output
confidence
tokens_in
tokens_out
cost
latency_ms
created_at
```

Nenhuma análise deve depender apenas de resposta transitória de IA.

---

# 17. Thresholds de confiança

Criar política centralizada.

Exemplo:

```yaml
jev:
  classification:
    auto_accept: 0.97
    human_review: 0.80

  semantic_match:
    auto_accept: 0.95
    human_review: 0.75

  contradiction:
    escalate: 0.70
```

Nunca espalhar thresholds diretamente pelo código.

---

# 18. Plano de Verificação COSCIP

Este é o núcleo da refatoração.

Criar:

```text
packages/normative/coscip_normative/
    verification/
        models.py
        catalog.py
        compiler.py
        applicability.py
        dependencies.py
        executor.py
```

Entrada:

```json
{
  "occupancy": "M-2",
  "risk": "GRANDE",
  "atc_m2": 1200,
  "floors": 1,
  "height_m": 4.5,
  "special_conditions": [...]
}
```

Saída:

```json
{
  "plan_version": "...",
  "applicable_checks": [
    "EXT-CAD-001",
    "EXT-CAD-002",
    "HID-CAD-001",
    "HID-DOC-001",
    "HID-DOC-004",
    "HID-CROSS-002"
  ],
  "not_applicable_checks": [...],
  "manual_checks": [...]
}
```

---

# 19. Catálogo normativo de Checks

O catálogo deve ser organizado por sistema.

Exemplo:

```text
normative/checks/
    common/
    extintores/
    hidrantes/
    alarme/
    iluminacao/
    sinalizacao/
    saidas/
    sprinklers/
    glp/
    pressurizacao/
    controle_fumaca/
    spda/
    materiais_acabamento/
```

Cada check deve conter:

- ID estável;
- versão;
- sistema;
- pergunta;
- aplicabilidade;
- dependências;
- evidências aceitas;
- regra;
- resultado em caso de ausência;
- base normativa;
- severidade;
- regra de revisão.

---

# 20. Dependências entre Checks

Checks podem depender de outros.

Exemplo:

```text
HID-REQ-001
"hidrante é exigido?"

↓ se sim

HID-CAD-001
"hidrantes existem na planta?"

HID-DOC-001
"há responsabilidade técnica?"

HID-DOC-004
"motobomba identificada?"

HID-CALC-001
"memorial hidráulico disponível?"

HID-CROSS-001
"valores de vazão e pressão são coerentes?"
```

O executor deve respeitar dependências.

---

# 21. Motor de Cruzamento

Criar:

```text
packages/analysis/coscip_crosscheck/
    engine.py
    matching.py
    conflicts.py
    normalization.py
```

Funções:

- planta × ART;
- planta × RRT;
- planta × memorial;
- ART × memorial;
- ART × curva;
- memorial × ficha técnica;
- cálculo × equipamento;
- documento × documento.

---

# 22. Modelo de Claim

Criar um modelo intermediário:

```text
Claim
```

Exemplo:

```json
{
  "subject": "fire_pump_1",
  "property": "flow_l_min",
  "value": 200,
  "unit": "L/min",
  "source": "ART",
  "evidence_id": "..."
}
```

Outro documento:

```json
{
  "subject": "fire_pump_1",
  "property": "flow_l_min",
  "value": 250,
  "unit": "L/min",
  "source": "MEMORIAL",
  "evidence_id": "..."
}
```

O Crosscheck detecta:

```text
CONFLICT
200 != 250
```

---

# 23. Entity Resolution

Para cruzar documentos, o sistema precisa resolver quando entidades representam o mesmo objeto.

Exemplos:

```text
Bomba principal
Bomba de incêndio principal
Motobomba 01
BP-01
```

Criar:

```text
Entity
EntityAlias
EntityLink
```

O Jev pode ajudar na probabilidade de correspondência.

A confirmação humana deve ser possível.

---

# 24. Matriz de Evidências

Cada Check deverá declarar quais evidências podem respondê-lo.

Exemplo interno:

| Check | CAD | ART/RRT | Memorial | Laudo | Ficha | Humano |
|---|---:|---:|---:|---:|---:|---:|
| existência de extintor | X |  | X |  |  | X |
| responsabilidade hidrante |  | X |  |  |  | X |
| vazão bomba |  | X | X | X | X | X |
| alcance mangueira | X |  |  |  |  | X |

Essa matriz deverá ser compilável a partir dos metadados dos Checks.

---

# 25. Quality Gates

Antes de executar checks geométricos críticos, o sistema deve avaliar se há qualidade suficiente.

Exemplo:

```text
QG-CAD-WALLS
QG-CAD-UNITS
QG-CAD-FLOOR
QG-CAD-SYMBOLS
QG-OCCUPANCY
QG-DOCUMENT-TEXT
```

Se `QG-CAD-WALLS` falhar:

- percurso pode ser calculado;
- resultado numérico pode ser mostrado;
- compliance não pode ser finalizado;
- evidence_status deve refletir baixa qualidade;
- review_status deve ser `PENDING`.

---

# 26. Revisão do Motor CAD

O Motor CAD atual deve ser preservado e adaptado para produzir evidências estruturadas.

Atualmente já existem:

- entidades;
- layers;
- blocos;
- texto;
- geometria;
- recortes;
- unidades;
- origem no DXF;
- percurso;
- extintores presumidos;
- medidas.

A mudança é:

```text
resultado CAD
→ Evidence
→ Check
→ Finding
```

Não:

```text
resultado CAD
→ texto de relatório
```

---

# 27. Resultados geométricos

Todo resultado geométrico deve registrar:

```text
value
unit
tolerance
uncertainty
algorithm
algorithm_version
geometry_snapshot_hash
input_entity_ids
quality_gate
```

Exemplo:

```json
{
  "value": 19.7,
  "unit": "m",
  "uncertainty": 1.1,
  "algorithm": "grid_dijkstra_16",
  "algorithm_version": "2.0",
  "geometry_snapshot_hash": "...",
  "quality_gate": "PARTIAL"
}
```

---

# 28. Aplicação das Tabelas do Anexo III

As Tabelas 2–4 já implementadas devem ser migradas para o novo modelo sem perder o trabalho existente.

Não continuar diretamente Tabelas 5–21 antes da criação das abstrações centrais.

A nova sequência:

1. encapsular consulta das Tabelas 2–4;
2. converter resultado em `NormativeRequirement`;
3. compilar `NormativeRequirement` em Checks;
4. testar;
5. somente depois incorporar Tabelas 5–21.

---

# 29. Entidade NormativeRequirement

Criar:

```text
NormativeRequirement
```

Exemplo:

```json
{
  "system": "HYDRANTS",
  "required": true,
  "source": {
    "document": "Decreto 42/2018",
    "annex": "III",
    "table": 3,
    "row": "M-2",
    "column": "..."
  },
  "conditions": [...],
  "notes": [...],
  "reference_hash": "..."
}
```

---

# 30. Eliminar duplicidade de “verdades”

Atualmente campos como:

```text
requires_hydrants
requires_alarm
requires_lighting
```

podem ser informados manualmente ao mesmo tempo em que o sistema começa a consultar tabelas normativas.

Na nova arquitetura:

```text
normative_requirement
human_override
effective_requirement
```

Exemplo:

```json
{
  "normative_requirement": true,
  "human_override": null,
  "effective_requirement": true
}
```

Se houver override:

```json
{
  "normative_requirement": true,
  "human_override": false,
  "effective_requirement": false,
  "override_reason": "...",
  "review_decision_id": "..."
}
```

Nunca sobrescrever silenciosamente.

---

# 31. Consolidador de Achados

Criar:

```text
packages/analysis/coscip_findings/
    models.py
    consolidate.py
    severity.py
    deduplication.py
    wording.py
```

Responsabilidades:

- deduplicar pendências;
- agrupar por sistema;
- evitar várias mensagens sobre a mesma causa raiz;
- priorizar o que o analista precisa resolver;
- construir linguagem simples;
- separar resultado técnico de texto.

---

# 32. Deduplicação por causa raiz

Exemplo inadequado:

```text
Pendência 1: fabricante ausente
Pendência 2: modelo ausente
Pendência 3: rotação ausente
Pendência 4: potência ausente
```

Exemplo correto:

```text
ART incompleta para identificação da motobomba.

Não foram localizados:
- fabricante;
- modelo;
- rotação;
- potência.
```

Internamente podem existir quatro failures.

Externamente existe um `FindingGroup`.

---

# 33. Severidade

Criar taxonomia:

```text
CRITICAL
MAJOR
MINOR
INFORMATIONAL
```

Severidade não é compliance.

Usar severidade para ordenação da tela.

---

# 34. Nova interface

## Página inicial do processo

Exibir:

```text
Processo
Enquadramento
Plantas
Documentos
Análise
Revisão
Relatórios
Histórico
```

---

# 35. Tela Documentos

Tabela:

```text
Documento
Tipo
Status de leitura
Checks relacionados
Divergências
Última versão
```

Ações:

```text
Adicionar documento
Substituir por nova versão
Visualizar
Ver evidências extraídas
Reprocessar
```

Documentos nunca são sobrescritos.

Nova versão cria novo registro.

---

# 36. Tela Análise — visão executiva

A primeira tela não deve apresentar dezenas de resultados técnicos.

Exibir:

```text
ANÁLISE DO PROCESSO

3 pendências
2 dados ausentes
1 divergência
1 item para revisão
18 verificações sem pendência
```

Em seguida:

```text
PENDÊNCIAS
DADOS AUSENTES
DIVERGÊNCIAS
REVISÃO NECESSÁRIA
```

Itens conformes devem ficar recolhidos.

---

# 37. Card de Finding

Exemplo:

```text
HIDRANTES

ART incompleta para identificação da motobomba

Não foram localizados:
• fabricante
• modelo
• rotação
• potência

Providência:
Apresentar ART complementar ou substitutiva contendo
a identificação técnica do equipamento.

[Ver evidências]
[Ver norma]
[Abrir documento]
[Revisar]
```

---

# 38. Detalhe técnico recolhível

Ao expandir:

```text
Check: HID-DOC-004 v1
Resultado normativo: UNDETERMINED
Evidência: PARTIAL
Revisão: PENDING

Fontes:
ART nº ...
página 2
Memorial ...
página 7

LLM:
schema art/1.0

Jev:
semantic-match/1.0
confidence 0.94

Norma:
NT ...
item ...
```

---

# 39. Não destacar “IA” na tela principal

O analista deve entender:

- problema;
- evidência;
- norma;
- providência.

Jev e LLM aparecem apenas em detalhes técnicos e auditoria.

---

# 40. Navegação evidência → fonte

Toda evidência deve permitir:

```text
Abrir na planta
Abrir documento na página
Destacar trecho
Abrir entidade DXF
Abrir regra
Abrir base normativa
```

---

# 41. Nova tela de revisão

A revisão deve ser por `Finding`, não por texto genérico.

Ações:

```text
CONFIRM
CONTEST
REQUEST_DATA
MARK_RESOLVED
```

`CONFIRM` e `CONTEST` devem exigir status final quando aplicável.

Manter append-only.

---

# 42. Revisões e reanálise

Se um documento novo for adicionado:

- análise anterior permanece;
- nova análise recebe novo snapshot;
- Findings podem ser resolvidos;
- nenhuma decisão anterior é apagada.

---

# 43. Relatórios

Criar dois produtos diferentes.

## 43.1 Parecer do analista

Curto e limpo.

Estrutura:

```text
1. Identificação
2. Enquadramento
3. Documentos analisados
4. Pendências
5. Dados ausentes
6. Divergências
7. Conclusão
```

Evitar:

- hashes;
- prompts;
- detalhes de algoritmo;
- probabilidades;
- logs.

---

# 44. Relatório técnico de auditoria

Completo.

Incluir:

- hashes;
- versões;
- fontes normativas;
- versões dos checks;
- plano de verificação;
- evidências;
- páginas;
- entidades CAD;
- cálculos;
- algoritmos;
- tolerâncias;
- IA utilizada;
- respostas estruturadas;
- probabilidades;
- thresholds;
- decisões humanas;
- histórico;
- versões de documentos.

---

# 45. Banco de dados — novas entidades

Criar, no mínimo:

```text
processes
process_versions
documents
document_versions
document_pages
document_segments
document_extractions

entities
entity_aliases
entity_links

evidences
claims

check_catalog_versions
checks
verification_plans
verification_plan_items

analysis_runs
check_runs
findings
finding_groups

ai_runs
ai_decisions

reviews
reports
```

Preservar tabelas atuais onde possível.

---

# 46. Migração

Não alterar registros históricos.

Estratégia:

```text
migração aditiva
↓
compatibilidade
↓
adaptadores para análise antiga
↓
novo fluxo v2
↓
migração opcional de dados
```

Não converter análises antigas silenciosamente.

---

# 47. APIs propostas

## Processos

```text
POST /v1/processes
GET /v1/processes
GET /v1/processes/{id}
```

## Documentos

```text
POST /v1/processes/{id}/documents
GET /v1/processes/{id}/documents
GET /v1/documents/{id}
GET /v1/documents/{id}/versions
GET /v1/document-versions/{id}/evidence
```

## Plano de verificação

```text
POST /v1/processes/{id}/verification-plan/compile
GET /v1/processes/{id}/verification-plan
```

## Análise

```text
POST /v1/processes/{id}/analyses
GET /v1/processes/{id}/analyses
GET /v1/process-analyses/{id}
```

## Findings

```text
GET /v1/process-analyses/{id}/findings
GET /v1/findings/{id}
POST /v1/findings/{id}/reviews
```

## Evidências

```text
GET /v1/evidence/{id}
```

## Relatórios

```text
POST /v1/process-analyses/{id}/reports
```

---

# 48. Jobs

Adicionar tipos:

```text
DOCUMENT_INGEST
DOCUMENT_EXTRACT
DOCUMENT_CLASSIFY
DOCUMENT_STRUCTURED_EXTRACTION
ENTITY_RESOLUTION
VERIFICATION_PLAN
CHECK_EXECUTION
CROSSCHECK
FINDING_CONSOLIDATION
REPORT_RENDER
```

Todos persistidos.

---

# 49. Orquestrador de análise

Criar:

```text
apps/api/coscip_api/analysis/orchestrator.py
```

Fluxo:

```python
def analyze_process(process_id):
    snapshot = freeze_process(process_id)

    context = build_normative_context(snapshot)

    plan = compile_verification_plan(context)

    collect_existing_evidence(snapshot)

    execute_document_pipeline(plan)
    execute_cad_pipeline(plan)
    execute_geometry_pipeline(plan)
    execute_crosschecks(plan)

    findings = execute_checks(plan)

    consolidated = consolidate(findings)

    return freeze_analysis_snapshot(consolidated)
```

---

# 50. Determinismo

Uma análise deve ser reproduzível quando:

- entradas;
- versões dos documentos;
- pacote normativo;
- check catalog;
- versões dos algoritmos;
- resultados de IA congelados

forem os mesmos.

Chamadas de IA não devem ser refeitas durante reprodução de um relatório antigo.

Usar resultados congelados.

---

# 51. Versionamento obrigatório

Versionar:

```text
normative_package
check_catalog
verification_plan_schema
evidence_schema
finding_schema
LLM extraction schema
Jev question sets
geometry algorithms
report templates
```

---

# 52. Hash de análise

Criar manifesto:

```text
process_snapshot_hash
normative_package_hash
check_catalog_hash
documents_manifest_hash
drawings_manifest_hash
ai_results_manifest_hash
analysis_hash
```

---

# 53. Segurança contra alucinação

Nenhum valor extraído por IA pode ser considerado “fato confirmado” sem localização de evidência.

Regra:

```text
No evidence locator → no evidence
```

A LLM deve fornecer:

```text
page
text span
bbox quando disponível
```

Valores sem origem clara devem ser:

```text
UNVERIFIED
```

---

# 54. Ausência não é negativa

Se a LLM não localizar um campo:

Não concluir automaticamente:

> “o documento não contém”.

Registrar:

```text
NOT_FOUND_BY_EXTRACTION
```

Depois aplicar política.

Checks críticos podem exigir:

- segunda extração;
- busca textual;
- revisão humana.

---

# 55. Política de consenso documental

Quando duas fontes informarem o mesmo valor:

```text
SUPPORTED
```

Quando divergirem:

```text
CONFLICTING
```

Quando somente uma fonte informar:

```text
SINGLE_SOURCE
```

Quando fonte obrigatória não informar:

```text
MISSING_REQUIRED_SOURCE
```

---

# 56. Tipos de pendência final

O usuário final deve ver poucos tipos:

```text
NÃO ATENDE
DOCUMENTO INCOMPLETO
DOCUMENTO AUSENTE
DADO AUSENTE
DIVERGÊNCIA
NÃO FOI POSSÍVEL VERIFICAR
REVISÃO DO ANALISTA
```

Internamente os códigos podem ser mais detalhados.

---

# 57. Linguagem das pendências

Toda pendência deve possuir:

```text
title
explanation
evidence_summary
required_action
normative_basis
```

Exemplo:

```text
Título:
ART incompleta para identificação da motobomba

Explicação:
A documentação apresentada informa vazão e pressão,
mas não permite identificar inequivocamente o equipamento.

Não localizados:
fabricante, modelo, rotação, diâmetro do rotor e potência.

Providência:
Apresentar ART complementar ou substitutiva contendo
os dados técnicos exigidos.
```

---

# 58. Gerador de texto

O texto final pode ser produzido:

1. por template determinístico; ou
2. por LLM somente para redação.

Se LLM:

- receber Finding estruturado;
- não adicionar requisito;
- não remover requisito;
- não alterar norma;
- saída validada.

Preferência inicial: template determinístico.

---

# 59. Testes

## Unitários

Cobrir:

- aplicação de Check;
- ausência;
- conflito;
- aplicabilidade;
- dependências;
- thresholds;
- consolidação;
- versionamento.

## Integração

Cobrir:

```text
processo → documentos → evidence → checks → findings
```

## Golden tests

Criar corpus com:

- ART completa;
- ART incompleta;
- RRT;
- memorial;
- laudo;
- documentos contraditórios;
- PDF digital;
- PDF escaneado;
- tabelas.

---

# 60. Corpus documental

Criar diretório separado de teste.

Nunca usar processo real no repositório.

Exemplo:

```text
tests/fixtures/documents/
```

Usar documentos sintéticos ou anonimizados.

---

# 61. Avaliação da IA

Criar conjunto cego.

Isso aproveita a futura linha `AI-01`.

Medir:

```text
classification_accuracy
field_precision
field_recall
semantic_match_accuracy
false_conflict_rate
missed_conflict_rate
human_review_rate
```

---

# 62. Métrica mais importante

Não medir apenas “acurácia da IA”.

Medir:

```text
pendências corretas / pendências emitidas
```

e:

```text
pendências reais encontradas / pendências reais existentes
```

O objetivo do sistema é qualidade da análise final.

---

# 63. Observabilidade

Logar:

```text
check_started
check_completed
check_failed
evidence_found
evidence_missing
conflict_detected
human_review_requested
AI_called
AI_reused
```

Não logar conteúdo sensível desnecessariamente.

---

# 64. Privacidade

Documentos técnicos podem conter:

- CPF;
- endereço;
- CREA/CAU;
- telefone;
- assinatura;
- dados pessoais.

Implementar:

- minimização de envio à IA;
- redaction quando possível;
- provider desligado por padrão;
- autorização explícita para serviços externos;
- política de retenção;
- log de envio.

---

# 65. Modo sem IA

O sistema deve continuar funcional sem LLM/Jev.

Nesse modo:

- extração manual;
- busca textual;
- checks determinísticos;
- revisão humana.

IA acelera.

IA não é dependência normativa.

---

# 66. Fallbacks

Cada etapa IA deve possuir fallback.

Exemplo:

```text
Jev indisponível
→ HUMAN_REVIEW
```

Nunca:

```text
Jev indisponível
→ assumir conformidade
```

---

# 67. Interface de configuração

Configurações:

```text
IA ativada
Provider LLM
Provider Jev
Budget máximo
Threshold profile
Permitir envio externo
```

---

# 68. Orçamento

Persistir `BudgetLedger`.

Reservas:

```text
budget_reservations
```

Antes da chamada:

```text
reserve
```

Após:

```text
commit actual
```

Falha:

```text
release
```

---

# 69. Ordem de implementação recomendada

## Fase 0 — estabilizar estado atual

Antes da refatoração:

- concluir build pendente;
- executar suíte completa;
- resolver commit;
- preservar v4;
- não perder arquivos existentes.

---

## Fase 1 — novo domínio

Construir:

- `Process`;
- `Check`;
- `Evidence`;
- `Finding`;
- novos statuses;
- schemas;
- migrations;
- testes.

**Não alterar UI principal ainda.**

Critério de aceite:

- um check sintético consegue gerar Finding reproduzível.

---

## Fase 2 — Plano de Verificação

Construir:

- catálogo;
- compilador;
- aplicabilidade;
- dependências;
- executor.

Migrar pequeno subconjunto:

- extintores;
- hidrantes.

Critério:

- dado um contexto, lista de checks é determinística.

---

## Fase 3 — adaptar CAD

Converter resultados atuais em `Evidence`.

Começar:

- extintores;
- portas;
- paredes;
- distâncias;
- saídas.

Critério:

- nova análise produz Finding sem depender de texto antigo.

---

## Fase 4 — Motor Documental mínimo

Suportar:

```text
ART
RRT
MEMORIAL
LAUDO
CURVA_BOMBA
```

Construir upload/versionamento/extração.

Critério:

- documento resulta em evidências localizáveis.

---

## Fase 5 — LLM estruturada

Implementar:

- provider;
- schemas;
- audit;
- cache;
- retry;
- fallback.

Começar com ART.

Critério:

- campos extraídos possuem localização na fonte.

---

## Fase 6 — Jev

Implementar:

- provider;
- question sets versionados;
- thresholds;
- semantic matching;
- ambiguity routing.

Critério:

- decisões abaixo do threshold viram revisão humana.

---

## Fase 7 — Crosscheck

Implementar:

- Claims;
- entity resolution;
- conflito;
- normalização de unidades;
- deduplicação.

Critério:

- ART e memorial conflitantes geram Finding único.

---

## Fase 8 — UI v2

Construir:

- tela de processo;
- documentos;
- resumo;
- Findings;
- evidências;
- revisão.

Critério:

- analista entende as pendências sem abrir detalhes técnicos.

---

## Fase 9 — relatórios

Criar:

- parecer curto;
- auditoria completa;
- PDF.

Critério:

- os dois relatórios refletem o mesmo snapshot.

---

## Fase 10 — retomar Anexo III

Depois da arquitetura acima:

- migrar Tabelas 2–4 para `NormativeRequirement`;
- implementar 5–21;
- gerar checks por sistema.

---

# 70. O que NÃO fazer

1. Não transformar a LLM em agente livre de análise.
2. Não permitir que Jev defina regra normativa.
3. Não usar um único status “REVIEW”.
4. Não continuar espalhando lógica normativa pela UI.
5. Não gerar pendências diretamente de prompts.
6. Não deixar ausência de extração significar ausência documental.
7. Não sobrescrever documentos.
8. Não apagar análises antigas.
9. Não misturar resultado técnico e texto.
10. Não seguir implementando Tabelas 5–21 antes das abstrações centrais.

---

# 71. Estrutura de pastas-alvo

```text
packages/
├── cad/
├── geometry/
├── normative/
│   └── coscip_normative/
│       ├── requirements/
│       ├── verification/
│       └── checks/
├── documents/
│   └── coscip_documents/
├── ai/
│   └── coscip_ai/
├── analysis/
│   ├── coscip_evidence/
│   ├── coscip_crosscheck/
│   └── coscip_findings/
└── reports/

apps/api/coscip_api/
├── processes/
├── documents/
├── analysis/
├── evidence/
├── findings/
├── reviews/
└── reports/

apps/web/src/features/
├── processes/
├── process-documents/
├── process-analysis/
├── findings/
├── evidence/
└── reviews/
```

Não é obrigatório mover imediatamente o código atual.

Pode-se usar adaptadores primeiro.

---

# 72. Compatibilidade com o sistema atual

Criar camada:

```text
legacy_analysis_adapter.py
```

Função:

```text
old result → Evidence + Finding
```

Somente para visualização histórica.

Não reescrever dados antigos.

---

# 73. Definition of Done da arquitetura v2

A arquitetura v2 estará funcional quando for possível:

1. criar um processo;
2. informar enquadramento;
3. anexar CAD;
4. anexar ART e memorial;
5. compilar plano de verificação;
6. extrair evidências da planta;
7. extrair evidências dos documentos;
8. executar checks;
9. cruzar documentos;
10. detectar ausência e divergência;
11. apresentar Findings simples;
12. revisar Findings;
13. gerar parecer;
14. gerar auditoria;
15. reproduzir toda a análise.

---

# 74. Critérios gerais de aceite

## Rastreabilidade

100% dos Findings devem apontar para:

- Check;
- evidência;
- norma;
- análise;
- versão.

## Auditabilidade

Toda decisão de IA deve possuir:

- provider;
- modelo;
- schema;
- input hash;
- output;
- confiança.

## Clareza

A tela principal não deve exigir conhecimento do pipeline.

## Segurança

Nenhum resultado inconclusivo pode virar “atende” por fallback.

## Reprodutibilidade

Relatório antigo deve continuar reproduzível mesmo se IA ou regra mudar.

---

# 75. Primeiros checks documentais recomendados

Para POC:

```text
DOC-GEN-001 — tipo documental
DOC-GEN-002 — documento legível
DOC-GEN-003 — identificação do responsável

ART-001 — número da ART
ART-002 — profissional
ART-003 — registro
ART-004 — escopo
ART-005 — sistemas abrangidos

HID-DOC-001 — responsabilidade pelo sistema
HID-DOC-002 — vazão
HID-DOC-003 — pressão
HID-DOC-004 — identificação completa da motobomba
HID-CROSS-001 — ART × memorial
HID-CROSS-002 — ART × curva
HID-CROSS-003 — memorial × curva
```

Esses checks formam um bom primeiro piloto porque refletem pendências reais do trabalho de análise.

---

# 76. Primeiro fluxo de POC recomendado

Usar processo sintético:

```text
1 planta DXF
1 ART
1 memorial
1 curva de bomba
```

Introduzir propositalmente:

- fabricante ausente;
- modelo divergente;
- mesma vazão;
- pressão divergente.

Resultado esperado:

```text
1 documento incompleto
2 divergências
1 dado confirmado
```

---

# 77. Relação com o projeto atual

Preservar integralmente:

- parser DXF;
- viewer;
- recortes;
- unidade;
- base normativa;
- hashes;
- DSL;
- revisão append-only;
- backup;
- análise histórica;
- Tabelas 2–4 já codificadas.

Refatorar a forma como os resultados são representados e orquestrados.

---

# 78. Próxima sessão — instrução recomendada

Ao iniciar a implementação desta arquitetura:

> Leia primeiro `proxima-sessao.md` e depois este documento.  
> Não altere nem descarte mudanças pendentes existentes.  
> Conclua a estabilização do v4 antes da refatoração.  
> Implemente a arquitetura v2 de forma incremental e aditiva.  
> Comece pelos modelos `Check`, `Evidence`, `Finding` e pelos três status separados.  
> Em seguida construa o compilador de Plano de Verificação.  
> Não continue as Tabelas 5–21 antes de existir essa base.  
> Não introduza Jev ou LLM antes de o fluxo determinístico `Check → Evidence → Finding` estar testado.  
> Toda mudança deve incluir teste, migração segura e atualização do `proxima-sessao.md`.

---

# 79. Decisão arquitetural resumida

A arquitetura definitiva deve seguir esta responsabilidade:

```text
COSCIP / NT
↓
define O QUE deve ser verificado

CÓDIGO
↓
define COMO a análise será executada

LLM
↓
LÊ e ESTRUTURA documentos

JEV
↓
RESOLVE classificações e ambiguidades probabilísticas

CAD / GEOMETRIA
↓
MEDE e LOCALIZA elementos

MOTOR DE REGRAS
↓
COMPARA evidências com requisitos

CONSOLIDADOR
↓
TRANSFORMA falhas em pendências claras

ANALISTA
↓
CONFIRMA, CONTESTA ou SOLICITA DADOS

RELATÓRIO
↓
COMUNICA o resultado
```

---

# 80. Resultado esperado para o analista

A implementação deve fazer com que o analista deixe de receber uma lista técnica extensa e passe a receber algo como:

```text
PROCESSO 21471

3 PENDÊNCIAS
2 DADOS AUSENTES
1 DIVERGÊNCIA
18 VERIFICAÇÕES SEM PENDÊNCIA

HIDRANTES

1. ART incompleta para identificação da motobomba
   Ausentes: fabricante, modelo, rotação e potência.
   Providência: apresentar ART complementar ou substitutiva.

2. Divergência de pressão
   ART: 73 mca
   Memorial: 65 mca
   Providência: compatibilizar a documentação.

SAÍDAS

3. Distância a percorrer não pôde ser concluída
   Motivo: camadas de parede não confirmadas.
   Providência: confirmar as layers correspondentes às paredes.
```

Ao clicar em cada item, o sistema abre todos os detalhes técnicos.

Essa é a meta da arquitetura v2: **mais capacidade interna, menos confusão externa**.
