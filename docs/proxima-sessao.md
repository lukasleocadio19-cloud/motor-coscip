# Guia para a próxima sessão — Motor CAD/COSCIP

Atualizado em 19/09/2026 (sessão da tarde, Claude). **Este arquivo fica em `C:\Users\USER\Downloads\proxima-sessao.md`
e deve ser atualizado aqui mesmo**, sem criar outro; `motor-coscip/docs/proxima-sessao.md` é uma cópia sincronizada.
Plano de referência: `motor-coscip/docs/plano/00-plano-completo.html` (v2.0). Status por ID: `motor-coscip/docs/backlog.md`.

## Onde estamos

Fase de viabilidade, **Gate A pré-aprovado**. A planta real aparece na tela, o clique leva à origem no DXF, a unidade
é confirmada com referência medida, a medição foi conferida contra 1.460 cotas dos 5 projetos e o recorte de
pavimento funciona. Falta só o que depende de você (abaixo).

### Feito nesta sessão (verificado: 97 testes, lint, build, migração coerente)

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

## Próximos passos técnicos, em ordem

1. **Tela de revisão das confirmações** (lista de desenhos com unidade confirmada por quem/justificativa e botão
   "aceitar") — facilita o item 1 acima.
2. **PREP-02 — classificação assistida**: portas, saídas, extintores e ambientes a partir de layers/blocos
   (`coscip_semantics.classify` já existe), com confirmação por propriedade e novo snapshot.
3. **PREP-03 / GEO-02 / GEO-03**: contornos analíticos, áreas e largura livre de portas (vão × folha).
4. **Recorte poligonal** (hoje só retângulo) e opção de recomputar o enquadramento das cenas antigas.
5. **REG-02**: matriz de cobertura da NT 2-01 (extintores) — precisa do responsável técnico.
6. **REP-01**: relatório HTML local com cobertura, evidências, hashes e pendências.

Melhorias anotadas: texto (TEXT/MTEXT) ainda não é desenhado na cena; importação do 9715 levou 44 s (discretização
de ~24 mil curvas); destaque da entidade selecionada percorre todos os segmentos (ok até 1,3 mi).

## Estado do ambiente

- Código: `C:\Users\USER\Downloads\motor-coscip`. Commits: `d53f65d` (fundação) + o commit desta sessão.
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

> Leia `C:\Users\USER\Downloads\proxima-sessao.md` e continue pelos próximos passos técnicos; atualize esse mesmo arquivo ao final.
