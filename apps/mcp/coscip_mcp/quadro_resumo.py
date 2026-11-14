"""Quadro Resumo do projeto (frente D4, §9 da arquitetura), no modelo do CBMERJ.

A NT 1-01, Parte 1, 5.3.7 h), manda imprimir o Quadro Resumo na planta de situação ou prancha 01,
pelo modelo do Portal do Requerente; o AAST nº 01/2025 (1.3) manda inseri-lo no projeto digital.
O modelo do portal exige login; a estrutura aqui (18 seções, rótulos, ordem e proporção das
colunas) é a da planilha do CBMERJ embutida (OLE) numa prancha aprovada que o usuário enviou em
12/11/2026: IDENTIFICAÇÃO, CLASSIFICAÇÃO (Anexo II), CARGA DE INCÊNDIO (NT 1-04), ELEMENTOS
ESTRUTURAIS (NT 2-19), MEDIDAS DE SEGURANÇA, RISCOS ESPECIAIS, RESERVATÓRIO/RTI, BOMBA (NT 2-04),
HIDRANTES E MANGOTINHOS (NT 2-02), GÁS (NT 3-02), QUADRO DE ÁREAS, EXTINTORES (NT 2-01),
POSICIONAMENTO DOS HIDRANTES, SINALIZAÇÃO (NT 2-05), ILUMINAÇÃO (NT 2-06), DETECÇÃO E ALARME
(NT 2-07), SAÍDAS (NT 2-08) e MATERIAIS DE ACABAMENTO (NT 2-20).

Dois tipos de conteúdo, que nunca se misturam:

- **o que o usuário informa** (endereço, proprietário, classificação, medidas exigidas, RTI,
  bomba, hidrantes, materiais, saídas...): vai como informado; o que faltar fica em branco,
  nada é inventado;
- **o que está desenhado** (extintores por tipo, hidrantes, placas por código e dimensão,
  pontos de iluminação, alarme e detecção, recipientes de GLP): contado do próprio desenho,
  por pavimento.

A contagem é evidência do desenho, não prova de conformidade. ``conferir`` compara essas
contagens com o que o usuário declarou (ex. os extintores calculados) e devolve onde divergem:
``confere``, ``diverge`` ou ``sem dado declarado``.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from typing import Any, Literal

from ezdxf.enums import TextEntityAlignment
from pydantic import BaseModel, ConfigDict, Field

from coscip_mcp import apresentacao

FUNDO_SECAO = (238, 236, 225)  # cor do cabeçalho das seções no modelo (RGB)
LARGURA_MM = 180.0  # largura da tabela impressa
LINHA_MM = 5.0
TEXTO_MM = 2.0
# Larguras das 8 colunas do modelo (unidades da planilha): a grade do quadro inteiro.
COLUNAS = (2019, 8846, 5518, 7907, 5717, 5717, 6286, 8078)
FONTE_MODELO = ("modelo do Quadro Resumo do CBMERJ (planilha 'Principal' embutida numa prancha "
                "aprovada; NT 1-01, Parte 1, 5.3.7 h; AAST 01/2025, 1.3)")


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Identificacao(_M):
    endereco: str = ""
    proprietario: str = ""
    responsavel_tecnico: str = ""
    conselho_tecnico: str = ""  # ex. CREA-RJ
    numero_matricula: str = ""
    decreto_adotado: str = ""
    altura_m: str = ""
    numero_de_pavimentos: str = ""
    ocupacao_do_subsolo: str = ""
    anterior_ao_decreto: bool | None = None
    ano_de_construcao: str = ""
    lotacao_prevista: str = ""
    condicionamento_de_ar: str = ""


class Classificacao(_M):
    grupo: str = ""
    ocupacao: str = ""
    divisao: str = ""
    descricao: str = ""
    risco: str = ""
    carga_de_incendio_mj_m2: str = ""


class Estruturais(_M):
    estrutura_portante: str = ""
    estrutura_da_cobertura: str = ""
    profundidade_do_subsolo_m: str = ""
    trrf: str = ""
    aplicacao_de_revestimento: bool | None = None
    material_de_protecao: str = ""


class VolumeRti(_M):
    sistema: str = Field(description="ex. HID, SPK")
    volume_l: str = ""


class Reservatorio(_M):
    localizacao: str = ""  # Superior, Inferior...
    tipo_de_succao: str = ""  # Positiva, Negativa
    volume_do_reservatorio_l: str = ""
    rti: list[VolumeRti] = Field(default_factory=list, max_length=6)
    rti_total_l: str = ""


class Bomba(_M):
    funcao: str = Field(default="Principal", description="Principal, Reserva, Jockey...")
    tipo: str = ""  # Elétrica, Combustão
    vazao_l_min: str = ""
    pressao_mca: str = ""


class SistemaHidrantes(_M):
    classificacao_de_risco: str = ""
    diametro_succao_mm: str = ""
    diametro_recalque_mm: str = ""
    diametro_mangueira_mm: str = ""
    tipo_mangueira: str = ""
    tipo_esguicho: str = ""
    hidrante_de_recalque: str = ""


class Gas(_M):
    abastecimento: str = Field(default="", description="GLP, GN ou 'não abastecida por gás "
                               "combustível' (NT 1-01, 5.3.8 i)")
    estacionario_capacidade_kg: str = ""
    estacionario_quantidade: str = ""
    transportavel_capacidade_kg: str = ""
    transportavel_quantidade: str = ""


class Acabamento(_M):
    elemento: str = Field(description="Piso, Paredes / Divisórias, Tetos / Forros ou Fachadas")
    acabamento: str = ""
    classe_do_acabamento: str = ""
    revestimento: str = ""
    classe_do_revestimento: str = ""
    retardante_de_chamas: str = ""


class Saidas(_M):
    lotacao: str = ""
    tipo_de_edificacao: str = ""
    grupo_e_divisao: str = ""
    pavimento: str = ""
    com_chuveiros_ou_detectores: bool | None = None
    saida_unica: bool | None = None
    tipo_de_escada: str = ""  # não há no modelo do CBMERJ: fica no memorial
    capacidade_da_unidade_de_passagem: str = ""
    unidades_de_passagem_projetadas: str = ""


class Declarado(_M):
    """Valores que o usuário (ou o cálculo) já fixou, para conferir com o desenho."""

    extintores: int | None = Field(default=None, ge=0, description="total calculado")
    saidas: int | None = Field(default=None, ge=0, description="número de saídas previstas")
    pontos_de_iluminacao: int | None = Field(default=None, ge=0)
    glp_kg: float | None = Field(default=None, ge=0, description="capacidade total de GLP")
    atc_m2: float | None = Field(default=None, gt=0, description="área total construída")


class PavimentoQuadro(_M):
    nome: str = Field(min_length=1, max_length=30)
    janela: list[float] | None = Field(default=None, min_length=4, max_length=4,
                                       description="[x0, y0, x1, y1] em metros; sem ela, tudo")
    atc_m2: float | None = Field(default=None, gt=0)


class QuadroResumo(_M):
    """Tabela do Quadro Resumo desenhada no model space (canto superior esquerdo em ``x, y``),
    na escala de impressão da planta; ver o módulo."""

    tipo: Literal["quadro_resumo"]
    x: float
    y: float
    pavimentos: list[PavimentoQuadro] = Field(default_factory=lambda: [PavimentoQuadro(
        nome="Térreo")], min_length=1, max_length=8)
    identificacao: Identificacao = Field(default_factory=Identificacao)
    classificacao: Classificacao = Field(default_factory=Classificacao)
    estruturais: Estruturais = Field(default_factory=Estruturais)
    tabela_anexo_iii: str = Field(default="", description="tabela adotada do Anexo III")
    medidas_de_seguranca: list[str] = Field(default_factory=list, max_length=30)
    riscos_especiais: list[str] = Field(default_factory=list, max_length=12)
    reservatorio: Reservatorio = Field(default_factory=Reservatorio)
    bombas: list[Bomba] = Field(default_factory=list, max_length=4)
    hidrantes: SistemaHidrantes = Field(default_factory=SistemaHidrantes)
    gas: Gas = Field(default_factory=Gas)
    acabamentos: list[Acabamento] = Field(default_factory=list, max_length=12)
    saidas: Saidas = Field(default_factory=Saidas)
    declarado: Declarado = Field(default_factory=Declarado)


# --- contagem do desenho ----------------------------------------------------------------------

Contagem = dict[str, dict[str, int]]  # rótulo -> {pavimento: quantidade}


@dataclass
class Contagens:
    """O que o desenho tem, por pavimento. Preenchido pelo autoria.py."""

    pavimentos: list[str]
    extintores: Contagem = field(default_factory=dict)
    sinalizacao: dict[tuple[str, str], dict[str, int]] = field(default_factory=dict)
    iluminacao: Contagem = field(default_factory=dict)
    hidrantes: Contagem = field(default_factory=dict)
    alarme: Contagem = field(default_factory=dict)
    recipientes_glp: dict[str, dict[str, int]] = field(default_factory=dict)  # "P-45 (45 kg)"
    area_util: dict[str, float] = field(default_factory=dict)
    saidas_desenhadas: int = 0
    placas_de_saida: int = 0  # S-12 e S-14

    def total(self, tabela: Contagem) -> int:
        return sum(sum(v.values()) for v in tabela.values())

    def total_glp_kg(self) -> float:
        return sum(_kg(r) * sum(v.values()) for r, v in self.recipientes_glp.items())


def _kg(rotulo: str) -> float:
    inicio = rotulo.rfind("(")
    try:
        return float(rotulo[inicio + 1:].split()[0].replace(",", "."))
    except (ValueError, IndexError):
        return 0.0


def conferir(op: QuadroResumo, c: Contagens) -> list[dict[str, Any]]:
    """Consistência entre o desenho e o declarado. Não é verificação de conformidade."""
    d = op.declarado
    out: list[dict[str, Any]] = []

    def item(nome: str, desenho: Any, declarado: Any, ok: bool | None, nota: str = "") -> None:
        situacao = "sem dado declarado" if ok is None else ("confere" if ok else "diverge")
        out.append({"item": nome, "desenho": desenho, "declarado": declarado,
                    "situacao": situacao, **({"nota": nota} if nota else {})})

    ext = c.total(c.extintores)
    item("extintores", ext, d.extintores, None if d.extintores is None else ext >= d.extintores,
         "o desenho precisa ter pelo menos os calculados (extras, como o classe K, são aceitos)")
    item("saídas", c.saidas_desenhadas, d.saidas,
         None if d.saidas is None else c.saidas_desenhadas >= d.saidas)
    item("placa de saída (S-12/S-14) por saída", c.placas_de_saida, c.saidas_desenhadas,
         None if not c.saidas_desenhadas else c.placas_de_saida >= c.saidas_desenhadas,
         "cada saída desenhada deve ter sua placa; o declarado aqui é o número de saídas")
    luz = c.total(c.iluminacao)
    item("pontos de iluminação de emergência", luz, d.pontos_de_iluminacao,
         None if d.pontos_de_iluminacao is None else luz >= d.pontos_de_iluminacao)
    glp = c.total_glp_kg()
    item("GLP (kg)", glp, d.glp_kg, None if d.glp_kg is None else abs(glp - d.glp_kg) < 0.5)
    util = round(sum(c.area_util.values()), 2)
    atc = d.atc_m2 or sum(p.atc_m2 or 0 for p in op.pavimentos) or None
    item("área útil dos ambientes não passa da área construída", util, atc,
         None if atc is None else util <= atc + 1e-6)
    return out


# --- desenho da tabela -------------------------------------------------------------------------

Celula = tuple[str, int, int]  # texto, coluna inicial, coluna final (exclusiva) da grade


class _Tabela:
    """Grade de 8 colunas nas proporções do modelo; cada linha tem células que ocupam colunas
    inteiras. Os quadros por pavimento dividem a parte direita em colunas iguais."""

    def __init__(self, msp, x: float, y: float, escala: int) -> None:  # noqa: ANN001
        k = escala / 1000.0  # metros de desenho por mm de papel
        self.msp, self.x, self.y = msp, x, y
        self.W = LARGURA_MM * k
        self.row = LINHA_MM * k
        self.h = TEXTO_MM * k
        self.pad = 1.0 * k
        tot = sum(COLUNAS)
        self.xs = [x]
        for c in COLUNAS:
            self.xs.append(self.xs[-1] + self.W * c / tot)

    def _line(self, x0: float, y0: float, x1: float, y1: float) -> None:
        self.msp.add_line((x0, y0), (x1, y1), dxfattribs={"layer": "QUADRO"})

    def _texto(self, s: str, x: float, y: float, *, centro: bool = False,
               h: float | None = None) -> None:
        t = self.msp.add_text(s, dxfattribs={"layer": "QUADRO", "height": h or self.h,
                                             "style": apresentacao.ESTILO_TEXTO})
        t.set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER if centro
                        else TextEntityAlignment.MIDDLE_LEFT)

    def titulo(self, texto: str) -> None:
        self._texto(texto, self.x + self.W / 2, self.y - self.row * 0.7, centro=True,
                    h=self.h * 2.2)
        self.y -= self.row * 1.4

    def secao(self, texto: str, destaque: bool = True) -> None:
        """Cabeçalho de seção (as cinco primeiras do modelo têm fundo; as demais não)."""
        if destaque:
            from ezdxf import colors

            pts = [(self.x, self.y), (self.x + self.W, self.y),
                   (self.x + self.W, self.y - self.row), (self.x, self.y - self.row)]
            hatch = self.msp.add_hatch(color=7, dxfattribs={"layer": "QUADRO"})
            hatch.set_solid_fill(color=7, rgb=colors.RGB(*FUNDO_SECAO))
            hatch.paths.add_polyline_path(pts, is_closed=True)
        self.linha([(texto, 0, 8)], centro=True)

    def linha(self, cels: list[tuple[str, float, float]] | list[Celula], *,
              centro: bool = False, alinhar: str | None = None,
              xs: list[float] | None = None) -> None:
        """Uma linha: células ``(texto, c0, c1)`` sobre as fronteiras ``xs`` (a grade do
        modelo, por padrão); quebra o texto e cresce a linha. ``alinhar``: uma letra por célula,
        ``c`` centralizada e ``l`` à esquerda (sobrepõe ``centro``)."""
        xs = xs or self.xs
        quebradas: list[list[str]] = []
        for txt, c0, c1 in cels:
            larg = xs[int(c1)] - xs[int(c0)]
            cpl = max(4, int((larg - 2 * self.pad) / (self.h * 0.66)))
            quebradas.append(textwrap.wrap(str(txt), cpl) or [""])
        n = max(len(q) for q in quebradas)
        altura = self.row * (1 if n == 1 else 0.45 + 0.5 * n)
        y_top, y_bot = self.y, self.y - altura
        self._line(xs[0], y_top, xs[-1], y_top)
        self._line(xs[0], y_bot, xs[-1], y_bot)
        bordas = {xs[0], xs[-1]}
        for _, c0, c1 in cels:
            bordas |= {xs[int(c0)], xs[int(c1)]}
        for xv in bordas:
            self._line(xv, y_top, xv, y_bot)
        for j, ((_, c0, c1), q) in enumerate(zip(cels, quebradas, strict=True)):
            xa, xb = xs[int(c0)], xs[int(c1)]
            centrada = centro if alinhar is None or j >= len(alinhar) else alinhar[j] == "c"
            for i, ln in enumerate(q):
                yy = y_top - altura / 2 + (len(q) - 1) / 2 * self.h * 1.35 - i * self.h * 1.35
                if centrada:
                    self._texto(ln, (xa + xb) / 2, yy, centro=True)
                else:
                    self._texto(ln, xa + self.pad, yy)
        self.y = y_bot

    def grade_pav(self, n_pav: int, rotulo_ate: int = 3) -> list[float]:
        """Fronteiras para quadros por pavimento: as colunas do modelo até ``rotulo_ate`` e o
        resto dividido em ``n_pav`` + 1 (total) colunas iguais."""
        base = self.xs[:rotulo_ate + 1]
        passo = (self.xs[-1] - base[-1]) / (n_pav + 1)
        return base + [base[-1] + passo * (i + 1) for i in range(n_pav + 1)]

    def rodape(self, texto: str) -> None:
        self.y -= self.row * 0.5
        h = self.h * 0.9
        for ln in textwrap.wrap(texto, max(10, int(self.W / (h * 0.7)))):
            self._texto(ln, self.x, self.y, h=h)
            self.y -= self.row * 0.7
        self.y -= self.row * 0.3


def _marca(v: bool | None) -> tuple[str, str]:
    """``SIM (  )`` / ``NÃO (  )`` com o X só no que foi informado."""
    return (f"SIM ({' X ' if v is True else '   '})", f"NÃO ({' X ' if v is False else '   '})")


def _n(v: int) -> str:
    return str(v) if v else ""


def desenhar(doc, msp, op: QuadroResumo, c: Contagens, escala: int) -> dict[str, Any]:  # noqa: ANN001, C901, PLR0915
    """Desenha o quadro e devolve o resumo (altura, contagens e conferência)."""
    from coscip_mcp import simbologia

    apresentacao.criar_camada(doc, "QUADRO")
    t = _Tabela(msp, op.x, op.y, escala)
    pavs = c.pavimentos
    npv = len(pavs)
    i, cl, es = op.identificacao, op.classificacao, op.estruturais

    t.titulo("QUADRO RESUMO")
    t.secao("IDENTIFICAÇÃO DA EDIFICAÇÃO E/OU ÁREA DE RISCO")
    t.linha([(f"Endereço: {i.endereco}", 0, 8)])
    t.linha([(f"Proprietário: {i.proprietario}", 0, 8)])
    t.linha([(f"Responsável técnico de segurança: {i.responsavel_tecnico}", 0, 8)])
    t.linha([(f"Conselho Técnico: {i.conselho_tecnico}", 0, 4),
             (f"nº de matrícula: {i.numero_matricula}", 4, 8)])
    t.linha([(f"Decreto Estadual adotado (nº e ano): {i.decreto_adotado}", 0, 2),
             (f"Altura (m): {i.altura_m}", 2, 3),
             (f"Nº de pavimentos: {i.numero_de_pavimentos}", 3, 4),
             (f"Ocupação do subsolo: {i.ocupacao_do_subsolo}", 4, 8)])
    sim, nao = _marca(i.anterior_ao_decreto)
    t.linha([("Edificação construída ou licenciada anterior à vigência do Decreto nº "
              "42/2018:", 0, 3), (f"{sim}  {nao}", 3, 4),
             (f"Ano da construção ou do licenciamento: {i.ano_de_construcao}", 4, 8)])
    t.linha([("Lotação prevista (apenas para áreas que desenvolvam ocupação do Grupo F): "
              f"{i.lotacao_prevista}", 0, 8)])
    t.linha([("Descreva como se dá o sistema de condicionamento de ar da edificação (central "
              f"de ar, split, etc.): {i.condicionamento_de_ar}", 0, 8)])

    t.secao("CLASSIFICAÇÃO – Decreto Estadual nº 42/2018 - Anexo II")
    t.linha([("Grupo", 0, 2), ("Ocupação", 2, 3), ("Divisão", 3, 4), ("Descrição", 4, 8)],
            centro=True)
    t.linha([(cl.grupo, 0, 2), (cl.ocupacao, 2, 3), (cl.divisao, 3, 4), (cl.descricao, 4, 8)],
            centro=True)
    t.secao("CLASSIFICAÇÃO DAS EDIFICAÇÕES E ÁREAS DE RISCO QUANTO A CARGA DE INCÊNDIO – "
            "NT 1-04")
    t.linha([("Risco", 0, 3), ("Carga de incêndio (MJ/m²) (Apenas para o grupo J)", 3, 8)],
            centro=True)
    t.linha([(cl.risco, 0, 3), (cl.carga_de_incendio_mj_m2, 3, 8)], centro=True)

    t.secao("ELEMENTOS ESTRUTURAIS – NT 2-19")
    t.linha([("Estrutura portante (ex: concreto, aço, madeira, outros): "
              f"{es.estrutura_portante}", 0, 8)])
    t.linha([("Estrutura de sustentação da cobertura (ex: concreto, aço, madeira, outros): "
              f"{es.estrutura_da_cobertura}", 0, 8)])
    t.linha([(f"Profundidade do subsolo (m): {es.profundidade_do_subsolo_m}", 0, 3),
             (f"TRRF: {es.trrf}", 3, 8)])
    sim, nao = _marca(es.aplicacao_de_revestimento)
    t.linha([("Aplicação de revestimento", 0, 2), (f"{sim}  {nao}", 2, 3),
             (f"Tipo de material de proteção: {es.material_de_protecao} (Conforme modelo do "
              "Anexo E, da NT 2-19)", 3, 8)])

    t.secao("MEDIDAS DE SEGURANÇA CONTRA INCÊNDIO – DECRETO Nº 42/2018")
    t.linha([("", 0, 1), ("Tabela adotada, conforme anexo III do Decreto nº 42/2018", 1, 3),
             (op.tabela_anexo_iii, 3, 8)])
    for m in op.medidas_de_seguranca:
        t.linha([("X", 0, 1), (m, 1, 8)], alinhar="cl")
    if not op.medidas_de_seguranca:
        t.linha([("", 0, 1), ("(nenhuma medida informada)", 1, 8)])
    t.secao("RISCOS ESPECIAIS – DECRETO Nº 42/2018")
    for m in op.riscos_especiais:
        t.linha([("X", 0, 1), (m, 1, 8)], alinhar="cl")
    if not op.riscos_especiais:
        t.linha([("", 0, 1), ("(nenhum risco especial informado)", 1, 8)])

    r = op.reservatorio
    t.secao("RESERVATÓRIO/RTI", destaque=False)
    t.linha([("Localização", 0, 2), ("Tipo de Sucção", 2, 3), ("Vol. do Reservatório", 3, 4),
             ("Vol. da RTI (Litros)", 4, 8)], centro=True)
    t.linha([(r.localizacao, 0, 2), (r.tipo_de_succao, 2, 3),
             (r.volume_do_reservatorio_l, 3, 4), ("", 4, 8)], centro=True)
    for v in r.rti:
        t.linha([("", 0, 4), (v.sistema, 4, 5), (v.volume_l, 5, 8)], centro=True)
    if r.rti or r.rti_total_l:
        t.linha([("", 0, 4), ("TOTAL", 4, 5), (r.rti_total_l, 5, 8)], centro=True)

    t.secao("BOMBA DE INCÊNDIO – NT 2-04", destaque=False)
    t.linha([("", 0, 2), ("Tipo", 2, 3), ("Vazão (L/MIN)", 3, 4), ("Pressão (MCA)", 4, 8)],
            centro=True)
    for b in op.bombas or [Bomba(funcao="")]:
        t.linha([(b.funcao, 0, 2), (b.tipo, 2, 3), (b.vazao_l_min, 3, 4),
                 (b.pressao_mca, 4, 8)], centro=True)

    h = op.hidrantes
    t.secao("SISTEMA DE HIDRANTES E MANGOTINHOS – NT 2-02", destaque=False)
    for rot, val in (("Classificação de Risco", h.classificacao_de_risco),
                     ("Diâmetro da Tubulação de Sucção (mm)", h.diametro_succao_mm),
                     ("Diâmetro da Tubulação Recalque (mm)", h.diametro_recalque_mm),
                     ("Diâmetro da Mangueira (mm)", h.diametro_mangueira_mm),
                     ("Tipo da Mangueira", h.tipo_mangueira),
                     ("Tipo de Esguicho", h.tipo_esguicho),
                     ("Hidrante de Recalque", h.hidrante_de_recalque)):
        t.linha([(rot, 0, 3), (val, 3, 8)], alinhar="lc")

    g = op.gas
    t.secao("GÁS GLP/GN – NT 3-02", destaque=False)
    t.linha([(f"Abastecimento por gás combustível: {g.abastecimento}", 0, 8)])
    t.linha([("Tipo de Cilindro/Botijão", 0, 3), ("Capacidade Individual", 3, 4),
             ("Nº de Cilindros", 4, 5), ("Capacidade Total", 5, 8)], centro=True)

    def _tot(cap: str, qt: str) -> str:
        try:
            return f"{float(cap.replace(',', '.')) * float(qt.replace(',', '.')):g}"
        except ValueError:
            return ""

    t.linha([("Estacionário (Kg)", 0, 3), (g.estacionario_capacidade_kg, 3, 4),
             (g.estacionario_quantidade, 4, 5),
             (_tot(g.estacionario_capacidade_kg, g.estacionario_quantidade), 5, 8)],
            alinhar="lccc")
    if c.recipientes_glp:  # o que está desenhado
        for rot, por in c.recipientes_glp.items():
            n, kg = sum(por.values()), _kg(rot)
            # "Transportável P-45", não só "P-45": o leitor leria a célula como a placa P-45
            t.linha([(f"Transportável {rot.split(' (')[0]} (Kg)", 0, 3), (f"{kg:g}", 3, 4),
                     (str(n), 4, 5), (f"{kg * n:g}", 5, 8)], alinhar="lccc")
    else:
        t.linha([("Transportável (Kg)", 0, 3), (g.transportavel_capacidade_kg, 3, 4),
                 (g.transportavel_quantidade, 4, 5),
                 (_tot(g.transportavel_capacidade_kg, g.transportavel_quantidade), 5, 8)],
                alinhar="lccc")

    gp = t.grade_pav(npv)
    cab_pav = [("Descrição", 0, 3)] + [(p, 3 + j, 4 + j) for j, p in enumerate(pavs)] + [
        ("Total", 3 + npv, 4 + npv)]

    def linha_pav(rotulo: str, valores: list[str], total: str) -> None:
        t.linha([(rotulo, 0, 3)] + [(v, 3 + j, 4 + j) for j, v in enumerate(valores)]
                + [(total, 3 + npv, 4 + npv)], alinhar="l" + "c" * (npv + 1), xs=gp)

    def contagem(rotulo: str, por: dict[str, int]) -> None:
        linha_pav(rotulo, [_n(por.get(p, 0)) for p in pavs], str(sum(por.values())))

    t.secao("QUADRO DE ÁREAS", destaque=False)
    t.linha(cab_pav, centro=True, xs=gp)
    atc_por = {p.nome: p.atc_m2 for p in op.pavimentos}
    atc_tot = op.declarado.atc_m2 or sum(v for v in atc_por.values() if v) or None
    linha_pav("ATC (m²)", [f"{atc_por[p]:.2f}".replace(".", ",") if atc_por.get(p) else ""
                           for p in pavs],
              f"{atc_tot:.2f}".replace(".", ",") if atc_tot else "")

    t.secao("SISTEMA DE PROTEÇÃO POR EXTINTORES – NT 2-01", destaque=False)
    t.linha([("Tipo e capacidade", 0, 3)] + cab_pav[1:], centro=True, xs=gp)
    for rot, por in c.extintores.items():
        contagem(rot, por)
    if not c.extintores:
        t.linha([("(nenhum extintor desenhado)", 0, 8)])
    linha_pav("Total", [_n(sum(v.get(p, 0) for v in c.extintores.values())) for p in pavs],
              str(c.total(c.extintores)))

    t.secao("POSICIONAMENTO DOS HIDRANTES – NT 2-02", destaque=False)
    t.linha([("", 0, 3)] + cab_pav[1:], centro=True, xs=gp)
    for rot, por in c.hidrantes.items():
        contagem(rot, por)
    if not c.hidrantes:
        t.linha([("(nenhum hidrante desenhado)", 0, 8)])

    t.secao("SISTEMA DE SINALIZAÇÃO DE EMERGÊNCIA – NT 2-05", destaque=False)
    gs = t.grade_pav(npv)  # Código (0-2) | Dimensões (2-3) | pavimentos | Total
    t.linha([("Código da Placa", 0, 2), ("Dimensões (mm)", 2, 3)] + cab_pav[1:], centro=True,
            xs=gs)
    ordem = {"P": 0, "A": 1, "S": 2, "E": 3, "M": 4}  # a ordem do modelo e da legenda

    def chave(item: tuple[tuple[str, str], dict[str, int]]) -> tuple[int, int, str]:
        cod, dim = item[0]
        num = cod.split("-")[-1]
        return ordem.get(cod[:1].upper(), 9), int(num) if num.isdigit() else 99, dim

    for (cod, dim), por in sorted(c.sinalizacao.items(), key=chave):
        ent = simbologia.achar(cod)
        # "Placa E-5", não só "E-5": o leitor do motor leria a célula como a placa
        nome = f"Placa {cod}" if ent else cod
        t.linha([(nome, 0, 2), (dim, 2, 3)] + [(_n(por.get(p, 0)), 3 + j, 4 + j)
                                                  for j, p in enumerate(pavs)]
                + [(str(sum(por.values())), 3 + npv, 4 + npv)], alinhar="cc" + "c" * (npv + 1),
                xs=gs)
    if not c.sinalizacao:
        t.linha([("(nenhuma placa desenhada)", 0, 8)])

    t.secao("SISTEMA DE ILUMINAÇÃO DE EMERGÊNCIA – NT 2-06", destaque=False)
    t.linha([("Tipo", 0, 3)] + cab_pav[1:], centro=True, xs=gp)
    for rot, por in c.iluminacao.items():
        contagem(rot, por)
    if not c.iluminacao:
        t.linha([("(nenhum ponto de iluminação desenhado)", 0, 8)])

    t.secao("SISTEMA DE DETECÇÃO E ALARME DE INCÊNDIO – NT 2-07", destaque=False)
    t.linha([("Componente", 0, 3)] + cab_pav[1:], centro=True, xs=gp)
    for rot, por in c.alarme.items():
        contagem(rot, por)
    if not c.alarme:
        t.linha([("(nenhum componente de alarme ou detecção desenhado)", 0, 8)])

    s = op.saidas
    t.secao("SAÍDAS DE EMERGÊNCIA – NT 2-08", destaque=False)
    t.linha([("Lotação:", 0, 3), (s.lotacao, 3, 8)])
    t.linha([("Tipo de edificação", 0, 2), ("Grupo e divisão", 2, 3), ("Pavimento", 3, 4),
             ("Sem chuveiros ou sem detectores automáticos", 4, 6),
             ("Com chuveiros ou com detectores automáticos", 6, 8)], centro=True)
    # espaço não separável: a quebra nunca deixa "saída" sozinha numa linha (o leitor do motor
    # leria o texto como uma saída de emergência)
    mais = "Mais de uma saída"
    t.linha([("", 0, 4), ("Saída única", 4, 5), (mais, 5, 6),
             ("Saída única", 6, 7), (mais, 7, 8)], centro=True)
    marca = ["", "", "", ""]
    if s.com_chuveiros_ou_detectores is not None and s.saida_unica is not None:
        marca[2 * int(s.com_chuveiros_ou_detectores) + int(not s.saida_unica)] = "X"
    t.linha([(s.tipo_de_edificacao, 0, 2), (s.grupo_e_divisao, 2, 3), (s.pavimento, 3, 4)]
            + [(m, 4 + j, 5 + j) for j, m in enumerate(marca)], centro=True)
    t.linha([("Capacidade de unidade de passagem:", 0, 3),
             (s.capacidade_da_unidade_de_passagem, 3, 8)])
    t.linha([("Número de unidade de passagem projetada:", 0, 3),
             (s.unidades_de_passagem_projetadas, 3, 8)])

    t.secao("CONTROLE DE MATERIAIS DE ACABAMENTO E REVESTIMENTO - NT 2-20", destaque=False)
    t.linha([("", 0, 3), ("Material", 3, 4), ("Classificação", 4, 5),
             ("Retardante de chamas", 5, 8)], centro=True)
    padrao = ("Piso", "Paredes / Divisórias", "Tetos / Forros", "Fachadas")
    por_el = {a.elemento.casefold(): a for a in op.acabamentos}
    elementos = list(padrao) + [a.elemento for a in op.acabamentos
                                if a.elemento.casefold() not in {p.casefold() for p in padrao}]
    for el in elementos:
        a = por_el.get(el.casefold()) or Acabamento(elemento=el)
        t.linha([(el, 0, 2), ("Acabamento", 2, 3), (a.acabamento, 3, 4),
                 (a.classe_do_acabamento, 4, 5), (a.retardante_de_chamas, 5, 8)],
                alinhar="llccc")
        t.linha([("", 0, 2), ("Revestimento", 2, 3), (a.revestimento, 3, 4),
                 (a.classe_do_revestimento, 4, 5), (a.retardante_de_chamas, 5, 8)],
                alinhar="llccc")
    t.rodape("Rascunho gerado pelo motor COSCIP no modelo do Quadro Resumo do CBMERJ: dados "
             "informados pelo usuário e contagens do desenho; sem valor normativo.")

    return {"altura_m": round(op.y - t.y, 3), "largura_m": round(t.W, 3),
            "modelo": FONTE_MODELO,
            "contagens": {"extintores": c.total(c.extintores),
                          "placas": sum(sum(v.values()) for v in c.sinalizacao.values()),
                          "iluminacao": c.total(c.iluminacao),
                          "hidrantes": c.total(c.hidrantes), "alarme": c.total(c.alarme),
                          "glp_kg": c.total_glp_kg(),
                          "saidas_desenhadas": c.saidas_desenhadas,
                          "area_util_m2": round(sum(c.area_util.values()), 2)},
            "conferencia": conferir(op, c)}


__all__ = ["Contagens", "QuadroResumo", "conferir", "desenhar"]
