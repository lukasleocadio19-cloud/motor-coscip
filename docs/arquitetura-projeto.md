# Motor CAD/COSCIP — modo PROJETO (arquitetura)

Documento de arquitetura, não registro: estado, histórico e pendências continuam só em
[`proxima-sessao.md`](proxima-sessao.md). Iniciado em 09/11/2026.

## 1. Objetivo

O motor nasceu para **conferir** projetos (planta → evidência → achado). O modo projeto faz o
caminho inverso: a partir dos dados da edificação, **dimensiona** as medidas de segurança, gera o
**memorial de cálculo**, **desenha** as plantas com a simbologia oficial e os cortes esquemáticos, e
usa o próprio motor de conferência para verificar o que desenhou.

Meta: um rascunho completo de Projeto de Segurança Contra Incêndio e Pânico (PSCIP) que um
responsável técnico revisa e assina. O motor **não substitui** o profissional habilitado: sem
ART/RRT, sem homologação das regras e sem conferência humana, nada tem valor normativo.

## 2. Princípios (herdados do projeto)

1. **Todo número da norma tem citação conferida.** Os parâmetros ficam em
   `normative/projeto/parametros.yaml`, cada um com documento, item e termos que são procurados no
   texto ingerido ao carregar. Citação que não confere → o parâmetro não é usado e o cálculo é
   recusado (não há valor "de memória").
2. **O que a norma não fixa é premissa do projetista**, listada à parte no memorial: constante da
   fórmula de Hazen-Williams (imagem no texto ingerido), C da mangueira, comprimentos equivalentes,
   rendimento da bomba. Nenhuma premissa entra escondida.
3. **Dados da edificação vêm do usuário.** Ocupação, áreas, alturas, traçado da tubulação: a IA
   pergunta, não supõe.
4. **Ausência não vira dispensa.** Tabela não carregada responde "fora do escopo", nunca "nada
   exigido".
5. **Projetar e conferir são o mesmo motor.** O que o modo projeto desenha é relido pelo leitor de
   plantas; distâncias a percorrer (extintor, hidrante, acionador, saída) só são dadas como
   atendidas depois de `analisar_planta`.

## 3. Componentes

| Camada | Onde | Papel |
|---|---|---|
| Parâmetros | `normative/projeto/parametros.yaml` | valores das NTs com citação; Anexo A da NT 2-08 linha a linha |
| Cálculo | `packages/design/coscip_design` | `params` (carrega e confere), `memorial` (passos, premissas, pendências), `extintores`, `saidas`, `hidrantes`, `sistemas` |
| Desenho | `apps/mcp/coscip_mcp/autoria.py`, `simbologia.py` | operações de planta, catálogo NT 1-03/2-05, legenda, corte esquemático |
| Conferência | `packages/analysis`, `packages/normative` | leitura do DXF, percursos, Plano de Verificação (já existia) |
| Ferramentas | `apps/mcp/coscip_mcp/server.py` | MCP: `enquadrar_edificacao`, `dimensionar_*`, `requisitos_iluminacao_alarme`, `salvar_memorial`, `desenhar_planta` (com `corte`) |

`coscip_design` não depende do MCP: a API e o app web podem chamá-lo depois.

## 4. Fluxo de um projeto

```
enquadrar_edificacao      divisão + ATC + pavimentos → risco (NT 1-04), medidas exigidas
        │                 (Decreto 42/2018, Anexo III), limite até a saída (NT 2-08, Anexo C)
        ▼
dimensionar_extintores    NT 2-01: quantidade por pavimento, tipo, capacidade
dimensionar_saidas        NT 2-08: população, unidades de passagem, larguras, portas, escadas
dimensionar_hidrantes     NT 2-02: sistema, RTI, perdas, altura manométrica, bomba
requisitos_iluminacao_alarme  NT 2-06 / NT 2-07: o que as NTs fixam
        │                 cada cálculo devolve memorial com base normativa, premissas e pendências
        ▼
criar_planta → desenhar_planta   salas, paredes, portas, símbolos nas quantidades calculadas,
        │                        legenda e corte esquemático (esquema vertical)
        ▼
confirmar_unidade → definir_pavimentos → analisar_planta   percursos reais e Plano de Verificação
        │                 pendência → ajustar o desenho e analisar de novo
        ▼
salvar_memorial           Markdown com todos os cálculos da sessão
```

## 5. O que existe (fase P1, 09/11/2026)

- **Extintores (NT 2-01):** unidades pela área máxima por risco, mínimo de dois, exceção de 50 m²,
  capacidade mínima (Tabelas 1 e 2), sobre rodas e 4-A no risco grande, instalações especiais.
- **Saídas (NT 2-08):** população pelo Anexo A (área, dormitórios, leitos, vagas), N = P/C,
  larguras mínimas, vãos de porta, escadas pelo pavimento de maior população, duas saídas e barra
  antipânico no grupo F, duas escadas a partir de 15 pavimentos.
- **Hidrantes (NT 2-02):** sistema pela Tabela 1, RTI (redação de 2020), Hazen-Williams por trecho
  com comprimento equivalente, velocidades (2, 3 e 5 m/s), perda na mangueira, altura manométrica
  total no modelo do Anexo B, pressão máxima de 100 mca, potência estimada, hidrante de recalque,
  casa de máquinas e abrigos.
- **Iluminação e alarme:** só o que as NT 2-06 e 2-07 fixam (locais, autonomia, 30 m até o
  acionador).
- **Corte esquemático:** pavimentos empilhados com níveis, cota total, prumada de hidrantes,
  reservatório com a RTI e registro de recalque. Sai das alturas informadas.

- **Enquadramento completo (09/11/2026):** Anexo III, Tabelas 2 a 32, com as observações de cada célula e o roteiro de cada medida (`medidas.yaml` → `como_tratar`).
- **Skill** `skills/projetar-pscip-cbmerj`: conduz o Claude pelo projeto inteiro, incluindo as medidas sem cálculo (ler a NT e registrar).

## 6. Limites conhecidos (o que falta para "o projeto todo")

| Falta | Por quê | Fase |
|---|---|---|
| Conferência do Anexo III por responsável técnico | as Tabelas 5 a 32 foram conferidas no PDF oficial pelo assistente em 09/11/2026 (registro com resumo da leitura em `normative/projeto/anexo-iii.yaml`); falta a conferência de um profissional | sempre |
| Ocupação mista | o enquadramento trata uma ocupação por vez | P2 |
| Detalhamento da escada (NT 2-08) | o tipo (enclausurada ou não) já vem nas observações do Anexo III; o Anexo B e o detalhamento são lidos na NT | P2 |
| Conjunto de pressurização (NT 2-04) | quantidade e tipo de bombas, partida, NPSH | P2 |
| Tabela de comprimentos equivalentes | a NT não traz; hoje o projetista informa a soma por trecho | P2 |
| Sinalização (NT 2-05) | quantidade e posição das placas, dimensão pela distância de visualização (Tabela 7) | P2 |
| Sprinklers (NT 2-03) | cálculo hidráulico por área de operação | P3 |
| Iluminação e detecção por norma ABNT | NBR 10898 e NBR 17240 não estão na base (direito autoral: não podem ser copiadas para o repositório) | P3 |
| SPDA, brigada, compartimentação, TRRF, CMAR, controle de fumaça, acesso de viaturas | NT 2-10 a 2-20: nada calculado | P3 |
| Riscos específicos e ocupações especiais | NTs dos grupos 3, 4 e 5 | P4 |
| Posicionamento automático de equipamentos | hoje a IA posiciona e o motor confere; falta um otimizador sobre a grade de percursos | P3 |
| Corte real | uma planta 2D não tem altura; corte de verdade exige modelo 3D ou dados por ambiente | P4 |
| Pranchas (folha, carimbo, Quadro Resumo, escala) e PDF | hoje sai DXF em modelspace e memorial em Markdown | P2 |
| Isométrico da rede de hidrantes | só o esquema vertical | P3 |
| Homologação | regras e parâmetros em rascunho; sem responsável técnico | sempre |

## 7. Bibliotecas

Nenhuma dependência nova nesta fase: `ezdxf` (DXF), `shapely` (geometria), `pydantic` (entradas),
`pyyaml` (parâmetros). Candidatas para as próximas fases, a decidir quando o caso chegar:

- **PDF das pranchas:** o backend de desenho do `ezdxf` com `PyMuPDF` ou `matplotlib`.
- **Rede hidráulica malhada (sprinklers, anéis):** resolver por Hardy-Cross próprio ou `wntr`
  (EPANET); para rede ramificada o cálculo por trechos atual basta.
- **Modelo 3D / IFC para cortes reais:** `ifcopenshell`.

## 8. Como estender

1. Ler o item na NT (`consultar_norma`) e, se for tabela com célula mesclada, conferir na imagem.
2. Acrescentar o parâmetro em `parametros.yaml` com `fonte` (`quote` ou `linha`).
3. Rodar `pytest tests/unit/test_design.py`: o primeiro teste falha se a citação não conferir.
4. Usar o parâmetro no cálculo com `params.get(...)` e registrar no memorial (`m.passo(..., base=[p])`).
5. O que não vier da norma entra em `m.premissas`; o que ficar em aberto, em `m.pendencias`.
