"""Autoria de plantas: a IA descreve a planta em operações e o motor gera o DXF.

A planta criada aqui é **sintética** (desenhada pela IA a partir do que o usuário descreveu),
não um projeto real. O estado é a lista de operações, guardada ao lado do DXF em
``<nome>.coscip.json``; cada alteração regenera o DXF inteiro a partir dela, então o arquivo
nunca fica pela metade e a IA pode retomar a planta depois.

Convenções do desenho gerado (as mesmas que o leitor do motor reconhece):

- coordenadas em METROS, eixo Y para cima, ``$INSUNITS`` = 6;
- paredes como contornos fechados de linhas (espessura real) na camada do estilo da parede
  (comum, corta-fogo, compartimentação, divisória — NT 1-03, p. 10), com os vãos das portas
  já recortados; portas na camada ``PORTAS`` (``PORTA_CORTA_FOGO`` para P-60/90/120);
- ambientes como polilinha fechada em ``AMBIENTES`` com nome e área em texto;
- símbolos como blocos do catálogo da NT 1-03 / NT 2-05 (``simbologia.py``), com o nome que o
  dicionário (``simbolos.yaml``) reconhece, e legenda gerada a partir deles (NT 1-03, 5.4).

Mesmo assim a unidade segue a regra do projeto: a análise só roda depois de
``confirmar_unidade`` (duas medidas em direções diferentes, ex. duas paredes cujo
comprimento o usuário informou).
"""

from __future__ import annotations

import difflib
import json
import math
import re
from pathlib import Path
from typing import Annotated, Any, Literal

import ezdxf
from coscip_design.rede_sprinklers import Rede, projetar
from coscip_design.sprinklers import Classe, EntradaSprinklers, ZonaEntrada, criterios_de
from ezdxf.enums import TextEntityAlignment
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from shapely.geometry import LineString, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from coscip_mcp import (
    apresentacao,
    biblioteca,
    detalhes,
    folhas,
    isometrico,
    quadro_resumo,
    simbologia,
    situacao,
    vistas,
)
from coscip_mcp.detalhes import Detalhe
from coscip_mcp.folhas import Folha
from coscip_mcp.quadro_resumo import Contagens, QuadroResumo
from coscip_mcp.simbologia import Entrada
from coscip_mcp.situacao import Situacao
from coscip_mcp.vistas import Edificacao, Fachada, Secao

SCHEMA = "coscip-autoria/1"
MIN_WALL_SEGMENTS = 20  # mesmo limite de coscip_analysis.analyze (walls_detected)
WALL_PIECE_M = 0.5

Pt = Annotated[list[float], Field(min_length=2, max_length=2)]

BASE_LAYERS = ("PAREDE", "PORTAS", "AMBIENTES", "TEXTOS", "COTAS", "LEGENDA")

# estilos de parede da NT 1-03 (p. 10): camada, preenchimento, espessura padrão, id no catálogo
WALL_STYLES: dict[str, tuple[str, str | None, float, str]] = {
    "comum": ("PAREDE", None, 0.15, "PAREDE_COMUM"),
    "corta_fogo": ("PAREDE_CORTA_FOGO", "solid", 0.20, "PAREDE_CORTA_FOGO"),
    "compartimentacao": ("PAREDE_COMPARTIMENTACAO", "hatch", 0.20, "PAREDE_COMPARTIMENTACAO"),
    "divisoria": ("DIVISORIA", None, 0.05, "DIVISORIA"),
}
WallStyle = Literal["comum", "corta_fogo", "compartimentacao", "divisoria"]

# classe do motor -> símbolo do catálogo usado quando a IA pede só a classe
CLASS_DEFAULTS: dict[str, str] = {
    "HIDRANTE": "HIDRANTE_SIMPLES", "HIDRANTE_URBANO": "HIDRANTE_URBANO",
    "REGISTRO_RECALQUE": "REGISTRO_RECALQUE", "BOMBA_INCENDIO": "BOMBA_INCENDIO",
    "ACIONADOR_BOMBA": "ACIONADOR_BOMBA_INCENDIO", "RESERVA_TECNICA": "RESERVA_TECNICA_INCENDIO",
    "SPRINKLER": "BICO_SPRINKLER_PENDENTE", "ILUMINACAO_EMERGENCIA": "PONTO_ILUMINACAO_EMERGENCIA",
    "DETECTOR": "DETECTOR_FUMACA", "ACIONADOR_MANUAL": "ACIONADOR_MANUAL",
    "AVISADOR": "AVISADOR_SONORO_ELETRONICO", "CENTRAL_ALARME": "CENTRAL_ALARME_DETECCAO",
    "CENTRAL_GLP": "CENTRAL_GLP", "SAIDA": "ROTA_DE_FUGA_FINAL",
}
# agente do extintor aceito -> sufixo do bloco (o dicionário lê o agente do nome)
EXTINGUISHER_AGENTS = {"CO2": "CO2", "AP": "AP", "AGUA": "AP", "ESPUMA": "ESPUMA",
                       "PQS_BC": "PQS_BC", "PQS_ABC": "PQS_ABC", "PO_D": "PO_D",
                       "PQS_D": "PO_D", "CLASSE_D": "PO_D"}
STATES = ("NOVO", "EXISTENTE", "DEMOLIR", "REALOCADO")
_CAPACITY = re.compile(r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*(kg|l)\s*$", re.I)


def classes_desenhaveis() -> list[str]:
    return sorted({"EXTINTOR", "SINALIZACAO", *CLASS_DEFAULTS})


class AuthoringError(ValueError):
    """Erro de uso: a mensagem diz à IA o que corrigir."""


class _Op(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Parede(_Op):
    """Parede pelo EIXO: poligonal com espessura. ``fechar`` liga o último ponto ao primeiro."""

    tipo: Literal["parede"]
    pontos: list[Pt] = Field(min_length=2)
    espessura_m: float | None = Field(default=None, gt=0, le=1.0)
    fechar: bool = False
    estilo: WallStyle = "comum"


class Sala(_Op):
    """Ambiente pela face INTERNA (área útil = área do desenho), com parede por fora.

    ``retangulo`` = [x0, y0, x1, y1] ou ``poligono``. Salas vizinhas separadas por uma
    distância igual à espessura dividem uma única parede.
    """

    tipo: Literal["sala"]
    nome: str = Field(min_length=1, max_length=60)
    retangulo: Annotated[list[float], Field(min_length=4, max_length=4)] | None = None
    poligono: list[Pt] | None = Field(default=None, min_length=3)
    espessura_m: float | None = Field(default=None, gt=0, le=1.0)
    estilo_parede: WallStyle = "comum"
    sem_paredes: bool = False
    area_no_desenho: bool = True


class Porta(_Op):
    """Porta sobre uma parede: recorta o vão e desenha a folha e o arco de giro."""

    tipo: Literal["porta"]
    x: float
    y: float
    largura_m: float = Field(default=0.9, ge=0.4, le=6.0)
    angulo_graus: float = Field(default=0.0, description="direção da parede (0 = horizontal)")
    abre_para: Literal["esquerda", "direita"] = "esquerda"
    corte_m: float = Field(default=0.4, gt=0, le=2.0,
                           description="espessura recortada; use ≥ espessura da parede")
    corta_fogo_min: Literal[60, 90, 120] | None = None  # P-60/P-90/P-120 (NT 1-03, p. 10)
    altura_m: float = Field(default=2.10, ge=1.5, le=6.0, description="só para a etiqueta")
    etiqueta: bool = True  # escreve largura x altura em cm (80x210) no lado oposto ao giro


class Janela(_Op):
    """Janela sobre uma parede: recorta o vão, desenha o caixilho e a etiqueta
    ``largura x altura / peitoril`` em cm (150x120/90).

    O motor trabalha em planta: altura e peitoril só entram na etiqueta (e nas fachadas).
    ``espessura_m`` é a da parede onde a janela fica.
    """

    tipo: Literal["janela"]
    x: float
    y: float
    largura_m: float = Field(default=1.5, ge=0.3, le=12.0)
    altura_m: float = Field(default=1.2, ge=0.2, le=4.0)
    peitoril_m: float = Field(default=0.9, ge=0.0, le=3.0)
    angulo_graus: float = Field(default=0.0, description="direção da parede (0 = horizontal)")
    espessura_m: float = Field(default=0.2, gt=0.04, le=1.0)
    etiqueta: bool = True
    lado_etiqueta: Literal["esquerda", "direita"] = "esquerda"


class Simbolo(_Op):
    """Símbolo do catálogo, por ``id`` OU por ``classe`` do motor (+ agente, código…)."""

    tipo: Literal["simbolo"]
    id: str | None = None
    classe: str | None = None
    x: float
    y: float
    rotacao_graus: float = 0.0
    tamanho_m: float | None = Field(default=None, gt=0, le=10)
    agente: str | None = None  # só com classe EXTINTOR
    sobre_rodas: bool = False  # só com classe EXTINTOR
    capacidade: str | None = None  # extintores, ex. "6 kg"
    estado: Literal["NOVO", "EXISTENTE", "DEMOLIR", "REALOCADO"] | None = None
    codigo: str | None = None  # só com classe SINALIZACAO, ex. "E-5", "S-12"


class Chamada(_Op):
    """Chamada de placa em planta: círculo com o código e a dimensão da placa (``E-5``,
    ``150x150``), com linha de chamada até onde a placa será instalada. É a forma de representar
    as placas em plantas de projeto (o pictograma fica na legenda); o motor a conta como a placa
    de sinalização do código (e como saída, para S-12 e S-14)."""

    tipo: Literal["chamada"]
    codigo: str = Field(description="código da NT 2-05, ex. E-5, S-12, P-1")
    x: float
    y: float
    dimensao: str | None = Field(default=None, pattern=r"^[0-9]{1,4}[xX][0-9]{1,4}$",
                                 description="largura x altura da placa em mm, ex. 252x126")
    alvo: Pt | None = None


class Mobiliario(_Op):
    """Bloco da biblioteca própria (louça, mesa, equipamento de cozinha, GLP, escada, pilar):
    ``id`` de ``listar_blocos``, centro em ``x, y``. ``largura_m`` e ``profundidade_m`` mudam o
    tamanho (recipientes de GLP: só a largura, que é o diâmetro)."""

    tipo: Literal["mobiliario"]
    id: str
    x: float
    y: float
    rotacao_graus: float = 0.0
    largura_m: float | None = Field(default=None, gt=0, le=30)
    profundidade_m: float | None = Field(default=None, gt=0, le=30)


class Texto(_Op):
    tipo: Literal["texto"]
    texto: str = Field(min_length=1, max_length=200)
    x: float
    y: float
    altura_m: float | None = Field(default=None, gt=0, le=5,
                                   description="padrão: 2,5 mm impressos na escala da planta")
    camada: str = "TEXTOS"
    centralizado: bool = False


class RotuloClasse(_Op):
    """Rótulo do controle de materiais de acabamento (NT 2-20) na planta, como nas pranchas
    de referência: moldura com PISO (PAREDE, TETO) / CLASSE e a classe abaixo. A classe é a que
    o usuário informar para o material daquele ambiente."""

    tipo: Literal["rotulo_classe"]
    elemento: Literal["piso", "parede", "teto"]
    classe: str = Field(pattern=r"^(I|II-A|II-B|III-A|III-B|IV-A|IV-B|V-A|V-B|VI)$")
    x: float
    y: float


class Cota(_Op):
    """Cota linear (DIMENSION) entre dois pontos; ajuda a confirmar a unidade."""

    tipo: Literal["cota"]
    a: Pt
    b: Pt
    afastamento_m: float = 0.8


class CotaCadeia(_Op):
    """Cotas em cadeia (uma por trecho) alinhadas numa só linha, mais a cota total.

    ``pontos`` em ordem ao longo da linha (a direção é do primeiro ao último ponto).
    ``afastamento_m`` positivo põe a cadeia à esquerda dessa direção, negativo à direita.
    """

    tipo: Literal["cota_cadeia"]
    pontos: list[Pt] = Field(min_length=2, max_length=40)
    afastamento_m: float = 0.8
    total: bool = True
    separacao_total_m: float = Field(default=0.6, ge=0.2, le=5.0)


class MarcaCorte(_Op):
    """Marca de corte na planta: linha tracejada de ``a`` a ``b`` e, em cada ponta, a seta do
    sentido de observação e o círculo com a letra do corte (A, B...)."""

    tipo: Literal["marca_corte"]
    nome: str = Field(min_length=1, max_length=3)
    a: Pt
    b: Pt
    sentido: Literal["esquerda", "direita"] = "esquerda"  # lado de a->b para onde se olha


class Legenda(_Op):
    """Legendas em tabela (NT 1-03, 5.4), no formato das pranchas aprovadas no CBMERJ:

    - ``LEGENDA SISTEMA DE INCÊNDIO``: SÍMBOLO | DESCRIÇÃO (extintores, hidrantes, iluminação,
      alarme, paredes e portas corta-fogo...), cada símbolo na cor do seu sistema;
    - ``LEGENDA - SINALIZAÇÃO DE EMERGÊNCIA``: SÍMBOLO | CÓDIGO E TAMANHO | DESCRIÇÃO, com a
      placa, o círculo com o código e a dimensão (das chamadas da planta) e o nome da NT 2-05.

    Sem ``ids`` lista o que a planta usa (símbolos, estilos de parede, portas corta-fogo, placas
    e chamadas). Com ``ids`` lista exatamente esses. ``x, y`` é o canto superior esquerdo; as
    tabelas descem uma abaixo da outra, com tamanho impresso fixo (160 mm de largura) na
    escala da planta, multiplicado por ``escala``. ``titulo`` troca o título da primeira
    tabela; ``altura_linha_m`` ficou sem uso (o tamanho segue a escala da planta).
    """

    tipo: Literal["legenda"]
    x: float
    y: float
    ids: list[str] | None = None
    titulo: str = "LEGENDA SISTEMA DE INCÊNDIO"
    escala: float = Field(default=1.0, gt=0, le=5)
    altura_linha_m: float = Field(default=1.0, gt=0.2, le=10)


class PavimentoCorte(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=40)
    pe_direito_m: float = Field(default=2.8, ge=2.0, le=20.0)


class Corte(_Op):
    """Corte esquemático / esquema vertical: pavimentos empilhados com níveis e, se pedido, a
    prumada de hidrantes e o reservatório com a RTI.

    É ESQUEMÁTICO: sai das alturas informadas, não da geometria da planta (uma planta 2D não
    tem altura). ``x, y`` é o canto inferior esquerdo, no nível do piso do primeiro pavimento;
    ``pavimentos`` vai de baixo para cima. Desenhe-o afastado da planta baixa.
    """

    tipo: Literal["corte"]
    x: float
    y: float
    largura_m: float = Field(default=12.0, ge=4.0, le=200.0)
    pavimentos: list[PavimentoCorte] = Field(min_length=1, max_length=80)
    laje_m: float = Field(default=0.15, gt=0.05, le=1.0)
    titulo: str = Field(default="CORTE ESQUEMÁTICO", max_length=80)
    prumada_hidrantes: bool = False
    reservatorio: Literal["superior", "inferior"] | None = None
    rti_l: float | None = Field(default=None, gt=0)


TAMANHO_BICO_M = 1.0  # largura do símbolo do bico (com o tubo tracejado de cada lado)


class Sprinklers(_Op):
    """Malha de chuveiros automáticos de uma zona, com a rede e o cálculo hidráulico.

    A zona é um ``retangulo`` [x0, y0, x1, y1], um ``poligono`` ou o nome de uma ``sala`` já
    desenhada. O motor distribui os bicos respeitando o espaçamento e a área máxima por bico da
    classe de risco, traça ramais, subgeral e geral até ``alimentacao`` (onde a prumada chega) e
    calcula a área de operação remota. Critérios não informados vêm da referência da NFPA 13
    (premissa que o memorial de ``dimensionar_sprinklers`` lista para conferir na norma
    adotada). O bico é o símbolo oficial da NT 1-03; o isométrico sai de ``isometrico``.
    """

    tipo: Literal["sprinklers"]
    nome: str = Field(min_length=1, max_length=40)
    classe: Classe = "ORDINARIO_1"
    sala: str | None = None
    retangulo: Annotated[list[float], Field(min_length=4, max_length=4)] | None = None
    poligono: list[Pt] | None = Field(default=None, min_length=3)
    alimentacao: Pt
    z_ramal_m: float = Field(default=3.0, gt=0.5, le=30)
    z_base_m: float = Field(default=0.0, ge=-10, le=50)
    orientacao: Literal["auto", "x", "y"] = "auto"
    densidade_mm_min: float | None = Field(default=None, gt=0, le=60)
    area_operacao_m2: float | None = Field(default=None, gt=0, le=2000)
    area_max_bico_m2: float | None = Field(default=None, gt=0, le=40)
    espacamento_max_m: float | None = Field(default=None, gt=0, le=8)
    fator_k: float = Field(default=80.0, gt=10, le=400)
    mostrar_dn: bool = True
    mostrar_area_de_operacao: bool = True


class Isometrico(_Op):
    """Isométrico (eixos a 30°) da rede de uma operação ``sprinklers``, com o quadro de cálculo
    hidráulico. ``x, y`` é onde fica a base da prumada no desenho; desenhe-o longe da planta."""

    tipo: Literal["isometrico"]
    sprinklers: str = Field(description="nome da operação sprinklers")
    x: float
    y: float
    titulo: str = Field(default="ISOMÉTRICO DA REDE DE SPRINKLERS", max_length=80)
    quadro: bool = True


Operacao = Annotated[Parede | Sala | Porta | Janela | Simbolo | Chamada | Mobiliario | Texto
                     | Cota | CotaCadeia | MarcaCorte | Legenda | Corte | Folha | QuadroResumo
                     | Edificacao | Secao | Fachada | Sprinklers | Isometrico | Situacao
                     | RotuloClasse | Detalhe,
                     Field(discriminator="tipo")]
_OPS = TypeAdapter(list[Operacao])


def parse_ops(raw: list[dict[str, Any]]) -> list[_Op]:
    return _OPS.validate_python(raw)


def sidecar(path: Path) -> Path:
    return path.with_suffix(".coscip.json")


# --- resolução de símbolos ------------------------------------------------------------------------


def resolve_symbol(op: Simbolo) -> Entrada:
    """Entrada do catálogo para o pedido; levanta ``AuthoringError`` com a correção."""
    if (op.id is None) == (op.classe is None):
        raise AuthoringError("simbolo: informe 'id' (de listar_simbologia) OU 'classe'")
    if op.id is not None:
        entry = simbologia.achar(op.id)
        if entry is None:
            near = difflib.get_close_matches(op.id.upper(), list(simbologia.CATALOGO), n=4,
                                             cutoff=0.5)
            raise AuthoringError(f"símbolo {op.id!r} não existe no catálogo"
                                 + (f"; parecidos: {near}" if near else "")
                                 + "; veja listar_simbologia")
        if op.agente or op.sobre_rodas or op.codigo:
            raise AuthoringError("agente, sobre_rodas e codigo só valem com 'classe'; com 'id' "
                                 "o símbolo já é específico")
    else:
        cls = (op.classe or "").upper()
        if cls == "EXTINTOR":
            if not op.agente:
                raise AuthoringError("classe EXTINTOR exige agente: "
                                     f"{sorted(set(EXTINGUISHER_AGENTS))}")
            agent = EXTINGUISHER_AGENTS.get(op.agente.upper())
            if agent is None:
                raise AuthoringError(f"agente {op.agente!r} inválido; use "
                                     f"{sorted(set(EXTINGUISHER_AGENTS))}")
            entry = simbologia.CATALOGO[
                f"EXTINTOR_{agent}" + ("_SOBRERODAS" if op.sobre_rodas else "")]
        elif cls == "SINALIZACAO":
            found = simbologia.achar(op.codigo) if op.codigo else None
            if found is None or not found.esquematico:
                raise AuthoringError("classe SINALIZACAO exige codigo da NT 2-05, ex. 'E-5', "
                                     "'S-12' (listar_simbologia grupo='PLACAS')")
            entry = found
        elif cls in CLASS_DEFAULTS:
            entry = simbologia.CATALOGO[CLASS_DEFAULTS[cls]]
        else:
            raise AuthoringError(f"classe {op.classe!r} não desenhável; use uma de "
                                 f"{classes_desenhaveis()} ou 'id' (listar_simbologia)")
        if cls != "EXTINTOR" and (op.agente or op.sobre_rodas):
            raise AuthoringError("agente e sobre_rodas só valem para EXTINTOR")
        if cls != "SINALIZACAO" and op.codigo:
            raise AuthoringError("codigo só vale para SINALIZACAO")
    if entry.uso == "parede":
        raise AuthoringError(f"{entry.id} é um estilo de parede: use a operação 'parede' ou "
                             "'sala' com estilo (corta_fogo, compartimentacao, comum, divisoria)")
    if entry.uso == "porta":
        raise AuthoringError(f"{entry.id} é uma porta: use a operação 'porta' com "
                             "corta_fogo_min (60, 90 ou 120)")
    if op.capacidade:
        if entry.classe != "EXTINTOR":
            raise AuthoringError("capacidade só vale para extintor")
        if not _CAPACITY.match(op.capacidade):
            raise AuthoringError(f"capacidade {op.capacidade!r}: use '6 kg' ou '10 L'")
    return entry


def block_name(op: Simbolo, entry: Entrada | None = None) -> str:
    """Nome do bloco: id do catálogo + estado + capacidade (a capacidade vai por último: o
    dicionário a lê com "\\b" depois da unidade, ex. "6KG")."""
    entry = entry or resolve_symbol(op)
    parts = [entry.id]
    if op.estado:
        parts.append(op.estado)
    m = _CAPACITY.match(op.capacidade or "")
    if m:
        parts.append(m.group(1).replace(",", ".") + m.group(2).upper())
    return "_".join(parts)


class Authoring:
    """Planta em construção: lista de operações + o DXF que elas geram."""

    def __init__(self, path: Path, ops: list[_Op] | None = None, title: str = "",
                 escala: int = apresentacao.ESCALA_PADRAO) -> None:
        self.path = path
        self.ops: list[_Op] = ops or []
        self.title = title
        # denominador da escala de impressão (100 = 1:100): decide texto, cota e marcas
        self.escala = validar_escala(escala)
        # Posições dos símbolos de legenda (x, y, classe do motor), da última geração.
        self.legend_marks: list[tuple[float, float, str]] = []
        # Retângulos [x0, y0, x1, y1] das tabelas de legenda desenhadas pelo motor: o que está
        # dentro é legenda, não equipamento (o leitor recebe essas regiões).
        self.legend_boxes: list[list[float]] = []

    # --- persistência ---------------------------------------------------------------------

    @classmethod
    def load(cls, path: Path) -> Authoring:
        side = sidecar(path)
        if not side.exists():
            raise AuthoringError(f"não há planta criada pelo motor em {path} (falta {side.name})")
        data = json.loads(side.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA:
            raise AuthoringError(f"{side.name}: esquema desconhecido {data.get('schema')!r}")
        return cls(path, parse_ops(data["operacoes"]), data.get("titulo", ""),
                   data.get("escala", apresentacao.ESCALA_PADRAO))

    def save(self) -> None:
        body = {"schema": SCHEMA, "titulo": self.title, "escala": self.escala,
                "aviso": "planta sintética criada pelo MCP do motor COSCIP; não é projeto real",
                "operacoes": [o.model_dump(exclude_none=True) for o in self.ops]}
        sidecar(self.path).write_text(json.dumps(body, ensure_ascii=False, indent=1),
                                      encoding="utf-8")

    # --- edição ---------------------------------------------------------------------------

    def add(self, raw: list[dict[str, Any]]) -> list[int]:
        new = parse_ops(raw)
        for op in new:
            _validate(op)
        first = len(self.ops)
        self.ops.extend(new)
        return list(range(first, len(self.ops)))

    def remove(self, indices: list[int]) -> list[_Op]:
        bad = [i for i in indices if not 0 <= i < len(self.ops)]
        if bad:
            raise AuthoringError(f"índices inexistentes: {bad}; há {len(self.ops)} elementos "
                                 "(0 a n-1, de listar_elementos)")
        gone = [self.ops[i] for i in sorted(set(indices))]
        keep = set(range(len(self.ops))) - set(indices)
        self.ops = [op for i, op in enumerate(self.ops) if i in keep]
        return gone

    def describe(self) -> list[dict[str, Any]]:
        return [{"i": i, **op.model_dump(exclude_none=True)} for i, op in enumerate(self.ops)]

    def used_entries(self) -> list[Entrada]:
        """Símbolos, estilos de parede e portas corta-fogo usados, sem repetir, na ordem."""
        out: dict[str, Entrada] = {}
        for op in self.ops:
            ent: Entrada | None = None
            if isinstance(op, Simbolo):
                ent = resolve_symbol(op)
            elif isinstance(op, Parede) and op.estilo != "comum":
                ent = simbologia.CATALOGO[WALL_STYLES[op.estilo][3]]
            elif isinstance(op, Sala) and op.estilo_parede != "comum" and not op.sem_paredes:
                ent = simbologia.CATALOGO[WALL_STYLES[op.estilo_parede][3]]
            elif isinstance(op, Porta) and op.corta_fogo_min:
                ent = simbologia.CATALOGO[f"PORTA_CORTA_FOGO_P{op.corta_fogo_min}"]
            if ent is not None:
                out.setdefault(ent.id, ent)
        return list(out.values())

    # --- geração do DXF --------------------------------------------------------------------

    def build(self) -> dict[str, Any]:
        """Regenera o DXF (substitui o arquivo) e devolve um resumo do que foi desenhado."""
        doc = ezdxf.new("R2018", setup=True)
        apresentacao.configurar(doc, self.escala)
        for name in BASE_LAYERS:
            apresentacao.criar_camada(doc, name)
        msp = doc.modelspace()
        blocks: set[str] = set()
        esc = self.escala

        def layer(name: str) -> str:
            return apresentacao.criar_camada(doc, name)

        walls: dict[str, list[BaseGeometry]] = {}
        openings: list[BaseGeometry] = []
        rooms: list[dict[str, Any]] = []
        for op in self.ops:
            if isinstance(op, Parede):
                t = op.espessura_m or WALL_STYLES[op.estilo][2]
                pts = [tuple(p) for p in op.pontos]
                if op.fechar:
                    pts.append(pts[0])
                walls.setdefault(op.estilo, []).append(
                    LineString(pts).buffer(t / 2, cap_style="square", join_style="mitre"))
            elif isinstance(op, Sala):
                poly = _room_polygon(op)
                if not op.sem_paredes:
                    t = op.espessura_m or WALL_STYLES[op.estilo_parede][2]
                    walls.setdefault(op.estilo_parede, []).append(
                        poly.buffer(t, join_style="mitre").difference(poly))
                rooms.append({"nome": op.nome, "area_m2": round(poly.area, 2)})
            elif isinstance(op, Porta):
                openings.append(_door_opening(op))
            elif isinstance(op, Janela):
                openings.append(_window_opening(op))

        cut = unary_union(openings) if openings else None
        wall_loops = wall_segments = 0
        paredes_finais: list[BaseGeometry] = []
        for style, parts in walls.items():
            geom = unary_union(parts)
            if cut is not None:
                geom = geom.difference(cut)
            if geom.is_empty:
                continue
            paredes_finais.append(geom)
            wall_layer, fill, _, _ = WALL_STYLES[style]
            lname = layer(wall_layer)
            for poly in getattr(geom, "geoms", [geom]):
                for ring in (poly.exterior, *poly.interiors):
                    pts = list(ring.coords)
                    for a, b in zip(pts, pts[1:], strict=False):
                        for p, q in _chop(a, b):
                            msp.add_line(p, q, dxfattribs={"layer": lname})
                            wall_segments += 1
                    wall_loops += 1
                if fill:
                    _fill_wall(msp, poly, lname, fill)

        self.legend_marks = []
        self.legend_boxes = []
        legends: list[Legenda] = []
        calculadas = self._calcular_redes()
        bicos_da_sala: dict[str, list[tuple[float, float, float]]] = {}
        for sop, rede in calculadas.values():
            if sop.sala is not None:  # o nome do ambiente não pode ficar sobre um bico
                rot = 0.0 if rede.resumo["orientacao_dos_ramais"] == "x" else 90.0
                bicos_da_sala.setdefault(sop.sala.casefold(), []).extend(
                    (b.x, b.y, rot) for b in rede.bicos)
        for op in self.ops:
            if isinstance(op, Sala):
                _draw_room(msp, op, esc, bicos_da_sala.get(op.nome.casefold(), []))
            elif isinstance(op, Porta):
                if op.corta_fogo_min:
                    layer("PORTA_CORTA_FOGO")
                if op.etiqueta:
                    layer("ROTULOS")
                _draw_door(msp, op, esc)
            elif isinstance(op, Janela):
                layer("JANELAS")
                if op.etiqueta:
                    layer("ROTULOS")
                _draw_window(msp, op, esc)
            elif isinstance(op, Simbolo):
                entry = resolve_symbol(op)
                _place(doc, msp, entry, block_name(op, entry), layer(camada_de(entry)), op.x, op.y,
                       op.rotacao_graus, op.tamanho_m or entry.tamanho_m, blocks)
            elif isinstance(op, Chamada):
                layer(apresentacao.camada_placa(op.codigo))
                _draw_callout(doc, msp, op, esc)
            elif isinstance(op, Mobiliario):
                bloco = _resolve_block(op)
                biblioteca.inserir(doc, msp, bloco, op.x, op.y, op.rotacao_graus, op.largura_m,
                                   op.profundidade_m, layer(bloco.camada))
            elif isinstance(op, RotuloClasse):
                vistas.rotulo_classe(msp, op.x, op.y, op.elemento, op.classe, esc,
                                     layer("ROTULO_CLASSE"))
            elif isinstance(op, Texto):
                _text(msp, op.texto, op.x, op.y,
                      op.altura_m or apresentacao.altura_texto(esc), layer(op.camada),
                      op.centralizado)
            elif isinstance(op, Cota):
                _draw_dim(msp, op, esc)
            elif isinstance(op, CotaCadeia):
                _draw_dim_chain(msp, op, esc)
            elif isinstance(op, MarcaCorte):
                layer("CORTES")
                _draw_section_mark(msp, op, esc)
            elif isinstance(op, Legenda):
                legends.append(op)
            elif isinstance(op, Corte):
                _draw_section(doc, msp, op, layer("CORTE"), layer("CORTE_INC"), blocks, esc)
        redes = self._desenhar_sprinklers(doc, msp, layer, blocks, calculadas)
        for leg in legends:  # por último: "usados" depende de todas as outras operações
            self._draw_legend(doc, msp, leg, blocks)

        quadros = [op for op in self.ops if isinstance(op, QuadroResumo)]
        if len(quadros) > 1:
            raise AuthoringError("só um quadro_resumo por planta (há "
                                 f"{len(quadros)}); remova os outros com remover_elementos")
        quadro_out = None
        if quadros:  # depois de todo o desenho: a contagem sai das operações
            quadro_out = quadro_resumo.desenhar(doc, msp, quadros[0],
                                                _contar(self.ops, quadros[0]), esc)

        vistas_out = self._desenhar_vistas(doc, msp, paredes_finais, layer)
        situacoes = [op for op in self.ops if isinstance(op, Situacao)]
        if len(situacoes) > 1:
            raise AuthoringError("só uma situacao por planta (há "
                                 f"{len(situacoes)}); remova as outras com remover_elementos")
        detalhes_out = []
        for dop in (op for op in self.ops if isinstance(op, Detalhe)):
            try:
                detalhes_out.append(detalhes.desenhar(doc, msp, dop))
            except detalhes.DetalheError as exc:
                raise AuthoringError(str(exc)) from exc
        situacao_out = None
        if situacoes:
            try:
                situacao_out = situacao.desenhar(doc, msp, situacoes[0])
            except ValueError as exc:
                raise AuthoringError(str(exc)) from exc

        sheets: list[dict[str, Any]] = []
        folha_ops = [op for op in self.ops if isinstance(op, Folha)]
        if folha_ops:  # depois do model space completo: a vista padrão é o desenho inteiro
            from ezdxf import bbox

            e = bbox.extents(msp)
            ext = (e.extmin.x, e.extmin.y, e.extmax.x, e.extmax.y) if e.has_data else None
            for fo in folha_ops:
                try:
                    sheets.append(folhas.montar(doc, fo, ext, rooms, esc,
                                                legenda_ext=self._legend_extent()))
                except folhas.FolhaError as exc:
                    raise AuthoringError(str(exc)) from exc

        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        doc.saveas(tmp)  # grava inteiro e só então troca: nunca fica DXF pela metade
        tmp.replace(self.path)
        self.save()
        out: dict[str, Any] = {"contornos_de_parede": wall_loops,
                               "segmentos_de_parede": wall_segments, "ambientes": rooms,
                               "operacoes": len(self.ops), "escala_de_impressao": f"1:{esc}"}
        if sheets:
            out["folhas"] = sheets
        if quadro_out:
            out["quadro_resumo"] = quadro_out
        if vistas_out:
            out["vistas"] = vistas_out
        if situacao_out:
            out["situacao"] = situacao_out
        if detalhes_out:
            out["detalhes"] = detalhes_out
        if redes:
            out["sprinklers"] = redes
        if wall_segments < MIN_WALL_SEGMENTS:
            out["ALERTA_paredes"] = (
                f"só {wall_segments} segmentos de parede: o motor só reconhece paredes com "
                f"{MIN_WALL_SEGMENTS} ou mais e, sem elas, a área útil e os percursos "
                "viram estimativa do recorte. Desenhe as salas/paredes antes de analisar.")
        return out

    def _zona_de(self, op: Sprinklers) -> ZonaEntrada:
        if sum(x is not None for x in (op.sala, op.retangulo, op.poligono)) != 1:
            raise AuthoringError(f"sprinklers {op.nome!r}: informe sala OU retangulo OU poligono")
        pts = op.poligono
        if op.sala is not None:
            sala = next((o for o in self.ops if isinstance(o, Sala)
                         and o.nome.casefold() == op.sala.casefold()), None)
            if sala is None:
                nomes = [o.nome for o in self.ops if isinstance(o, Sala)]
                raise AuthoringError(f"sprinklers {op.nome!r}: não há sala {op.sala!r}; salas "
                                     f"desenhadas: {nomes}")
            pts = [list(c) for c in _room_polygon(sala).exterior.coords][:-1]
        return ZonaEntrada(nome=op.nome, retangulo=op.retangulo,
                           poligono=[list(p) for p in pts] if pts and op.retangulo is None
                           else None, alimentacao=list(op.alimentacao), z_ramal_m=op.z_ramal_m,
                           z_base_m=op.z_base_m, orientacao=op.orientacao)

    def _calcular_redes(self) -> dict[str, tuple[Sprinklers, Rede]]:
        """Malha, rede e hidráulica de cada ``sprinklers`` (antes de desenhar, para que o nome
        dos ambientes se desvie dos bicos)."""
        ops = [o for o in self.ops if isinstance(o, Sprinklers)]
        nomes = [o.nome.casefold() for o in ops]
        if len(set(nomes)) != len(nomes):
            raise AuthoringError("sprinklers: dois com o mesmo nome; use nomes diferentes")
        out: dict[str, tuple[Sprinklers, Rede]] = {}
        for op in ops:
            ent = EntradaSprinklers(
                classe=op.classe, densidade_mm_min=op.densidade_mm_min,
                area_operacao_m2=op.area_operacao_m2, area_max_bico_m2=op.area_max_bico_m2,
                espacamento_max_m=op.espacamento_max_m, fator_k=op.fator_k)
            rede = projetar(self._zona_de(op).zona(), criterios_de(ent))
            if not rede.bicos:
                raise AuthoringError(f"sprinklers {op.nome!r}: " + "; ".join(rede.avisos))
            out[op.nome.casefold()] = (op, rede)
        return out

    def _desenhar_sprinklers(self, doc, msp, layer, blocks: set[str],  # noqa: ANN001
                             calculadas: dict[str, tuple[Sprinklers, Rede]]
                             ) -> list[dict[str, Any]]:
        """Desenha a malha, os tubos e a área de operação de cada ``sprinklers``; depois os
        isométricos."""
        ops = [o for o in self.ops if isinstance(o, Sprinklers)]
        isos = [o for o in self.ops if isinstance(o, Isometrico)]
        redes = {k: r for k, (_, r) in calculadas.items()}
        resumo: list[dict[str, Any]] = []
        entrada_bico = simbologia.CATALOGO["BICO_SPRINKLER_PENDENTE"]
        vga = simbologia.CATALOGO["VALVULA_GOVERNO_ALARME_VGA"]
        for op in ops:
            rede = redes[op.nome.casefold()]
            for nome in ("INC_CHUV_TUBO", "INC_CHUV_TEXTO", "INC_CHUV_AREA"):
                layer(nome)
            rot = 0.0 if rede.resumo["orientacao_dos_ramais"] == "x" else 90.0
            meio_bico = TAMANHO_BICO_M / 2 + 0.08  # o símbolo do bico já traz o tubo
            meio_vga = vga.tamanho_m / 2 + 0.08
            for t in rede.tubos:
                if t.tipo == "prumada":
                    continue
                p0, p1 = _recuar(t.p0[:2], t.p1[:2],
                                 meio_bico if t.de.startswith("B") else
                                 meio_vga if t.de == "PR" else 0.0,
                                 meio_bico if t.para.startswith("B") else 0.0)
                msp.add_line(p0, p1, dxfattribs={"layer": "INC_CHUV_TUBO"})
            for b in rede.bicos:
                _place(doc, msp, entrada_bico, entrada_bico.id, layer(entrada_bico.camada),
                       b.x, b.y, rot, TAMANHO_BICO_M, blocks)
            ax, ay = op.alimentacao
            _place(doc, msp, vga, vga.id, layer(vga.camada), ax, ay, 0.0, vga.tamanho_m, blocks)
            esc = self.escala
            h = apresentacao.altura_texto(esc, apresentacao.TEXTO_PEQUENO_MM)
            if op.mostrar_dn:
                anterior: dict[str, int] = {}
                for t in rede.tubos:
                    if t.tipo != "ramal":  # subgeral e geral: no isométrico e no quadro
                        continue
                    mudou = anterior.get(t.de) != t.dn
                    anterior[t.para] = t.dn
                    comp = math.dist(t.p0[:2], t.p1[:2])
                    if mudou and comp > 10 * h:  # trecho curto: sem rótulo, não sobrepor
                        mx, my = (t.p0[0] + t.p1[0]) / 2, (t.p0[1] + t.p1[1]) / 2
                        vertical = abs(t.p1[0] - t.p0[0]) < abs(t.p1[1] - t.p0[1])
                        _text(msp, f"DN{t.dn}", mx + (1.2 * h if vertical else 0.0),
                              my + (0.0 if vertical else 1.6 * h), h, "INC_CHUV_TEXTO",
                              True)
            if op.mostrar_area_de_operacao:
                ops_b = [b for b in rede.bicos if b.opera]
                sa = rede.resumo["espacamento_entre_bicos_m"]
                sb = rede.resumo["espacamento_entre_ramais_m"]
                dx, dy = (sa, sb) if rot == 0.0 else (sb, sa)
                x0, x1 = min(b.x for b in ops_b) - dx / 2, max(b.x for b in ops_b) + dx / 2
                y0, y1 = min(b.y for b in ops_b) - dy / 2, max(b.y for b in ops_b) + dy / 2
                msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                                   dxfattribs={"layer": "INC_CHUV_AREA", "linetype": "DASHED"})
                _text(msp, f"ÁREA DE OPERAÇÃO {op.nome.upper()} - {len(ops_b)} BICOS - "
                      f"{rede.resumo['area_de_operacao_m2']:.0f} m²".replace(".", ","),
                      x0, y1 + 1.2 * h, h, "INC_CHUV_TEXTO", False)
            resumo.append(rede.as_dict() | {"nome": op.nome, "classe": op.classe})
        for iso in isos:
            rede = redes.get(iso.sprinklers.casefold())
            if rede is None:
                raise AuthoringError(f"isometrico: não há operação sprinklers {iso.sprinklers!r}; "
                                     f"existentes: {[o.nome for o in ops]}")
            try:
                r = isometrico.desenhar(doc, msp, rede, iso.x, iso.y, self.escala, iso.titulo,
                                        iso.quadro)
            except ValueError as exc:
                raise AuthoringError(str(exc)) from exc
            for item in resumo:
                if item["nome"].casefold() == iso.sprinklers.casefold():
                    item["isometrico"] = r
        return resumo

    def _desenhar_vistas(self, doc, msp, paredes: list[BaseGeometry],  # noqa: ANN001
                         layer) -> dict[str, Any]:
        """Cortes e fachadas derivados da planta (frente D5): exigem uma ``edificacao``."""
        secoes = [op for op in self.ops if isinstance(op, Secao)]
        fachadas = [op for op in self.ops if isinstance(op, Fachada)]
        edifs = [op for op in self.ops if isinstance(op, Edificacao)]
        if len(edifs) > 1:
            raise AuthoringError("só uma edificacao por planta (há "
                                 f"{len(edifs)}); remova as outras com remover_elementos")
        if not (secoes or fachadas):
            return {}
        if not edifs:
            raise AuthoringError("secao e fachada exigem a operação edificacao (pé-direito, laje "
                                 "e platibanda informados pelo usuário); acrescente-a")
        modelo = _modelo(self.ops, paredes, edifs[0])
        out: dict[str, Any] = {"secoes": [], "fachadas": []}
        try:
            for op in secoes:
                if op.marca_na_planta:
                    layer("CORTES")
                    marca = MarcaCorte(tipo="marca_corte", nome=op.nome, a=op.a, b=op.b,
                                       sentido=op.sentido)
                    _draw_section_mark(msp, marca, self.escala)
                out["secoes"].append(vistas.secao(doc, msp, modelo, op, self.escala))
            for fo in fachadas:
                out["fachadas"].append(vistas.fachada(doc, msp, modelo, fo, self.escala))
        except ValueError as exc:
            raise AuthoringError(str(exc)) from exc
        out["premissas"] = [
            "alturas do mobiliário e dos recipientes vêm da biblioteca (medidas usuais, "
            "biblioteca.ALTURAS); extintores a 0,95-1,50 m e luminárias sob o forro são "
            "representação, não medida",
            "sem remoção de linhas ocultas nem esquadrias detalhadas; telhado (quando "
            "informado) é um plano por água sobre a pegada retangular, com beiral uniforme",
        ]
        return out

    def _legend_extent(self) -> tuple[float, float, float, float] | None:
        """Retângulo que envolve as tabelas de legenda desenhadas (para a janela da folha)."""
        if not self.legend_boxes:
            return None
        return (min(b[0] for b in self.legend_boxes), min(b[1] for b in self.legend_boxes),
                max(b[2] for b in self.legend_boxes), max(b[3] for b in self.legend_boxes))

    def legend_rows(self, op: Legenda) -> tuple[list[Entrada], list[tuple[Entrada, str]]]:
        """Linhas das duas tabelas: símbolos do sistema e placas ``(entrada, dimensão)``."""
        dims: dict[str, set[str]] = {}
        if op.ids is None:
            entries = self.used_entries()
            for o in self.ops:
                if isinstance(o, Chamada):
                    ent = _resolve_callout(o)
                    dims.setdefault(ent.id, set()).add((o.dimensao or "").lower())
                    if ent not in entries:
                        entries.append(ent)
        else:
            entries = []
            for key in op.ids:
                found = simbologia.achar(key)
                if found is None:
                    raise AuthoringError(f"legenda: {key!r} não existe no catálogo")
                entries.append(found)
        sistema = [e for e in entries if not e.id.startswith("PICTO_")]
        ordem = {"P": 0, "A": 1, "S": 2, "E": 3, "M": 4}
        placas = sorted((e for e in entries if e.id.startswith("PICTO_")),
                        key=lambda e: (ordem.get(e.id[6], 9), int(e.id.split("-")[1])))
        linhas: list[tuple[Entrada, str]] = []
        for e in placas:
            ds = sorted(d for d in dims.get(e.id, {""}) if d) or [""]
            linhas += [(e, d) for d in ds]
        return sistema, linhas

    def _draw_legend(self, doc, msp, op: Legenda, blocks: set[str]) -> None:  # noqa: ANN001
        """Tabelas da legenda (ver ``Legenda``), em milímetros impressos na escala da planta."""
        sistema, placas = self.legend_rows(op)
        k = self.escala / 1000.0 * op.escala  # metros de desenho por mm impresso
        lname = "LEGENDA"
        x0 = op.x
        y = op.y

        def linha(xa: float, ya: float, xb: float, yb: float) -> None:
            msp.add_line((xa, ya), (xb, yb), dxfattribs={"layer": lname})

        def texto(t: str, x: float, yy: float, h_mm: float, centro: bool = True) -> None:
            e = msp.add_text(t, dxfattribs={"layer": lname, "height": h_mm * k,
                                            "style": apresentacao.ESTILO_TEXTO})
            e.set_placement((x, yy), align=TextEntityAlignment.MIDDLE_CENTER if centro
                            else TextEntityAlignment.MIDDLE_LEFT)

        def tabela(titulo: str, cols: list[tuple[str, float]], n: int, passo_mm: float,
                   celula: Any) -> None:  # noqa: ANN401
            nonlocal y
            larg = sum(w for _, w in cols) * k
            topo = y
            texto(titulo, x0 + larg / 2, y - 4.0 * k, 3.0)
            y -= 8.0 * k
            linha(x0, y, x0 + larg, y)
            xs = [x0]
            for _, w in cols:
                xs.append(xs[-1] + w * k)
            for (rot, _), xa, xb in zip(cols, xs, xs[1:], strict=False):
                longo = len(rot) * 0.75 * 2.2 > (xb - xa) / k - 2
                partes = rot.rsplit(" ", 1) if longo else [rot]
                for j, parte in enumerate(partes):  # cabeçalho longo: duas linhas
                    texto(parte, (xa + xb) / 2,
                          y - (3.5 + (j - (len(partes) - 1) / 2) * 2.8) * k, 2.2)
            topo_cab = y
            y -= 7.0 * k
            linha(x0, y, x0 + larg, y)
            for i in range(n):
                celula(i, xs, y - passo_mm * k / 2)
                y -= passo_mm * k
                linha(x0, y, x0 + larg, y)
            for xv in xs[1:-1]:
                linha(xv, topo_cab, xv, y)
            for xv in (xs[0], xs[-1]):
                linha(xv, topo, xv, y)
            linha(x0, topo, x0 + larg, topo)
            self.legend_boxes.append([x0, y, x0 + larg, topo])
            y -= 6.0 * k

        def simbolo(i: int, xs: list[float], yc: float) -> None:
            e = sistema[i]
            gx = (xs[0] + xs[1]) / 2
            _place(doc, msp, e, e.id, apresentacao.criar_camada(doc, camada_de(e)), gx, yc,
                   0.0, 6.0 * k, blocks)
            if e.classe:
                self.legend_marks.append((gx, yc, e.classe))
            texto(e.nome.upper(), xs[1] + 2.0 * k, yc, 2.2, centro=False)

        def placa(i: int, xs: list[float], yc: float) -> None:
            e, dim = placas[i]
            code = e.id.removeprefix("PICTO_")
            gx = (xs[0] + xs[1]) / 2
            _place(doc, msp, e, e.id, apresentacao.criar_camada(doc, camada_de(e)), gx, yc,
                   0.0, 7.0 * k, blocks)
            self.legend_marks.append((gx, yc, "SINALIZACAO"))
            bx = (xs[1] + xs[2]) / 2
            nome = _callout_block(doc, code)
            ref = msp.add_blockref(nome, (bx, yc), dxfattribs={
                "layer": apresentacao.criar_camada(doc, apresentacao.camada_placa(code)),
                "xscale": 10.0 * k, "yscale": 10.0 * k, "zscale": 10.0 * k})  # Ø 9 mm
            ref.add_auto_attribs({"CODIGO": code, "DIMENSAO": dim})
            self.legend_marks.append((bx, yc, "SINALIZACAO"))
            texto(e.nome.split(" - ", 1)[-1], xs[2] + 2.0 * k, yc, 2.2, centro=False)

        if sistema:
            tabela(op.titulo, [("SÍMBOLO", 26.0), ("DESCRIÇÃO", 134.0)], len(sistema), 9.0,
                   simbolo)
        if placas:
            tabela("LEGENDA - SINALIZAÇÃO DE EMERGÊNCIA",
                   [("SÍMBOLO", 26.0), ("CÓDIGO E TAMANHO", 28.0), ("DESCRIÇÃO", 106.0)],
                   len(placas), 11.0, placa)


# --- validação e desenho ----------------------------------------------------------------------


_AGENTES = {"PQS_ABC": "PQS ABC", "PQS_BC": "PQS BC", "CO2": "CO2",
            "AP": "Água pressurizada (AP)", "ESPUMA": "Espuma mecânica", "PO_D": "Pó D"}
_RECIPIENTES = {"BOTIJAO_P45": "P-45 (45 kg)", "BOTIJAO_P190": "P-190 (190 kg)"}


def _pav_de(pavs, x: float, y: float) -> str | None:  # noqa: ANN001
    """Pavimento (do quadro) que contém o ponto; sem janela, o primeiro serve para tudo."""
    for p in pavs:
        j = p.janela
        if j is None or (j[0] <= x <= j[2] and j[1] <= y <= j[3]):
            return p.nome
    return None


def _soma(tabela: dict, chave: Any, pav: str) -> None:  # noqa: ANN401
    por = tabela.setdefault(chave, {})
    por[pav] = por.get(pav, 0) + 1


def _contar(ops: list[_Op], quadro: QuadroResumo) -> Contagens:
    """Conta o que está desenhado, por pavimento, para o Quadro Resumo: extintores por tipo e
    capacidade, hidrantes, alarme e detecção, placas por código e dimensão, pontos de
    iluminação, recipientes de GLP, saídas
    marcadas e a área útil dos ambientes. Símbolo a demolir não entra."""
    pavs = quadro.pavimentos
    c = Contagens([p.nome for p in pavs])
    for op in ops:
        if isinstance(op, Sala):
            poly = _room_polygon(op)
            ponto = poly.representative_point()
            pav = _pav_de(pavs, ponto.x, ponto.y)
            if pav:
                c.area_util[pav] = round(c.area_util.get(pav, 0.0) + poly.area, 4)
        elif isinstance(op, Simbolo):
            if op.estado == "DEMOLIR":
                continue
            ent = resolve_symbol(op)
            pav = _pav_de(pavs, op.x, op.y)
            if pav is None:
                continue
            if ent.classe == "EXTINTOR":
                agente = ent.id.removeprefix("EXTINTOR_").removesuffix("_SOBRERODAS")
                rot = _AGENTES.get(agente, agente) + (
                    " sobre rodas" if ent.id.endswith("_SOBRERODAS") else "")
                cap = _CAPACITY.match(op.capacidade or "")
                rot += (f" {cap.group(1).replace(',', '.')} "
                        f"{'kg' if cap.group(2).lower() == 'kg' else 'L'}" if cap
                        else " (capacidade não informada)")
                _soma(c.extintores, rot, pav)
            elif ent.classe == "ILUMINACAO_EMERGENCIA":
                _soma(c.iluminacao, ent.nome.capitalize(), pav)
            elif ent.classe in ("HIDRANTE", "MANGOTINHO"):
                _soma(c.hidrantes, ent.nome.capitalize(), pav)
            elif ent.classe in ("ACIONADOR_MANUAL", "AVISADOR", "CENTRAL_ALARME", "DETECTOR"):
                _soma(c.alarme, ent.nome.capitalize(), pav)
            elif ent.classe == "SAIDA" and not ent.esquematico:
                c.saidas_desenhadas += 1
            elif ent.esquematico:  # placa desenhada como símbolo: sem dimensão informada
                code = ent.id.removeprefix("PICTO_")
                _soma(c.sinalizacao, (code, ""), pav)
                c.placas_de_saida += code in ("S-12", "S-14")
        elif isinstance(op, Chamada):
            pav = _pav_de(pavs, op.x, op.y)
            if pav is None:
                continue
            code = _resolve_callout(op).id.removeprefix("PICTO_")
            _soma(c.sinalizacao, (code, (op.dimensao or "").lower()), pav)
            c.placas_de_saida += code in ("S-12", "S-14")
        elif isinstance(op, Mobiliario) and op.id.strip().upper() in _RECIPIENTES:
            pav = _pav_de(pavs, op.x, op.y)
            if pav:
                _soma(c.recipientes_glp, _RECIPIENTES[op.id.strip().upper()], pav)
    return c


def _modelo(ops: list[_Op], paredes: list[BaseGeometry], edif: Edificacao) -> vistas.Modelo:
    """Modelo da edificação para as vistas: paredes com os vãos recortados, contorno externo,
    aberturas com altura e peças (mobiliário, volumes, extintores, luminárias)."""
    from shapely import affinity

    contornos: list[BaseGeometry] = []
    aberturas: list[vistas.Abertura] = []
    pecas: list[vistas.Peca] = []
    for op in ops:
        if isinstance(op, Sala) and not op.sem_paredes:
            t = op.espessura_m or WALL_STYLES[op.estilo_parede][2]
            contornos.append(_room_polygon(op).buffer(t, join_style="mitre"))
        elif isinstance(op, Parede) and op.fechar and len(op.pontos) >= 3:
            t = op.espessura_m or WALL_STYLES[op.estilo][2]
            contornos.append(Polygon([tuple(p) for p in op.pontos])
                             .buffer(t / 2, join_style="mitre"))
        elif isinstance(op, Porta):
            aberturas.append(vistas.Abertura("porta", _door_opening(op), op.x, op.y, op.largura_m,
                                             op.angulo_graus, 0.0, op.altura_m))
        elif isinstance(op, Janela):
            aberturas.append(vistas.Abertura("janela", _window_opening(op), op.x, op.y,
                                             op.largura_m, op.angulo_graus, op.peitoril_m,
                                             op.altura_m))
        elif isinstance(op, Mobiliario):
            bloco = _resolve_block(op)
            w, d = biblioteca.tamanho(bloco, op.largura_m, op.profundidade_m)
            poly = affinity.rotate(box(op.x - w / 2, op.y - d / 2, op.x + w / 2, op.y + d / 2),
                                   op.rotacao_graus, origin=(op.x, op.y))
            base, topo = biblioteca.faixa_de_altura(bloco, edif.pe_direito_m)
            pecas.append(vistas.Peca(bloco.nome, poly, base, topo, "mobiliario",
                                     tracejado=bloco.id == "COIFA"))
        elif isinstance(op, Simbolo) and op.estado != "DEMOLIR":
            ent = resolve_symbol(op)
            if ent.classe in ("EXTINTOR", "ILUMINACAO_EMERGENCIA"):
                r = (op.tamanho_m or ent.tamanho_m) / 2
                pecas.append(vistas.Peca(ent.nome, box(op.x - r, op.y - r, op.x + r, op.y + r),
                                         0.0, 0.0,
                                         "extintor" if ent.classe == "EXTINTOR" else "luz"))
    for v in edif.volumes:
        x0, y0, x1, y1 = v.retangulo
        pecas.append(vistas.Peca(v.nome, box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)),
                                 v.base_m, v.topo_m, "volume", v.tracejado))
    if not contornos:
        raise AuthoringError("secao e fachada precisam de ambientes (sala) ou parede fechada "
                             "para saber o contorno da edificação")
    uniao = unary_union(contornos)
    maior = max(getattr(uniao, "geoms", [uniao]), key=lambda g: g.area)
    return vistas.Modelo(unary_union(paredes) if paredes else Polygon(), Polygon(maior.exterior),
                         aberturas, pecas, edif)


def validar_escala(escala: Any) -> int:
    """Denominador da escala de impressão (100 = 1:100); ``AuthoringError`` se inválido."""
    try:
        apresentacao.fator(escala)  # valida
    except ValueError as exc:
        raise AuthoringError(str(exc)) from exc
    return escala


def _resolve_callout(op: Chamada) -> Entrada:
    entry = simbologia.achar(op.codigo)
    if entry is None or not entry.esquematico:
        raise AuthoringError(f"chamada: {op.codigo!r} não é um código de placa da NT 2-05 "
                             "(ex. E-5, S-12, P-1; veja listar_simbologia grupo='PLACAS')")
    return entry


def _resolve_block(op: Mobiliario) -> biblioteca.BlocoBib:
    bloco = biblioteca.achar(op.id)
    if bloco is None:
        near = biblioteca.parecidos(op.id)
        raise AuthoringError(f"mobiliario: bloco {op.id!r} não existe na biblioteca"
                             + (f"; parecidos: {near}" if near else "") + "; veja listar_blocos")
    if bloco.so_diametro and op.profundidade_m:
        raise AuthoringError(f"mobiliario: {bloco.id} é redondo; informe só largura_m (diâmetro)")
    return bloco


def camada_de(entry: Entrada) -> str:
    """Camada de um símbolo do catálogo; as placas da NT 2-05 vão para a camada do seu grupo,
    com a cor do AAST 01/2025, item 3.5 (E em vermelho, S em verde, P e A em laranja)."""
    if entry.esquematico and entry.id.startswith("PICTO_"):
        return apresentacao.camada_placa(entry.id)
    return entry.camada


def _callout_block(doc, code: str) -> str:  # noqa: ANN001
    """Define (uma vez) o bloco ``PLACA_CHAMADA_<código>``: círculo de raio 0,45 com os
    atributos CODIGO e DIMENSAO, na cor do grupo da placa (AAST 01/2025, 3.5)."""
    name = f"PLACA_CHAMADA_{code}"
    if name not in doc.blocks:
        color = apresentacao.cor_placa(code)
        blk = doc.blocks.new(name)
        blk.add_circle((0, 0), 0.45, dxfattribs={"layer": "0", "color": color, "lineweight": 25})
        for tag, y, h in (("CODIGO", 0.08, 0.22), ("DIMENSAO", -0.17, 0.12)):
            att = blk.add_attdef(tag, (0, y), code if tag == "CODIGO" else "", dxfattribs={
                "layer": "0", "height": h, "color": color,
                "style": apresentacao.ESTILO_TEXTO})
            att.set_placement((0, y), align=TextEntityAlignment.MIDDLE_CENTER)
    return name


def _draw_callout(doc, msp, op: Chamada, escala: int) -> None:  # noqa: ANN001
    """Bloco ``PLACA_CHAMADA_<código>`` com atributos CODIGO e DIMENSAO, inserido na escala da
    planta, e a linha de chamada até ``alvo``."""
    entry = _resolve_callout(op)
    code = entry.id.removeprefix("PICTO_")
    name = _callout_block(doc, code)
    color = apresentacao.cor_placa(code)
    camada = apresentacao.camada_placa(code)
    f = apresentacao.fator(escala)
    ref = msp.add_blockref(name, (op.x, op.y), dxfattribs={
        "layer": camada, "xscale": f, "yscale": f, "zscale": f})
    ref.add_auto_attribs({"CODIGO": code, "DIMENSAO": (op.dimensao or "").lower()})
    if op.alvo is not None:
        tx, ty = op.alvo
        dx, dy = tx - op.x, ty - op.y
        dist = math.hypot(dx, dy)
        r = 0.50 * f  # começa um pouco fora do círculo: a linha não encosta nele
        if dist > r:
            ux, uy = dx / dist, dy / dist
            msp.add_line((op.x + ux * r, op.y + uy * r), (tx, ty),
                         dxfattribs={"layer": camada, "color": color})
            msp.add_circle((tx, ty), 0.05 * f, dxfattribs={"layer": camada, "color": color})


def _validate(op: _Op) -> None:
    if isinstance(op, Chamada):
        _resolve_callout(op)
    elif isinstance(op, Mobiliario):
        _resolve_block(op)
    if isinstance(op, CotaCadeia):
        (ax, ay), (bx, by) = op.pontos[0], op.pontos[-1]
        if math.dist((ax, ay), (bx, by)) <= 0:
            raise AuthoringError("cota_cadeia: o primeiro e o último ponto coincidem")
        ux, uy = _unit((bx - ax, by - ay))
        for p, q in zip(op.pontos, op.pontos[1:], strict=False):
            if (q[0] - p[0]) * ux + (q[1] - p[1]) * uy <= 1e-6:
                raise AuthoringError(f"cota_cadeia: pontos fora de ordem ou repetidos em {p} -> "
                                     f"{q}; liste-os do primeiro ao último ao longo da linha")
    elif isinstance(op, MarcaCorte):
        if math.dist(op.a, op.b) <= 0:
            raise AuthoringError("marca_corte: os dois pontos são iguais")
    elif isinstance(op, Secao):
        if math.dist(op.a, op.b) <= 0:
            raise AuthoringError("secao: os dois pontos são iguais")
    elif isinstance(op, Sprinklers):
        if sum(x is not None for x in (op.sala, op.retangulo, op.poligono)) != 1:
            raise AuthoringError(f"sprinklers {op.nome!r}: informe sala OU retangulo OU poligono")
        if op.retangulo is not None and not (op.retangulo[2] > op.retangulo[0]
                                             and op.retangulo[3] > op.retangulo[1]):
            raise AuthoringError(f"sprinklers {op.nome!r}: retangulo precisa de x1 > x0 e y1 > y0")
    if isinstance(op, Sala):
        if (op.retangulo is None) == (op.poligono is None):
            raise AuthoringError(f"sala {op.nome!r}: informe retangulo OU poligono")
        poly = _room_polygon(op)
        if not poly.is_valid or poly.area <= 0:
            raise AuthoringError(f"sala {op.nome!r}: geometria inválida ou sem área")
    elif isinstance(op, Simbolo):
        resolve_symbol(op)
    elif isinstance(op, Texto):
        if not re.fullmatch(r"[A-Za-z0-9_\-]{1,40}", op.camada):
            raise AuthoringError(f"nome de camada inválido: {op.camada!r}")
    elif isinstance(op, Cota):
        if math.dist(op.a, op.b) <= 0:
            raise AuthoringError("cota com os dois pontos iguais")
    elif isinstance(op, Legenda):
        for key in op.ids or []:
            if simbologia.achar(key) is None:
                raise AuthoringError(f"legenda: {key!r} não existe no catálogo")


def _chop(a: tuple[float, ...], b: tuple[float, ...]) -> list[tuple[tuple[float, float],
                                                                  tuple[float, float]]]:
    """Divide a parede em trechos de até ``WALL_PIECE_M``.

    O leitor do motor só reconhece paredes quando a camada tem ``MIN_WALL_SEGMENTS`` segmentos
    ou mais (heurística contra linhas soltas). Projetos reais têm milhares; uma sala pequena
    desenhada com 8 linhas ficaria de fora. A geometria é idêntica à de linhas inteiras.
    """
    n = max(1, math.ceil(math.dist(a[:2], b[:2]) / WALL_PIECE_M))
    pts = [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
    return list(zip(pts, pts[1:], strict=False))


def _fill_wall(msp, poly: Polygon, layer_name: str, fill: str) -> None:  # noqa: ANN001
    """Preenchimento da parede: sólido (corta-fogo) ou hachura (compartimentação)."""
    from ezdxf import const

    hatch = msp.add_hatch(color=7, dxfattribs={"layer": layer_name})
    if fill == "solid":
        hatch.set_solid_fill()
    else:
        hatch.set_pattern_fill("ANSI31", scale=0.1)
    hatch.paths.add_polyline_path(list(poly.exterior.coords)[:-1], is_closed=True,
                                  flags=const.BOUNDARY_PATH_EXTERNAL)
    for ring in poly.interiors:
        hatch.paths.add_polyline_path(list(ring.coords)[:-1], is_closed=True,
                                      flags=const.BOUNDARY_PATH_OUTERMOST)


def _room_polygon(op: Sala) -> Polygon:
    if op.retangulo is not None:
        x0, y0, x1, y1 = op.retangulo
        if not (x1 > x0 and y1 > y0):
            raise AuthoringError(f"sala {op.nome!r}: retangulo precisa de x1 > x0 e y1 > y0")
        return box(x0, y0, x1, y1)
    return Polygon([tuple(p) for p in op.poligono or []])


def _door_opening(op: Porta) -> BaseGeometry:
    from shapely import affinity

    rect = box(op.x - op.largura_m / 2, op.y - op.corte_m / 2,
               op.x + op.largura_m / 2, op.y + op.corte_m / 2)
    return affinity.rotate(rect, op.angulo_graus, origin=(op.x, op.y))


def _unit(v: tuple[float, float]) -> tuple[float, float]:
    n = math.hypot(*v)
    return v[0] / n, v[1] / n


def _window_opening(op: Janela) -> BaseGeometry:
    from shapely import affinity

    rect = box(op.x - op.largura_m / 2, op.y - (op.espessura_m + 0.1) / 2,
               op.x + op.largura_m / 2, op.y + (op.espessura_m + 0.1) / 2)
    return affinity.rotate(rect, op.angulo_graus, origin=(op.x, op.y))


def _draw_door(msp, op: Porta, escala: int) -> None:  # noqa: ANN001
    """Folha aberta a 90° e arco de giro, com a dobradiça numa das pontas do vão."""
    a = math.radians(op.angulo_graus)
    ux, uy = math.cos(a), math.sin(a)
    side = 1 if op.abre_para == "esquerda" else -1
    hx, hy = op.x - ux * op.largura_m / 2, op.y - uy * op.largura_m / 2
    leaf = (hx - side * uy * op.largura_m, hy + side * ux * op.largura_m)
    attrs = {"layer": "PORTA_CORTA_FOGO" if op.corta_fogo_min else "PORTAS"}
    msp.add_line((hx, hy), leaf, dxfattribs=attrs)
    start = op.angulo_graus
    end = op.angulo_graus + 90 * side
    lo, hi = (start, end) if side > 0 else (end, start)
    msp.add_arc((hx, hy), op.largura_m, lo, hi, dxfattribs=attrs)
    h = apresentacao.altura_texto(escala)
    if op.corta_fogo_min:  # o número do tempo (60/90/120) fica do lado oposto ao giro
        _text(msp, str(op.corta_fogo_min), op.x + side * uy * 0.4, op.y - side * ux * 0.4, h,
              attrs["layer"], True)
    if op.etiqueta:
        dist = 0.3 + (h * 1.6 if op.corta_fogo_min else 0.0)
        _label_along_wall(msp, apresentacao.rotulo_porta(op.largura_m, op.altura_m), op.x, op.y,
                          op.angulo_graus, -side, dist, apresentacao.altura_texto(
                              escala, apresentacao.TEXTO_PEQUENO_MM), "ROTULOS")


def _draw_window(msp, op: Janela, escala: int) -> None:  # noqa: ANN001
    """Caixilho em planta: as duas faces da parede e o vidro ao centro, ao longo do vão."""
    a = math.radians(op.angulo_graus)
    ux, uy = math.cos(a), math.sin(a)
    nx, ny = -uy, ux
    half = op.largura_m / 2
    attrs = {"layer": "JANELAS"}
    for off in (-op.espessura_m / 2, 0.0, op.espessura_m / 2):
        msp.add_line((op.x - ux * half + nx * off, op.y - uy * half + ny * off),
                     (op.x + ux * half + nx * off, op.y + uy * half + ny * off), dxfattribs=attrs)
    if op.etiqueta:
        side = 1 if op.lado_etiqueta == "esquerda" else -1
        _label_along_wall(msp, apresentacao.rotulo_janela(op.largura_m, op.altura_m,
                                                           op.peitoril_m),
                          op.x, op.y, op.angulo_graus, side, op.espessura_m / 2 + 0.25,
                          apresentacao.altura_texto(escala, apresentacao.TEXTO_PEQUENO_MM),
                          "ROTULOS")


def _label_along_wall(msp, texto: str, x: float, y: float, angulo: float,  # noqa: ANN001
                      lado: int, dist: float, h: float, layer: str) -> None:
    """Etiqueta paralela à parede, ``dist`` m ao lado (+1 esquerda, -1 direita) do ponto, com o
    texto sempre legível (nunca de cabeça para baixo)."""
    a = math.radians(angulo)
    px, py = x - lado * math.sin(a) * dist, y + lado * math.cos(a) * dist
    rot = angulo % 180
    if rot > 90:
        rot -= 180
    t = msp.add_text(texto, dxfattribs={"layer": layer, "height": h, "rotation": rot,
                                        "style": apresentacao.ESTILO_TEXTO})
    t.set_placement((px, py), align=TextEntityAlignment.MIDDLE_CENTER)


def _draw_room(msp, op: Sala, escala: int,  # noqa: ANN001
               bicos: list[tuple[float, float, float]] | None = None) -> None:
    poly = _room_polygon(op)
    msp.add_lwpolyline(list(poly.exterior.coords)[:-1], close=True,
                       dxfattribs={"layer": "AMBIENTES"})
    c = poly.representative_point()
    h = apresentacao.altura_texto(escala, 3.0)  # nome do ambiente: 3 mm impressos, serifado
    ha = apresentacao.altura_texto(escala)
    cx, cy = c.x, c.y
    if bicos:  # com sprinklers na sala, o nome sai do caminho dos símbolos dos bicos
        cx, cy = _longe_dos_bicos(poly, c.x, c.y, op, h, ha, bicos)
    _text(msp, op.nome.upper(), cx, cy + (h * 0.8 if op.area_no_desenho else 0.0), h,
          "TEXTOS", True, apresentacao.ESTILO_AMBIENTE)
    if op.area_no_desenho:
        _text(msp, f"{poly.area:.2f} m²".replace(".", ","), cx, cy - ha * 0.9, ha,
              "TEXTOS", True)


def _longe_dos_bicos(poly: Polygon, x: float, y: float, op: Sala, h: float, ha: float,
                     bicos: list[tuple[float, float, float]]) -> tuple[float, float]:
    """Posição do rótulo do ambiente (centro) que não toca nenhum símbolo de bico: tenta o
    centro e, em volta, deslocamentos crescentes; se nenhum servir, fica no centro."""
    largura = max(len(op.nome) * h * 0.75, 7 * ha * 0.75) + 0.3
    altura = (h + ha) * 1.8 + 0.2

    def livre(px: float, py: float) -> bool:
        caixa = box(px - largura / 2, py - altura / 2, px + largura / 2, py + altura / 2)
        if not poly.buffer(-0.2).contains(caixa):
            return False
        for bx, by, rot in bicos:
            hx, hy = (TAMANHO_BICO_M / 2, 0.2) if rot == 0.0 else (0.2, TAMANHO_BICO_M / 2)
            if caixa.intersects(box(bx - hx, by - hy, bx + hx, by + hy)):
                return False
        return True

    if livre(x, y):
        return x, y
    for passo in (0.4, 0.8, 1.2, 1.8, 2.6, 3.6):
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            if livre(x + dx * passo, y + dy * passo):
                return x + dx * passo, y + dy * passo
    return x, y


def _text(msp, s: str, x: float, y: float, h: float, layer: str,  # noqa: ANN001
          centered: bool, style: str = apresentacao.ESTILO_TEXTO) -> None:
    t = msp.add_text(s, dxfattribs={"layer": layer, "height": h, "style": style})
    t.set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER if centered
                    else TextEntityAlignment.LEFT)


def _recuar(p0: tuple[float, float], p1: tuple[float, float], a: float,
            b: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Encurta o segmento ``a`` m no começo e ``b`` m no fim (o símbolo cobre o tubo)."""
    comp = math.dist(p0, p1)
    if comp <= a + b + 1e-9:
        return p0, p0
    ux, uy = (p1[0] - p0[0]) / comp, (p1[1] - p0[1]) / comp
    return (p0[0] + ux * a, p0[1] + uy * a), (p1[0] - ux * b, p1[1] - uy * b)


def _place(doc, msp, entry: Entrada, name: str, layer: str, x: float, y: float,  # noqa: ANN001
           rotation: float, size: float, defined: set[str]) -> None:
    """Define o bloco (uma vez) com o desenho do catálogo e o insere escalado."""
    from coscip_mcp.simbologia import emit

    if name not in defined and name not in doc.blocks:
        emit(doc.blocks.new(name), entry.glyph())
        defined.add(name)
    msp.add_blockref(name, (x, y), dxfattribs={
        "layer": layer, "rotation": rotation, "xscale": size, "yscale": size, "zscale": size})


def _linear_dim(msp, p: tuple[float, float], q: tuple[float, float], ang: float,  # noqa: ANN001
                offset: float, escala: int) -> None:
    """Cota linear de ``p`` a ``q``; a linha de cota fica ``offset`` m à esquerda de ``ang``."""
    nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
    mx, my = (p[0] + q[0]) / 2 + nx * offset, (p[1] + q[1]) / 2 + ny * offset
    dim = msp.add_linear_dim(base=(mx, my), p1=p, p2=q, angle=ang,
                             dimstyle=apresentacao.dimstyle_nome(escala),
                             dxfattribs={"layer": "COTAS"})
    dim.render()


def _draw_dim(msp, op: Cota, escala: int) -> None:  # noqa: ANN001
    (ax, ay), (bx, by) = op.a, op.b
    ang = math.degrees(math.atan2(by - ay, bx - ax))
    _linear_dim(msp, (ax, ay), (bx, by), ang, op.afastamento_m, escala)


def _draw_dim_chain(msp, op: CotaCadeia, escala: int) -> None:  # noqa: ANN001
    pts = [(p[0], p[1]) for p in op.pontos]
    ang = math.degrees(math.atan2(pts[-1][1] - pts[0][1], pts[-1][0] - pts[0][0]))
    sign = 1.0 if op.afastamento_m >= 0 else -1.0
    off = op.afastamento_m
    for p, q in zip(pts, pts[1:], strict=False):
        _linear_dim(msp, p, q, ang, off, escala)
    if op.total and len(pts) > 2:
        _linear_dim(msp, pts[0], pts[-1], ang, off + sign * op.separacao_total_m, escala)


def _draw_section_mark(msp, op: MarcaCorte, escala: int) -> None:  # noqa: ANN001
    """Linha de corte tracejada; em cada ponta, seta para o lado observado e círculo com a letra."""
    f = apresentacao.fator(escala)
    (ax, ay), (bx, by) = op.a, op.b
    ux, uy = _unit((bx - ax, by - ay))
    side = 1.0 if op.sentido == "esquerda" else -1.0
    sx, sy = -uy * side, ux * side  # direção observada
    msp.add_line((ax, ay), (bx, by), dxfattribs={"layer": "CORTES"})
    arm, head, r = 0.9 * f, 0.3 * f, 0.4 * f
    for ex, ey in ((ax, ay), (bx, by)):
        tx, ty = ex + sx * arm, ey + sy * arm
        msp.add_line((ex, ey), (tx, ty), dxfattribs={"layer": "CORTES", "lineweight": 50})
        hatch = msp.add_hatch(color=6, dxfattribs={"layer": "CORTES"})
        hatch.set_solid_fill()
        hatch.paths.add_polyline_path(
            [(tx + sx * head, ty + sy * head),
             (tx + ux * head * 0.45, ty + uy * head * 0.45),
             (tx - ux * head * 0.45, ty - uy * head * 0.45)], is_closed=True)
        cx, cy = tx + sx * (head + r * 1.05), ty + sy * (head + r * 1.05)
        msp.add_circle((cx, cy), r, dxfattribs={"layer": "CORTES", "lineweight": 30})
        _text(msp, op.nome.upper(), cx, cy, apresentacao.altura_texto(escala, 3.5), "CORTES",
              True)


def _draw_section(doc, msp, op: Corte, lay: str, lay_inc: str,  # noqa: ANN001
                  defined: set[str], escala: int = apresentacao.ESCALA_PADRAO) -> None:
    """Corte esquemático: lajes, paredes externas, níveis, cota total e a parte de incêndio.

    Os símbolos da prumada usam blocos com nomes que o dicionário NÃO reconhece (``ESQV_*``):
    o esquema vertical repete os hidrantes da planta e não pode ser contado como equipamento.
    """
    x0, x1, wall = op.x, op.x + op.largura_m, 0.2
    a = {"layer": lay}

    def rect(xa: float, ya: float, xb: float, yb: float, attrs: dict[str, Any] = a) -> None:
        msp.add_lwpolyline([(xa, ya), (xb, ya), (xb, yb), (xa, yb)], close=True, dxfattribs=attrs)

    msp.add_line((x0 - 2.0, op.y - op.laje_m), (x1 + 2.0, op.y - op.laje_m), dxfattribs=a)
    levels = [op.y]
    for pav in op.pavimentos:
        levels.append(levels[-1] + pav.pe_direito_m + op.laje_m)
    for i, pav in enumerate(op.pavimentos):
        z = levels[i]
        rect(x0, z - op.laje_m, x1, z)  # laje de piso
        rect(x0, z, x0 + wall, z + pav.pe_direito_m)
        rect(x1 - wall, z, x1, z + pav.pe_direito_m)
        _text(msp, pav.nome.upper(), (x0 + x1) / 2, z + pav.pe_direito_m / 2, 0.3, lay, True)
        _level_mark(msp, x1 + 3.6, z, z - op.y, lay)
    top = levels[-1]
    rect(x0, top - op.laje_m, x1, top)  # laje de cobertura
    _level_mark(msp, x1 + 3.6, top, top - op.y, lay)
    dim = msp.add_linear_dim(base=(x0 - 1.2, op.y), p1=(x0, op.y), p2=(x0, top), angle=90,
                             dimstyle=apresentacao.dimstyle_nome(escala),
                             dxfattribs={"layer": "COTAS"})
    dim.render()
    _text(msp, op.titulo, (x0 + x1) / 2, op.y - 1.6, 0.4, lay, True)
    _text(msp, "ESQUEMÁTICO, SEM ESCALA DE DETALHE", (x0 + x1) / 2, op.y - 2.2, 0.2, lay, True)

    ai = {"layer": lay_inc}
    tank: tuple[float, float, float, float] | None = None
    if op.reservatorio == "superior":
        tank = (x1 - 4.0, top + 0.3, x1 - 1.0, top + 1.8)
    elif op.reservatorio == "inferior":
        tank = (x0 - 4.5, op.y - op.laje_m - 2.0, x0 - 1.5, op.y - op.laje_m - 0.5)
    if tank:
        rect(*tank, attrs=ai)
        label = "RESERVATÓRIO" + (f" - RTI {op.rti_l:,.0f} L".replace(",", ".")
                                  if op.rti_l else "")
        _text(msp, label, (tank[0] + tank[2]) / 2, tank[3] + 0.3, 0.22, lay_inc, True)
    if op.prumada_hidrantes:
        px = x1 - 1.5
        lo = op.y + 0.3
        hi = top - op.laje_m - 0.3
        if op.reservatorio == "superior" and tank:
            hi = tank[1]
        msp.add_line((px, lo), (px, hi), dxfattribs=ai)
        if op.reservatorio == "inferior" and tank:  # sucção até a prumada, por baixo do piso
            yb = (tank[1] + tank[3]) / 2
            msp.add_lwpolyline([(tank[2], yb), (px, yb), (px, lo)], dxfattribs=ai)
        glyph = simbologia.CATALOGO["HIDRANTE_SIMPLES"]
        for i in range(len(op.pavimentos)):
            zy = levels[i] + 1.2  # registro entre 1,0 e 1,5 m do piso (NT 2-02, 5.6.1 a)
            msp.add_line((px, zy), (px - 0.8, zy), dxfattribs=ai)
            _place(doc, msp, glyph, "ESQV_TOMADA_H", lay_inc, px - 1.1, zy + 0.1, 0.0, 0.5,
                   defined)
            _text(msp, f"H{i + 1}", px - 1.9, zy, 0.2, lay_inc, True)
        rr = simbologia.CATALOGO["REGISTRO_RECALQUE"]
        msp.add_lwpolyline([(px, lo), (x1 + 1.2, lo)], dxfattribs=ai)
        _place(doc, msp, rr, "ESQV_RR", lay_inc, x1 + 1.6, lo, 180.0, 0.6, defined)
        _text(msp, "RR", x1 + 2.3, lo + 0.35, 0.2, lay_inc, True)


def _level_mark(msp, x: float, y: float, level: float, lay: str) -> None:  # noqa: ANN001
    """Marca de nível: triângulo e a cota relativa ao piso do primeiro pavimento."""
    msp.add_lwpolyline([(x, y), (x - 0.15, y + 0.2), (x + 0.15, y + 0.2)], close=True,
                       dxfattribs={"layer": lay})
    msp.add_line((x - 0.5, y), (x + 1.6, y), dxfattribs={"layer": lay})
    sign = "+" if level >= 0 else "-"
    _text(msp, f"{sign}{abs(level):.2f}".replace(".", ","), x + 0.9, y + 0.3, 0.2, lay, True)
