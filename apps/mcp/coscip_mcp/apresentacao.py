"""Padrão de apresentação do desenho gerado pelo motor (frente D1, docs/arquitetura-projeto.md §9).

A convenção foi medida em um projeto digital real de restaurante enviado ao CBMERJ: camadas com
cor e espessura de linha, texto de 2,5 mm impresso, cotas em metros com vírgula e tiques
arquitetônicos, e estilos nomeados pela escala de impressão (``COSCIP-100``). Nada foi copiado
do arquivo real; só se mediu como ele é apresentado.

O desenho continua em METROS no model space. A escala de impressão (denominador, ex. 100) só
decide o tamanho de texto, cota e símbolos auxiliares, para que, impresso nessa escala, tenham o
tamanho certo no papel: altura no desenho = altura impressa (mm) × escala / 1000.

As camadas e seus nomes são os que o leitor do motor já reconhece; este módulo só acrescenta cor,
espessura e tipo de linha. Camadas fora da tabela recebem o padrão (preta, 0,25 mm). As cores
seguem o AAST nº 01/2025 do CBMERJ, item 3.5 (``CORES_AAST``).
"""

from __future__ import annotations

from dataclasses import dataclass

from ezdxf.document import Drawing

ESCALA_PADRAO = 100
ESCALAS = (20, 25, 50, 75, 100, 125, 150, 200, 250, 300, 500)

TEXTO_MM = 2.5  # altura impressa do texto corrente
TEXTO_PEQUENO_MM = 1.8  # etiquetas de vão e legendas auxiliares
TEXTO_TITULO_MM = 5.0

ESTILO_TEXTO = "COSCIP-TEXTO"
ESTILO_AMBIENTE = "COSCIP-AMBIENTE"


@dataclass(frozen=True)
class CamadaPadrao:
    cor: int  # AutoCAD Color Index
    espessura: int  # centésimos de mm; só valores válidos do DXF (13, 18, 25, 30, 35, 50...)
    linetype: str = "Continuous"
    descricao: str = ""
    plotar: bool = True


# Cores das camadas: AAST nº 01/2025 do CBMERJ, item 3.5 (projeto em formato digital):
#   vermelha = extintores e sistemas fixos de extinção; verde = sinalização de orientação e
#   salvamento; azul = iluminação de emergência; roxa = detecção e alarme de incêndio; laranja =
#   demais placas de sinalização e outros sistemas da NT 1-03; preta = demais linhas do desenho,
#   sem relação com as medidas de segurança. Ver ``CORES_AAST``.
VERMELHO, VERDE, AZUL, ROXO, LARANJA, PRETO = 1, 3, 5, 190, 30, 7
CORES_AAST: dict[str, tuple[int, str]] = {
    "vermelha": (VERMELHO, "extintores; sistemas fixos de extinção"),
    "verde": (VERDE, "sinalização de orientação e salvamento"),
    "azul": (AZUL, "iluminação de emergência"),
    "roxa": (ROXO, "detecção e alarme de incêndio"),
    "laranja": (LARANJA, "demais placas de sinalização e outros sistemas da NT 1-03"),
    "preta": (PRETO, "demais linhas do desenho (sem relação com as medidas de segurança)"),
}
FONTE_CORES = "CBMERJ, Aditamento Administrativo de Serviços Técnicos nº 01/2025, item 3.5"

CAMADAS: dict[str, CamadaPadrao] = {
    "PAREDE": CamadaPadrao(PRETO, 50, descricao="paredes comuns"),
    "PAREDE_CORTA_FOGO": CamadaPadrao(LARANJA, 50, descricao="paredes corta-fogo (NT 1-03)"),
    "PAREDE_COMPARTIMENTACAO": CamadaPadrao(LARANJA, 50,
                                            descricao="paredes de compartimentação"),
    "DIVISORIA": CamadaPadrao(PRETO, 18, descricao="divisórias"),
    "PORTAS": CamadaPadrao(PRETO, 25, descricao="portas: folha e arco de giro"),
    "PORTA_CORTA_FOGO": CamadaPadrao(LARANJA, 35, descricao="portas corta-fogo P-60/90/120"),
    "JANELAS": CamadaPadrao(PRETO, 25, descricao="janelas"),
    "ROTULOS": CamadaPadrao(PRETO, 13, descricao="etiquetas de portas e janelas (80x210)"),
    "MOBILIARIO": CamadaPadrao(PRETO, 13, descricao="mobiliário, louças e equipamentos"),
    "PILARES": CamadaPadrao(PRETO, 50, descricao="pilares"),
    "ESCADA": CamadaPadrao(PRETO, 25, descricao="escadas"),
    "QUADRO": CamadaPadrao(PRETO, 18, descricao="Quadro Resumo (tabela)"),
    "FOLHA": CamadaPadrao(PRETO, 50, descricao="moldura, carimbo e quadros da prancha"),
    "VIEWPORT": CamadaPadrao(6, 13, descricao="janelas de visualização (não plotam)",
                             plotar=False),
    "AMBIENTES": CamadaPadrao(8, 13, descricao="contorno dos ambientes"),
    "TEXTOS": CamadaPadrao(PRETO, 13, descricao="textos e nomes dos ambientes"),
    "COTAS": CamadaPadrao(PRETO, 13, descricao="cotas"),
    "LEGENDA": CamadaPadrao(PRETO, 13, descricao="legendas: tabelas, textos e molduras"),
    "INC_EXT": CamadaPadrao(VERMELHO, 25, descricao="extintores"),
    "INC_HID": CamadaPadrao(VERMELHO, 25, descricao="hidrantes e acessórios"),
    "INC_SPK": CamadaPadrao(VERMELHO, 25, descricao="sprinklers"),
    "INC_ALARME": CamadaPadrao(ROXO, 25, descricao="alarme e detecção"),
    "INC_FIXO": CamadaPadrao(VERMELHO, 25, descricao="sistemas fixos de extinção"),
    "ILUMINACAO": CamadaPadrao(AZUL, 25, descricao="iluminação de emergência"),
    "ROTAS": CamadaPadrao(VERDE, 35, descricao="rotas de fuga"),
    "SINALIZACAO": CamadaPadrao(VERDE, 25,
                                descricao="placas de orientação e salvamento (NT 2-05, S)"),
    "SINAL_EQUIPAMENTOS": CamadaPadrao(
        VERMELHO, 25, descricao="placas de equipamentos de combate e alarme (NT 2-05, E)"),
    "SINAL_DEMAIS": CamadaPadrao(
        LARANJA, 25, descricao="placas de proibição e alerta (NT 2-05, P e A)"),
    "PASSIVOS": CamadaPadrao(LARANJA, 25, descricao="sistemas passivos"),
    "TUBULACAO": CamadaPadrao(VERMELHO, 25, descricao="tubulação de incêndio"),
    "VASOS_TANQUES": CamadaPadrao(LARANJA, 30, descricao="vasos, tanques e central de GLP"),
    "ELETRICO": CamadaPadrao(LARANJA, 25, descricao="sistema elétrico"),
    "FUMACA": CamadaPadrao(LARANJA, 25, descricao="controle de fumaça"),
    "CORTE": CamadaPadrao(7, 35, descricao="corte esquemático"),
    "CORTE_INC": CamadaPadrao(VERMELHO, 25, descricao="incêndio no corte esquemático"),
    "CORTES": CamadaPadrao(PRETO, 30, "DASHDOT", "linha e marcas dos cortes"),
    # vistas derivadas da planta (cortes e fachadas); nomes sem "PAREDE"/"VIDRO"/"JANELA", que o
    # leitor trataria como obstáculo da planta
    "VISTA_CORTE": CamadaPadrao(7, 50, descricao="elementos cortados (hachurados)"),
    "VISTA_CONTORNO": CamadaPadrao(7, 35, descricao="contorno do que se vê além do plano"),
    "VISTA_AUX": CamadaPadrao(8, 13, descricao="traço fino: mobiliário e linhas auxiliares"),
    "VISTA_ESQ": CamadaPadrao(PRETO, 25, descricao="esquadrias em vista (janelas)"),
    "VISTA_PORTA": CamadaPadrao(PRETO, 25, descricao="portas em vista"),
    "VISTA_COTA": CamadaPadrao(7, 13, descricao="cotas das vistas"),
    "VISTA_TEXTO": CamadaPadrao(7, 13, descricao="textos e níveis das vistas"),
    "VISTA_INCENDIO": CamadaPadrao(VERMELHO, 25, descricao="extintores em vista"),
    "VISTA_ILUM": CamadaPadrao(AZUL, 25, descricao="iluminação de emergência em vista"),
    "VISTA_COBERTURA": CamadaPadrao(7, 35, descricao="telhado: cortado e em vista"),
    "VISTA_ESCALA": CamadaPadrao(8, 13, descricao="figura humana de escala nos cortes"),
    "ROTULO_CLASSE": CamadaPadrao(PRETO, 13, descricao="rótulos de classe dos materiais de "
                                  "acabamento (NT 2-20): PISO / PAREDE / TETO CLASSE"),
    # planta de situação
    "SITUACAO_LOTE": CamadaPadrao(PRETO, 50, descricao="divisas do lote"),
    "SITUACAO_EDIF": CamadaPadrao(PRETO, 35, descricao="projeção das edificações (hachurada)"),
    "SITUACAO_RUA": CamadaPadrao(PRETO, 25, descricao="meios-fios, calçadas e interrupções"),
    "SITUACAO_TEXTO": CamadaPadrao(PRETO, 13, descricao="nomes das ruas e textos da situação"),
    "SITUACAO_COTA": CamadaPadrao(PRETO, 13, descricao="cotas do lote e distâncias"),
    "NORTE": CamadaPadrao(PRETO, 25, descricao="indicação do norte"),
    # detalhes de instalação (cores do AAST 3.5 por sistema)
    "DETALHE": CamadaPadrao(PRETO, 35, descricao="detalhes: contornos e elementos cortados"),
    "DETALHE_AUX": CamadaPadrao(8, 13, descricao="detalhes: linhas de chamada e auxiliares"),
    "DETALHE_INC": CamadaPadrao(VERMELHO, 25, descricao="detalhes: extintor, abrigo, recalque"),
    "DETALHE_ILUM": CamadaPadrao(AZUL, 25, descricao="detalhes: iluminação de emergência"),
    "DETALHE_SINAL": CamadaPadrao(VERDE, 25, descricao="detalhes: placas de sinalização"),
    "DETALHE_COTA": CamadaPadrao(PRETO, 13, descricao="detalhes: cotas"),
    "DETALHE_TEXTO": CamadaPadrao(PRETO, 13, descricao="detalhes: títulos, chamadas e notas"),
    "DETALHE_HACH": CamadaPadrao(8, 9, descricao="detalhes: hachuras e preenchimentos"),
    "DETALHE_GLP": CamadaPadrao(LARANJA, 25, descricao="detalhes: central, rede e reguladores "
                                "de GLP"),
    # rede de sprinklers: nomes sem SPRINK/SPK, que o leitor trataria como símbolo
    "INC_CHUV_TUBO": CamadaPadrao(1, 35, descricao="tubulação dos chuveiros automáticos"),
    "INC_CHUV_TEXTO": CamadaPadrao(1, 13, descricao="diâmetros e rótulos dos chuveiros"),
    "INC_CHUV_AREA": CamadaPadrao(VERMELHO, 25, "DASHED", "área de operação remota"),
    "ISO_TUBO": CamadaPadrao(VERMELHO, 35, descricao="isométrico: ramais e subgeral"),
    "ISO_PRUMADA": CamadaPadrao(VERMELHO, 50, descricao="isométrico: geral, prumada e VGA"),
    "ISO_BICO": CamadaPadrao(VERMELHO, 25, descricao="isométrico: bicos"),
    "ISO_TEXTO": CamadaPadrao(7, 13, descricao="isométrico: diâmetros e títulos"),
    "ISO_COTA": CamadaPadrao(7, 13, descricao="isométrico: cotas de altura"),
    "ISO_QUADRO": CamadaPadrao(7, 18, descricao="isométrico: quadro de cálculo hidráulico"),
    "ISO_AUX": CamadaPadrao(8, 13, descricao="isométrico: eixos e legenda"),
}
PADRAO_DESCONHECIDA = CamadaPadrao(7, 25, descricao="camada fora do padrão do motor")

# Placas da NT 2-05 por grupo (letra do código) -> camada, com a cor do AAST 01/2025 (3.5): as de
# orientação e salvamento (S) em verde; as de equipamentos de combate a incêndio e alarme (E),
# que indicam extintores e sistemas fixos, em vermelho, como os próprios extintores; as demais
# (proibição P e alerta A) em laranja.
CAMADA_DA_PLACA = {"S": "SINALIZACAO", "E": "SINAL_EQUIPAMENTOS", "P": "SINAL_DEMAIS",
                   "A": "SINAL_DEMAIS", "M": "SINAL_DEMAIS"}


def camada_placa(codigo: str) -> str:
    """Camada da placa de código ``codigo`` (``E-5``, ``PICTO_S-12``)."""
    c = codigo.strip().upper().removeprefix("PICTO_")
    return CAMADA_DA_PLACA.get(c[:1], "SINAL_DEMAIS")


def cor_placa(codigo: str) -> int:
    """Cor (ACI) da placa: a da sua camada."""
    return CAMADAS[camada_placa(codigo)].cor


def _check_escala(escala: int) -> int:
    if not isinstance(escala, int) or isinstance(escala, bool) or not 10 <= escala <= 1000:
        raise ValueError(f"escala {escala!r}: informe o denominador inteiro (ex. 100 para 1:100)")
    return escala


def altura_texto(escala: int, mm: float = TEXTO_MM) -> float:
    """Altura, em metros no desenho, de um texto que impresso na escala tem ``mm`` de altura."""
    return round(mm * _check_escala(escala) / 1000, 4)


def fator(escala: int) -> float:
    """Fator de tamanho de símbolos e marcas auxiliares (1,0 em 1:100)."""
    return _check_escala(escala) / ESCALA_PADRAO


def dimstyle_nome(escala: int) -> str:
    return f"COSCIP-{_check_escala(escala)}"


def medida(valor_m: float) -> str:
    """Medida em metros com duas casas e vírgula, como nas cotas: 24,00."""
    return f"{valor_m:.2f}".replace(".", ",")


def cm(valor_m: float) -> str:
    return str(round(valor_m * 100))


def rotulo_porta(largura_m: float, altura_m: float) -> str:
    """Etiqueta de porta em cm, largura x altura: 80x210."""
    return f"{cm(largura_m)}x{cm(altura_m)}"


def rotulo_janela(largura_m: float, altura_m: float, peitoril_m: float) -> str:
    """Etiqueta de janela em cm, largura x altura / peitoril: 150x120/90."""
    return f"{cm(largura_m)}x{cm(altura_m)}/{cm(peitoril_m)}"


def criar_camada(doc: Drawing, nome: str) -> str:
    """Cria a camada com cor, espessura e tipo de linha do padrão; devolve o nome."""
    if nome in doc.layers:
        return nome
    p = CAMADAS.get(nome, PADRAO_DESCONHECIDA)
    layer = doc.layers.add(nome)
    layer.color = p.cor
    layer.dxf.lineweight = p.espessura
    if p.linetype != "Continuous" and p.linetype in doc.linetypes:
        layer.dxf.linetype = p.linetype
    if p.descricao:
        layer.description = p.descricao
    if not p.plotar:
        layer.dxf.plot = 0
    return nome


def configurar(doc: Drawing, escala: int = ESCALA_PADRAO) -> None:
    """Prepara o documento: unidade, estilos de texto e de cota da escala e as camadas básicas."""
    _check_escala(escala)
    doc.header["$INSUNITS"] = 6
    doc.header["$LWDISPLAY"] = 1  # espessuras visíveis
    doc.header["$MEASUREMENT"] = 1
    # os tipos de linha padrão têm traços de ~3,5 unidades: em um desenho em metros, sem isto
    # os traços teriam metros de comprimento
    doc.header["$LTSCALE"] = round(0.1 * escala / ESCALA_PADRAO, 4)
    for nome, fonte in ((ESTILO_TEXTO, "arial.ttf"), (ESTILO_AMBIENTE, "times.ttf")):
        if nome not in doc.styles:
            doc.styles.add(nome, font=fonte)
    _estilo_cota(doc, escala)


def _estilo_cota(doc: Drawing, escala: int) -> None:
    nome = dimstyle_nome(escala)
    if nome in doc.dimstyles:
        return
    h = altura_texto(escala)
    ds = doc.dimstyles.new(nome)
    ds.set_tick(size=round(h * 0.6, 4))  # tique arquitetônico no lugar da seta
    ds.dxf.dimtxt = h
    ds.dxf.dimtxsty = ESTILO_TEXTO
    ds.dxf.dimexe = round(h * 0.6, 4)  # extensão da linha de chamada além da cota
    ds.dxf.dimexo = round(h * 0.4, 4)  # afastamento da linha de chamada do objeto
    ds.dxf.dimgap = round(h * 0.3, 4)
    ds.dxf.dimtad = 1  # texto sobre a linha de cota
    ds.dxf.dimtih = 0  # texto alinhado com a cota, dentro e fora
    ds.dxf.dimtoh = 0
    ds.set_text_format(dec=2, sep=",")  # 24,00
    ds.dxf.dimlfac = 1.0
    ds.dxf.dimzin = 0
    ds.dxf.dimscale = 1.0
    ds.dxf.dimclrd = ds.dxf.dimclre = ds.dxf.dimclrt = 7
