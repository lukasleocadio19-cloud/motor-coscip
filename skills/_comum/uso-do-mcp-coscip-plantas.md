# Uso do MCP `coscip-plantas` (motor COSCIP) na análise

Referência comum (plano de correção, F8). Quando o processo traz **planta vetorial** (DXF ou
DWG), a leitura da planta e as medições do Grupo 2 vêm do motor, não da imagem. Sem planta
vetorial (só PDF), valem as regras de leitura visual de
`protocolo-leitura-pranchas.md` / da skill de grupo.

## Quando usar

- Há `.dxf` ou `.dwg` no dossiê (o `inventariar_dossie.py` lista; ele **não** lê a planta).
- O MCP está conectado (ferramentas `abrir_planta`, `ver_planta`, …). Se não estiver, dizer
  ao usuário que o servidor não está disponível e seguir pela leitura do PDF, registrando que
  a medida foi manual.

## Fluxo obrigatório

1. `abrir_planta(caminho)` → camadas, símbolos por classe, blocos não reconhecidos, unidade
   provisória, **balanço de reconhecimento**.
2. `ver_planta` / `listar_textos` / `listar_simbolos` para localizar títulos, pavimentos, cotas.
3. `confirmar_unidade` **somente** com medidas confirmadas pelo usuário (ou cotas legíveis que
   ele aceite): **duas** referências em direções diferentes (ex. uma cota horizontal e uma
   vertical); o motor bloqueia se forem paralelas ou discordarem mais que 0,5 %. O `$INSUNITS`
   do arquivo errou em 5 de 5 projetos reais: nunca supor.
4. `definir_pavimentos` (janelas/polígonos em metros, lidos dos títulos da planta).
5. `analisar_planta` com o enquadramento do processo (ocupação, ATC, pavimentos, altura,
   sistemas exigidos, dados do Anexo C da NT 2-08).
6. Blocos não reconhecidos em camada de segurança: `classificar_blocos` **com confirmação do
   usuário**, e analisar de novo.

## GATE-0 da planta (antes de qualquer achado de medida)

A matriz só recebe achados de contagem ou distância do motor quando **as duas** condições
valem; senão o achado é `UNDETERMINED` / `DATA_MISSING` e a pendência é a condição:

- unidade confirmada (`confirmar_unidade` feito);
- balanço de reconhecimento completo (`balanco_reconhecimento.completo = true`): nenhum
  bloco não reconhecido em camada de segurança e nenhum XREF pendente.

## Como levar para a matriz

- Os achados do motor saem no esquema comum [`achado.schema.json`](achado.schema.json)
  (`analisar_planta` → `achados`, ou `coscip_api.cli v2-findings <id> --out`): entram na
  matriz consolidada **sem tradução**, com `origem: motor`.
- Os três status (`compliance_status`, `evidence_status`, `review_status`) são copiados como
  estão: nunca fundir; `UNDETERMINED` não vira "conforme" nem "não conforme".
- Medida com incerteza que atravessa o limite fica inconclusiva: citar valor ± incerteza e
  pedir a conferência; não arredondar a favor de nenhum lado.
- "Critério adotado" (interpretação registrada, ex.: 2 extintores por pavimento) aparece como
  tal no bilhete; não é "a NT exige".
- Nada do motor tem valor normativo até a homologação das regras e dos checks.

## Citação

`consultar_norma` do MCP usa a mesma base de textos que o motor e as skills
(`normative/fontes`): é alternativa ao `localizar_item.py` do bilhete.
