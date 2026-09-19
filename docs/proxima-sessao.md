# Guia para a próxima sessão — Motor CAD/COSCIP

Atualizado em 19/09/2026 (continuação Codex; encerramento por consumo). **Este arquivo fica em `C:\Users\USER\Downloads\proxima-sessao.md`
e deve ser atualizado aqui mesmo**, sem criar outro; `motor-coscip/docs/proxima-sessao.md` é uma cópia sincronizada.
Plano de referência: `motor-coscip/docs/plano/00-plano-completo.html` (v2.0). Status por ID: `motor-coscip/docs/backlog.md`.

## Onde estamos

Fase de viabilidade, **Gate A pré-aprovado**. A planta real aparece na tela, o clique leva à origem no DXF, a unidade
é confirmada com referência medida, a medição foi conferida contra 1.460 cotas dos 5 projetos e o recorte de
pavimento funciona. Falta só o que depende de você (abaixo).

### Sessão anterior (Claude): 97 testes, lint, build, migração coerente

| Item | O que foi feito | Como foi verificado |
|---|---|---|
| Primeiro commit | `d53f65d` com 124 arquivos; sem dados reais; `ErrorReports/` e `*.tsbuildinfo` ignorados | revisão de nomes e conteúdo antes do commit |
| Importador 2.0 | worker gera `entities.jsonl` + índice binário + cena (`scene.bin`, `scene_ids.bin`, `scene.json`); supervisor confere hash de cada saída | testes e 5 plantas reais |
| Uma execução por DXF | cada desenho da revisão tem importação e confirmação próprias | teste com 2 desenhos na mesma revisão |
| CAD-02 | `POST /v1/drawings/{id}/unit-confirmation`: unidade + 2 pontos + medida real (desvio ≤ 2 %) + justificativa; novo quadro de coordenadas, novo snapshot, correção e auditoria; só a importação daquele desenho sai de `WAITING_INPUT` | 9 testes (referência errada, pontos iguais, acesso sem sessão, conflito de versão, reabrir app) |
| VIEW-01/02 | tela `/desenhos/:id`: camadas liga/desliga, zoom proporcional, clique → handle, caminho de instâncias, layer, bloco e hash do arquivo | navegador com a planta 9715 (1,28 mi de segmentos) |
| Medição | `POST /v1/drawings/{id}/measure`; ajusta ao vértice exato da entidade; ponto livre recebe incerteza do tamanho do pixel; opção de registrar | testes + navegador |
| PREP-01 | `POST /v1/drawings/{id}/floors` (retângulo) → novo snapshot; medida fora do recorte é recusada | testes |
| Migração 0002 | colunas de revisão/artefatos/cena em `drawings` e desenho em `floors`; subida e descida testadas | `alembic check` sem diferenças |
| Correções | backup não migra mais a base antes de copiar; leitor de números aceita ".91"; enquadramento não corta planta lateral; limite de upload 200 MB | testes |

### Corpus e pré-Gate A (detalhes em `Downloads\coscip-corpus\RELATORIO.md` e `gate_a.json`)

- As 5 plantas foram reimportadas no app com o importador 2.0 (projetos "Corpus …" no app).
- **Unidade confirmada em metros nas 5**, usando uma cota do próprio projeto como referência. Quem confirmou foi
  **o assistente, com sua autorização**; a justificativa gravada diz isso e pede revisão humana.
- Medição conferida contra as cotas: **1.452 de 1.460 conferem** dentro do arredondamento de exibição.
  As 8 divergências (todas no 41336) são do desenho: 2 cotas com texto diferente da geometria e 6 textos digitados
  à mão (prováveis alturas de instalação).
- **21778 × 21801**: mesmo empreendimento (mesmas ruas e cotas), ~45 % do conteúdo diferente → parecem dois
  protocolos do mesmo empreendimento, não uma revisão simples.
- **21471**: a planta está no Model; as pranchas PPCI têm notas, detalhes e 5 imagens OLE coladas (26,8 MB).
  O Model tem pouca arquitetura vetorial: pode ser que a base tenha vindo como imagem → conferir no AutoCAD.
- Backups: `C:\BackupsMotorCoscip` (antes da migração 0002 foi feito backup da base 0001). Mesmo SSD.

## O que falta para fechar o Gate A (com você)

1. **Revisar as 5 confirmações de unidade** feitas pelo assistente: abrir cada planta no app e aceitar (ou reconfirmar).
2. **Uma medida real independente** em pelo menos um projeto (medida de campo ou de documento fora do DXF),
   conferida com a ferramenta Medir.
3. Dizer se 21778 e 21801 são o mesmo processo (só importa para o teste de histórico).
4. Abrir o 21471 no AutoCAD e dizer se a base arquitetônica é imagem.
5. Pendrive/HD externo para backup; responsável pela validação da NT 2-01 (só na fase de regras).

## Continuação Codex — implementado em 19/09/2026

O desenvolvimento foi retomado com 94% disponíveis na janela de cinco horas e 100% na semanal.
Na consulta de encerramento, a janela de cinco horas estava em **95% consumidos / 5% restantes**;
a semanal em 14% consumidos / 86% restantes. A leitura anterior indicava 15% restantes;
o limite compartilhado saltou durante as verificações. Nenhuma funcionalidade adicional deve
ser iniciada nesta sessão. O usuário definiu o ponto de parada em **10% restantes**.
Este guia principal foi atualizado no próprio local, e somente sua cópia já existente em docs
foi sincronizada. Não foi criado outro guia na pasta de trabalho do Codex nesta continuação.

### Entregas desta continuação

- **Revisão de unidades:** menu “Revisar unidades” (`/#/unidades`), lista paginada com projeto,
  referência, conta que registrou, justificativa e formulário de aceitação. Requer nome do revisor,
  justificativa e conferência explícita. Aceitação append-only vinculada ao quadro e à confirmação;
  reconfirmar a unidade torna necessária outra revisão. Nenhuma unidade do corpus real foi aceita
  pelo Codex nesta sessão; a operação pelo navegador foi feita apenas em base sintética separada.
- **Classificação assistida:** na planta, selecionar uma entidade mostra sugestões por layer/bloco
  e permite confirmar classe ou nome individualmente, com pavimento, origem, autoria e justificativa.
  Cada alteração cria snapshot e correção auditada. Inclui porta, abertura, saída, extintor, ambiente,
  parede, escada e obstáculo. Sugestão não vira confirmação automaticamente. Conflitos são mostrados.
- **Persistência da preparação:** snapshots derivados preservam propriedades e geometrias anteriores.
  Mudança de quadro de coordenadas marca propriedades e geometrias dependentes para revisão.
  Os registros semânticos desta etapa ficam no JSON do snapshot, ainda sem popular as tabelas
  relacionais `elements/facts` (integração CAD-04 posterior).
- **Recorte poligonal:** seleção de até 256 vértices, validação de polígono simples e não vazio;
  medições rejeitam pontos fora e segmentos que cruzam o exterior de recortes côncavos.
- **Contornos e áreas:** ferramenta “Contorno e área”, novo contorno ou redesenho mantendo histórico,
  área, perímetro, incerteza e origem dos pontos. Contorno precisa caber no pavimento. Contornos
  ainda são registros próprios, sem associação obrigatória a um elemento semântico SPACE.
- **Larguras de portas:** ferramenta com medições separadas de vão, folha e largura livre, vinculadas
  a uma entidade classificada como porta. Não deduz largura livre a partir da folha ou do vão.
- **Reenquadramento:** botão “recalcular enquadramento” recompõe a vista a partir dos buffers da
  cena; efeito apenas visual/local, sem regravar o artefato original.
- **Relatório HTML de preparação:** emissão pela tela Preparação, ID próprio, conteúdo imutável,
  SHA-256, desenhos, referências, recortes, propriedades, áreas, larguras e pendências. Texto escapado
  e política restritiva de conteúdo. Declara expressamente que não é uma avaliação normativa.
- Tela Preparação passou a mostrar desenhos e recursos disponíveis, em vez dos placeholders antigos.

### Verificações e ambiente de teste

- Base anterior: **97 testes passaram** nesta sessão, antes das novas alterações.
- Novos testes de integração: **9 passaram**, incluindo revisão obsoleta, preservação de versões,
  acesso entre organizações, recorte côncavo, áreas de referência, dimensões distintas, reabertura,
  extintor em curva e relatório com hash, imutabilidade e escape de HTML.
- Suíte completa final: **106 testes passaram em 120,35 s**, com dois avisos de depreciação das dependências Starlette/httpx/AnyIO; nenhuma falha.
- Lint (`ruff check . --no-cache`) e TypeScript (`npm run typecheck`) passaram.
- Build de produção passou com a configuração Vite carregada diretamente pelo Node. O comando
  padrão `npm run build` falha nesta sessão no carregador esbuild com “Acesso negado” ao percorrer
  uma pasta ancestral. Alternativa executada com sucesso, na raiz do projeto:
  `node --experimental-strip-types --input-type=module -e "import config from './apps/web/vite.config.ts'; import {build} from 'vite'; await build({...config,configFile:false,root:'apps/web'});"`
- Pytest padrão não acessou a pasta temporária antiga. Usar `-p no:cacheprovider --basetemp` com
  uma pasta NOVA, exclusiva para testes, em uma área de trabalho liberada. Nunca apontar basetemp
  para dados reais: pytest pode limpar essa pasta.
- Navegador: revisão de unidade, seleção → origem, confirmação de propriedade, emissão de relatório
  e apresentação do HTML foram conferidos com uma planta sintética. Recortes/áreas/larguras foram
  testados pela API; conferir também esses fluxos completos visualmente na próxima sessão.
- Nenhuma migração nova. A base real do usuário não foi modificada nesta continuação.
- **Alterações ainda sem commit**. Último commit anterior: `3187435`; revisar o diff e fazer o próximo
  commit local após concluir a revisão indicada abaixo. Não publicar dados reais.

## Próximos passos técnicos, em ordem

1. Consultar consumo antes de retomar. Ler este guia e `docs/backlog.md`; preservar o trabalho
   não commitado desta sessão. Rever diff, repetir somente verificações justificadas e fazer commit.
2. Completar a revisão da preparação: testar visualmente recorte poligonal, redesenho de contorno
   e larguras; verificar invalidação de largura quando a classe da porta é alterada; associar
   contornos a ambientes semânticos, e consolidar elementos/instâncias/atributos em CAD-04.
3. Conferir inclusão espacial das entidades curvas e polilinhas com bulge. Para curvas antigas sem
   vértices no inventário, a classificação usa caixa conservadora da cena, com método registrado
   (`conservative-scene-bounds`), apenas para inclusão no recorte, nunca para áreas/larguras.
   Rever os demais casos de polilinha; aproximar visualmente não equivale a geometria analítica.
4. Melhorar classificação em lote e dicionário por projeto (PREP-04). O endpoint de candidatos
   existe, mas a confirmação atual é por entidade selecionada na planta, propriedade por propriedade.
5. Verificar inclusão do template HTML no empacotamento distribuível (setuptools/package-data).
   Relatório atual é de PREPARAÇÃO. REP-01 completo depende da execução de análises normativas;
   PDF, relatório de resultados e cobertura normativa continuam pendentes.
6. Fechar o Gate A com o usuário: revisão das confirmações reais e medida independente. Não marcar
   essas verificações humanas como feitas com base nos testes sintéticos.
7. GEO-04: conexões, obstáculos e percursos em um pavimento. REG-02: matriz de cobertura da NT 2-01
   com responsável técnico e fontes oficiais verificadas; sem publicar regra normativa não homologada.

Melhorias anteriores ainda pendentes: TEXT/MTEXT no viewer, desempenho das curvas do 9715,
seleção/destaque sem percorrer todos os segmentos. Não reimportar o corpus sem necessidade.

## Estado do ambiente

- Código: `C:\Users\USER\Downloads\motor-coscip`. Commits anteriores: `d53f65d`, `2aa8572`, `3187435`; continuação Codex ainda não commitada.
- Python: `.venv` do projeto (3.12). Interface compilada em `apps/api/coscip_api/static`.
- Dados do app: `%LOCALAPPDATA%\MotorCoscip` (base na migração 0002; 5 projetos "Corpus …" com cena e unidade confirmada,
  mais 2 projetos antigos de teste sem cena).
- Preview no navegador do Claude: entrada `motor-coscip` em `Downloads\.claude\launch.json` (porta 8765); o token de
  abertura aparece no log na linha `Abrir:` e é de uso único (um script que usa o token impede o navegador de usá-lo;
  reinicie o servidor para obter outro).

## Cuidados que já custaram tempo

- No Windows, `os.kill(pid, 0)` **encerra** o processo; usar `_pid_alive` do launcher.
- O `python.exe` do venv é um lançador: medir memória somando os processos filhos (`psutil`).
- `accoreconsole` com `Start-Process -Wait` pode travar; invocar direto com `&`.
- O estilo de cota padrão do ezdxf usa `DIMLFAC=100`; em testes, fixar o fator explicitamente.
- Migração: `PRAGMA` antes da transação do Alembic impedia gravar a versão (corrigido); `job_queue` fica fora do ORM
  (`include_object` em `env.py`); chaves estrangeiras em batch precisam de nome.
- Backup antes de atualizar: `coscip_api.cli backup` não migra a base.
- Cotas: texto digitado não é medida; números sem zero inicial (".91") são comuns.
- Dados reais nunca entram no repositório; nuvem para backup só com autorização do usuário (OneDrive recusado por ora).

## Comandos úteis

```powershell
.venv\Scripts\python -m pytest              # 97 testes (~80 s)
.venv\Scripts\ruff check .
npm run build
scripts\start\start.ps1
.venv\Scripts\python -m coscip_api.cli backup
.venv\Scripts\python -m coscip_api.cli benchmark C:\Users\USER\Downloads\coscip-corpus\dxf
```

## Frase para abrir a próxima sessão

> Leia `C:\Users\USER\Downloads\proxima-sessao.md`, consulte o consumo e retome pelos próximos passos técnicos. Preserve as alterações não commitadas. Ao restarem 10% em qualquer janela, encerre com margem e atualize este mesmo arquivo e a cópia já existente em docs; não crie outro guia.

