# Skills externas de CAD

Instaladas em 09/11/2026 a pedido do usuário, para ajudar na criação de projetos (plantas DXF/DWG,
cortes, fachadas). Ficam em `.claude/skills/<nome>/`, que o Claude Code lê como skills do projeto.
**Não** entram em `skills/` (essa pasta é a fonte das skills CBMERJ empacotadas por
`tools/skills/pack.py`) nem em `skills/pacotes.yaml`, então `verificar_links` e o workflow *Skills*
não as enxergam. Os arquivos estão **como no original**, sem edição; só foram retirados `.git`,
`.github` e `.gitignore`, e a licença GPL-3.0 foi copiada para `qcad/` e `freecad/`.
`docs/skills-externas.sha256` lista o hash de cada arquivo instalado.
Nada foi commitado.

| Skill | Origem (commit) | Licença | Para que serve aqui |
| --- | --- | --- | --- |
| `cad-operations` | github.com/2836048681/cad-operations-skill (`e430a57`, 29/05/2026) | MIT | Porta de entrada de CAD local; geradores de unifilar elétrico e de estrutura de pavimento (pouco ligados ao COSCIP); notas de AutoCAD, FreeCAD e SolidWorks |
| `dxf-civil` | github.com/pedroschz/dxf-civil (`1603445`, 11/05/2026) | MIT | Inspecionar, validar e quantificar DXF com `ezdxf` (`summary.py`, `validate.py`, `query.py`, `takeoff.py`, `render.py`); útil para conferir os DXF do motor |
| `qcad` | github.com/jablonkai/skills, `skills/qcad` (`81507bd`, v1.0.4) | GPL-3.0-only | Desenho 2D por script no QCAD sem interface, selo (title block) e DXF/DWG para PDF/PNG em lote |
| `freecad` | github.com/jablonkai/skills, `skills/freecad` (`81507bd`, v1.0.4) | GPL-3.0-only | Modelagem 3D paramétrica no FreeCAD por uma ponte local; exporta STEP/STL |

## O que foi verificado (leitura do código; nada foi executado)

- Todos os arquivos de cada skill foram listados; os quatro `SKILL.md`, `qcad-run.sh`,
  `freecad-bridge.py` e `freecad-send.sh` foram lidos por inteiro. Os demais scripts passaram por
  busca de `subprocess`, `eval/exec`, rede, `base64`, `rmtree`, `chmod`, `sudo`, `pickle`, `ctypes`.
- Não achei ofuscação, envio de dados, download de código nem acesso a credenciais.
- Achados, todos coerentes com o que as próprias skills declaram:
  - `freecad-bridge.py` abre um **servidor local que executa qualquer Python recebido**, em
    `127.0.0.1:8735`, sem autenticação (só recusa requisições com `Origin`/`Sec-Fetch-Site`). Só
    existe quando o usuário o inicia dentro do FreeCAD; a skill manda avisar antes. **Não iniciar
    sem pedir ao usuário.**
  - `cad-operations`: `generate_pavement_cad*.py` chamam `subprocess.Popen` só para abrir o AutoCAD
    quando se pede `--open`; `tests/smoke_test.py` apaga `output/smoke` dentro da própria pasta.
  - `qcad-run.sh` apaga só o diretório temporário que ele cria com `mktemp`.
  - `dxf-civil` não faz rede nem executa comandos; grava só no que se pede.
- **Não executei nenhum script baixado** (o teste foi bloqueado pelo classificador de permissões);
  portanto não há prova de que rodam nesta máquina.

## Limitações nesta máquina (Windows, `.venv` do projeto)

- `qcad` e `freecad` foram escritas para **macOS** (`/Applications/...`, `open -a`, `sips`,
  `qlmanage`) e os `.sh` precisam de bash. QCAD e FreeCAD **não estão instalados** aqui.
- `dxf-civil/render.py` precisa de `matplotlib` e `cad-operations/make_main_sld.py` de `reportlab`;
  nenhum dos dois está no `.venv` (`requirements/dev.lock` é travado por hash: não instalei nada).
  `ezdxf` e `PyYAML` já estão.
- `cad-operations` cita Codex, SolidWorks MCP e COM; `agents/openai.yaml` não serve ao Claude Code.
- `dxf-civil/standards/*.yml` trazem a convenção de camadas americana (NCS) como exemplo; as
  camadas do motor (`PAREDE`, `INC_EXT`, `ROTAS`...) não seguem esse padrão. Ajustar antes de usar
  `validate.py` como checagem de padrão.
- As regras do `dxf-civil` ("nunca ler DXF direto", "ler de `input/`, gravar em `output/`")
  convivem com o fluxo do motor; para plantas do COSCIP, as ferramentas `coscip-plantas` continuam
  sendo a primeira escolha (decisão do projeto: primeiro a ferramenta para a IA ler a planta).
- Licença GPL-3.0 em `qcad`/`freecad`: o repositório é privado; se for publicado ou distribuído,
  rever. As duas skills não foram misturadas ao código do motor.

## Atualizar ou remover

Atualizar: clonar de novo cada origem numa pasta vazia, ler o diff e recopiar. Remover:
apagar `.claude/skills/<nome>/` e a linha correspondente aqui.

## Reavaliação (09/11/2026): o que ficou ativo e o que foi guardado

Critério: só fica em `.claude/skills/` (descoberta automática) o que serve a este projeto e roda aqui.
As descrições de `qcad`, `freecad` e `cad-operations` são amplas ("DXF", "floor plan", "CAD model") e
passariam a ser sugeridas em qualquer tarefa de desenho, apontando para programas que **não estão
instalados** (QCAD, FreeCAD, AutoCAD). Elas foram movidas, **sem alteração**, para
`.claude/skills-inativas/` (o Claude Code não lê essa pasta). Para reativar: instalar o programa e
mover a pasta de volta para `.claude/skills/`.

| Skill | Situação | Por quê |
| --- | --- | --- |
| `dxf-civil` | **ativa** | Leitura, validação e quantitativo de DXF sem despejar o arquivo no contexto; `ezdxf` e `PyYAML` já estão no `.venv`. |
| `qcad` | inativa | Exige QCAD (não instalado) e bash/macOS; o que ela faz (camadas, cotas, hachuras, selo, DXF para PDF) já sai dos scripts em `ezdxf`. Aproveitável quando houver QCAD: `title-block.js` (selo em DXF existente) e `batch-export.js` (DXF/DWG para PDF em lote). |
| `freecad` | inativa | 3D mecânico paramétrico; o projeto é 2D. Só serviria para modelo 3D da edificação com cortes por TechDraw. Tem a ponte de execução remota (ver Riscos). |
| `cad-operations` | inativa | Geradores de unifilar elétrico e de pavimento, SolidWorks e Codex: fora do escopo. O que prestava (DXF como fonte, DWG por conversor, conferir o arquivo gerado) já é o fluxo do projeto. |

**Adaptação feita:** `dxf-civil/standards/layers.coscip.yml` (novo; o `layers.yml` americano ficou
intacto) com as camadas do motor e das vistas. Uso:
`python scripts/validate.py <arquivo.dxf> --standards standards/layers.coscip.yml`
(não executado). As camadas do motor são todas ACI 7; só `CORTES` e `VISTA_*` têm cor esperada.

## Candidatas encontradas (não instaladas; informação de páginas de terceiros)

Nenhuma delas foi baixada nem teve o código lido; os dados vêm de resumos de páginas web.

| Candidata | O que traria | Ressalvas |
| --- | --- | --- |
| github.com/alchaincyf/huashu-cad (skill) | Plantas baixas em DXF com `ezdxf`, cotas `DIMENSION` nativas, blocos/atributos, camadas por função, leitura e conferência por render; `references/floorplans.md` | MIT; 15 estrelas e 1 commit; texto em chinês; o agente instala dependências sozinho; testada só em macOS |
| github.com/puran-water/autocad-mcp (MCP, não skill) | Ferramentas de camadas, polilinhas, hachuras, cotas, blocos e salvar DXF; backend `ezdxf` sem AutoCAD | MIT; 642 estrelas; o backend AutoLISP (`execute_lisp`) roda código arbitrário no AutoCAD LT, que não está instalado: usar só o backend `ezdxf`; sem layouts/viewports |
| github.com/earthtojake/text-to-cad (`engineering-drawing`, `cad`) | Desenho técnico cotado em PDF a partir de modelo 3D; perfis 2D/DXF | MIT; 25,9 mil estrelas; foco mecânico; o instalador oficial é `irm \| iex` (baixa e executa script): não usar, copiar só a pasta da skill depois de ler; envia telemetria por padrão |
| Blueprint Engine (Tibsfox/gsd-skill-creator) | Convenções de selo, numeração de folhas ("Sheet X of Y"), planta baixa em SVG/DXF | Só texto de orientação; licença não confirmada; exemplos de data center |
| OpenAEC bonsai-impl-drawing (Impertio-Studio) | Plantas, cortes e fachadas a partir de modelo IFC no Blender/Bonsai, em folhas com selo | Exige Blender 4.2+, Bonsai e Inkscape; o projeto não tem modelo IFC |
