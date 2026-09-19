# Guia para a próxima sessão

Atualizado em 19/09/2026. Plano de referência: [`docs/plano/00-plano-completo.html`](plano/00-plano-completo.html) (v2.0).
Status detalhado por ID: [`docs/backlog.md`](backlog.md).

## Conferência e encerramento desta sessão — 19/09/2026 (Codex)

### Limite de consumo

O usuário pediu continuidade do desenvolvimento e atualização deste guia quando restassem 15%.
Na consulta inicial, a janela semanal já estava com **99% consumidos / 1% restante**;
a janela de cinco horas estava com **1% consumido / 99% restante**. Portanto, o ponto de parada
já havia sido ultrapassado no limite semanal. A sessão foi limitada à conferência e à preparação
desta passagem de trabalho; nenhuma funcionalidade nova foi implementada.
Na próxima sessão, consultar os limites novamente antes de iniciar. Considerar 15% **restantes**
em qualquer uma das duas janelas como ponto de encerramento e reservar margem para atualizar este guia.
Não usar o saldo de créditos como justificativa para ignorar o ponto de parada definido pelo usuário.

### O que foi efetivamente conferido agora

- Lidos este guia, `docs/backlog.md`, `CLAUDE.md`, configurações do projeto e arquivos centrais
  da API, do diagnóstico e do viewer; consultados o estado e o histórico Git.
- Confirmado: a branch `master` ainda não possui commits. Há arquivos preparados para commit,
  arquivos preparados com alterações posteriores e arquivos novos não rastreados.
- Confirmado: `coordinate_frames.unit_confirmed` existe, mas não foi encontrado o endpoint de
  confirmação de unidade. O Diagnóstico mostra a sugestão, sem formulário de confirmação.
- Confirmado: `GET /v1/models/{id}/scene` e a consulta de origem dos elementos existem como rotas,
  mas ainda respondem como não implementadas (VIEW-01/02).
- Confirmado: `GET /v1/artifacts/{id}/content` já possui implementação; reutilizá-la e verificar
  seu funcionamento com os novos artefatos de cena, sem tratar esse endpoint como tarefa do zero.
- Confirmado: `packages/viewer` já contém buffers por camada, pan, zoom e controle de visibilidade;
  ainda falta integrar a cena real e implementar seleção com vínculo à origem.
- Confirmado: a API de criação de análises verifica `model.quality.units_confirmed`. A confirmação
  deverá manter coerência entre esse estado e o quadro de coordenadas; alterar apenas a coluna
  `unit_confirmed` não completa o fluxo.
- **Testes, lint e build não foram reexecutados nesta sessão.** Os 79 testes e os resultados
  positivos citados abaixo são registros da sessão anterior, não uma validação nova.
- Nenhum commit, mudança no código, validação normativa ou aprovação do Gate A foi realizado.

### Retomada executável, quando houver limite disponível

1. Consultar consumo, reler este guia e conferir alterações concorrentes no Git.
2. Revisar o conteúdo do primeiro commit antes de gravá-lo: há `.claude-launch-tmp` e
   `apps/web/tsconfig.tsbuildinfo` preparados, além de `ErrorReports/` não rastreado. Conferir
   arquivos locais/gerados e informações privadas; preservar o trabalho existente e manter o
   corpus fora do repositório. O pedido do usuário já autoriza executar as tarefas do guia,
   inclusive o commit local, após essa revisão; não é necessária uma confirmação genérica extra.
3. Implementar CAD-02 completo: contrato/API, validação da referência (pontos/entidades e medida
   real positiva e finita), justificativa, persistência e confirmação explícita na interface.
   Conferir o vínculo desenho/revisão/projeto, a proteção de acesso e a coerência entre quadro
   de coordenadas, qualidade do modelo, snapshots e estado da execução. Em revisão com vários
   desenhos, confirmar um deles não deve liberar os demais. Não apagar o histórico da importação.
4. Verificar CAD-02 com testes que cubram referência inválida, acesso indevido, bloqueio antes da
   confirmação, liberação após a confirmação e persistência depois de reabrir o app.
5. Implementar VIEW-01/02: cena produzida pelo worker e publicada como artefato imutável com hash,
   renderização no viewer existente, seleção vinculada à origem e controle de camadas. Registrar
   o erro de discretização de curvas. Usar o corpus 9715 para verificar desempenho.
6. Implementar PREP-01 com recorte de pavimento persistido em novo snapshot e limitar as medidas
   ao recorte. Só então executar o Gate A com uma medida real informada pelo usuário.
7. Rodar os testes do projeto, lint e build; atualizar `docs/backlog.md` e este guia com resultados
   realmente observados. Registrar falhas e pendências sem declarar concluído o que não foi verificado.

As medidas reais, a relação entre 21778/21801, o espaço correto do 21471, o dispositivo externo
para backup e o responsável pela homologação continuam dependendo de informações ou recursos
do usuário. Não inventar esses dados nem transformar sugestões de unidade em confirmação humana.

## Onde estamos

Fase de **viabilidade** (semanas 1–4 do plano). A fundação local está pronta; o **Gate A** ainda não
foi passado: falta mostrar a planta na tela e conferir uma medida real de ponta a ponta.

### O que já funciona (registro anterior: 79 testes passando, lint e build ok)

| Área | O que existe |
|---|---|
| App local | Launcher em `127.0.0.1` com porta livre, token de abertura de uso único, sessão por cookie, CSRF, Host/Origin validados |
| Banco | SQLite (WAL, `synchronous=FULL`) com migração Alembic `0001` (~37 tabelas + fila) |
| Projetos | Projeto → revisão → upload em partes com SHA-256 → selagem com manifesto imutável |
| Importação DXF | Fila persistente + worker em processo separado (sem banco, sem chaves, sem pasta do usuário); só a tentativa vigente publica; retomada após queda |
| Leitor DXF | Entidades com identidade de origem (arquivo + handle + caminho de instâncias), blocos aninhados/espelhados, matriz de suporte, contagem por prancha, aviso de proxies |
| Unidade | Sugestão pelas cotas (`coscip_cad.unit_evidence`); **toda** importação termina em `WAITING_INPUT / DRAWING_UNIT_UNCONFIRMED` |
| Geometria | Unidades, transformações 4×4, tolerâncias experimentais, comparação com incerteza, grafo de pavimento |
| Regras | DSL fechada em YAML, cinco estados, regra artificial `DEMO_DOOR_WIDTH_MIN` (`TEST_ONLY`) |
| IA | Interfaces e reserva de orçamento; **desligada**, sem chave cadastrada |
| Backup | Cópia consistente + verificação por hash + restauração em pasta separada (testada) |
| Interface | Início, Projetos, Revisões, Upload, Diagnóstico (mostra unidade sugerida e pranchas), Operação, Configurações; demais telas mostram o ID do backlog |
| Benchmark | `python -m coscip_api.cli benchmark <pasta>` roda o worker real e mede tempo/memória |

### Corpus real (fora do repositório)

- Pasta: `C:\Users\USER\Downloads\coscip-corpus` — `dxf/`, `originais/`, `RELATORIO.md`, `manifesto.json`, `benchmark.json`.
- 5 projetos autorizados: 21471, 21778, 21801, 41336 (DWG convertidos pelo AutoCAD 2027) e 9715 (DXF do projetista).
- Conversão: `accoreconsole.exe` + `DXFOUT` 2018, precisão 16 — ver [`runbooks/dwg-para-dxf.md`](runbooks/dwg-para-dxf.md). **Nunca** usar o ODA File Converter (licença).
- Medições: 7–21 s e 185–271 MB por arquivo no PC (i7-3770, 16 GB). Hardware suficiente.

### Achados que mudaram o motor

1. `$INSUNITS` errado em **5 de 5** desenhos (todos em metros) → unidade sempre exige confirmação.
2. 21471 tem geometria nas pranchas `PPCI 1/2`; a análise lê só o Model.
3. Model space com várias plantas lado a lado → recorte do pavimento (PREP-01) é obrigatório antes de medir.
4. 21778 e 21801 são quase idênticos → provavelmente revisões do mesmo projeto.
5. Tamanho em MB não prediz custo; limitar por entidades expandidas.

### Estado do ambiente

- Código: `C:\Users\USER\Downloads\motor-coscip` — repositório git **sem nenhum commit** ainda.
- Python: `.venv` do projeto (3.12). Frontend compilado em `apps/api/coscip_api/static`.
- Dados do app: `%LOCALAPPDATA%\MotorCoscip` (projetos "Loja Centro - teste" e "Corpus 41336_655959").
- Backup: `C:\BackupsMotorCoscip` — **mesmo SSD, provisório** (escolha do usuário; OneDrive recusado por ora).
- Preview no navegador do Claude: entrada `motor-coscip` em `Downloads\.claude\launch.json` (porta 8765);
  o token de abertura aparece no log na linha `Abrir:`.

## Próximos passos, em ordem

### 1. Fazer o primeiro commit
Nada foi commitado. Conferir `git status`, revisar arquivos locais/gerados e dados privados e fazer o primeiro commit local. O usuário autorizou executar as tarefas deste guia em 19/09/2026; preservar alterações existentes e não publicar em serviço remoto sem solicitação.

### 2. Confirmação de unidade (CAD-02)
- Endpoint `POST /v1/drawings/{id}/unit-confirmation` com unidade escolhida + medida de referência
  (duas entidades/pontos e o valor real) + justificativa; grava `coordinate_frames.unit_confirmed`.
- Tela no Diagnóstico: mostrar a sugestão como pré-seleção, **exigir** a confirmação explícita.
- Critério: sem confirmação, nenhuma medida/análise; com confirmação, a execução sai de `WAITING_INPUT`.

### 3. Planta na tela com seleção → origem (VIEW-01/02, POC-06)
- Gerar a cena no worker: segmentos por layer (LINE, LWPOLYLINE, ARC/CIRCLE discretizados com erro registrado),
  relativos a uma origem local; gravar como artefato imutável com checksum.
- Implementar `GET /v1/models/{id}/scene` e reutilizar `GET /v1/artifacts/{id}/content`, que já existe; o viewer (`packages/viewer`) já desenha por buffers.
- Seleção: índice espacial → servidor devolve handle, caminho de instâncias, layer e bloco.
- Camadas liga/desliga (sem excluir da análise). Testar com o 9715 (134 mil entidades expandidas).

### 4. Recorte de um pavimento (PREP-01)
Retângulo/polígono desenhado na planta; medidas só dentro do recorte; novo snapshot.

### 5. Gate A (POC-08)
Com o **usuário**: abrir um DXF do corpus, selecionar um elemento, medir e comparar com uma medida conhecida,
reencontrar a origem após fechar e reabrir o app. Registrar o resultado no `RELATORIO.md` do corpus.

### Depois do Gate A
Contornos e portas assistidos (PREP-02/03, GEO-02/03), percursos em um pavimento (GEO-04), matriz de
cobertura da NT 2-01 (REG-02) e relatório HTML/PDF (REP-01/02). IA só depois do núcleo funcionando.

## Pendências do usuário

| Item | Por quê |
|---|---|
| **Uma medida real conhecida por projeto** (ex.: "porta de entrada do 41336 = 0,90 m") | Conferir a medição no Gate A |
| Dizer se 21778 e 21801 são revisões do mesmo projeto | Usar no teste de histórico |
| Dizer qual espaço do 21471 tem a planta a analisar (Model ou pranchas PPCI) | Definir o recorte |
| Pendrive/HD externo para backup | O backup atual está no mesmo SSD |
| Responsável pela validação da NT 2-01 | Só necessário na fase de regras reais |

## Cuidados que já custaram tempo

- No Windows, `os.kill(pid, 0)` **encerra** o processo; usar `_pid_alive` do launcher.
- O `python.exe` do venv é um lançador: medir memória somando os processos filhos (`psutil`).
- `accoreconsole` com `Start-Process -Wait` pode travar; invocar direto com `&`.
- O estilo de cota padrão do ezdxf usa `DIMLFAC=100`; em testes, fixar o fator explicitamente.
- Migração: o `PRAGMA` antes da transação do Alembic impedia gravar a versão (corrigido em `env.py`).
- Dados reais nunca entram no repositório; nuvem para backup só com autorização do usuário.

## Comandos úteis

```powershell
.venv\Scripts\python -m pytest              # testes
.venv\Scripts\ruff check .                  # lint
npm run build                               # interface (tsc estrito + vite)
scripts\start\start.ps1                     # abrir o app
.venv\Scripts\python -m coscip_api.cli benchmark C:\Users\USER\Downloads\coscip-corpus\dxf
scripts\backup\backup.ps1                   # backup no destino cadastrado
```

## Frase para abrir a próxima sessão

> Leia `docs/proxima-sessao.md` do motor-coscip e continue pelos próximos passos: confirmação de unidade
> e planta na tela com seleção, até o Gate A.

