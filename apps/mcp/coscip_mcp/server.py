"""Servidor MCP (stdio, JSON-RPC 2.0) que dá à IA acesso ao motor de leitura de plantas.

Implementado com a biblioteca padrão: uma mensagem JSON por linha no stdin/stdout, logs
só no stderr. Métodos: ``initialize``, ``ping``, ``tools/list`` e ``tools/call``.
"""

from __future__ import annotations

import base64
import json
import sys
import traceback
from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from coscip_mcp import __version__, norms
from coscip_mcp.render import SYSTEM_KEYS, render
from coscip_mcp.workspace import ToolError, Workspace

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")

INSTRUCTIONS = """\
Ferramentas para LER plantas DXF de segurança contra incêndio (CBMERJ) com precisão.
Fluxo recomendado:
1. abrir_planta(caminho .dxf ou .dwg) → visão geral: camadas, símbolos reconhecidos, blocos sem
   classificação, unidade provisória.
2. ver_planta → imagem com grade em metros e símbolos numerados; use janela=[x0,y0,x1,y1]
   para aproximar. listar_textos e listar_simbolos dão os dados exatos com coordenadas.
3. confirmar_unidade SOMENTE com medidas confirmadas pelo usuário ou cotas legíveis que o
   usuário aceite: DUAS referências em direções diferentes (horizontal e vertical). Nunca
   suponha a unidade: o cabeçalho do DXF errou em 5 de 5 projetos.
4. definir_pavimentos com janelas/polígonos em metros (leia os títulos com listar_textos).
5. analisar_planta com o enquadramento que o usuário informar.
Para CRIAR uma planta sintética (exemplos, testes, estudos): criar_planta → listar_simbologia
(escolher os símbolos oficiais) → desenhar_planta (salas, portas, símbolos, textos,
legenda) → ver_planta para conferir → confirmar_unidade (duas paredes não paralelas, de
comprimento informado pelo usuário, servem) → analisar_planta. listar_elementos e
remover_elementos corrigem o que foi desenhado. Planta criada não é projeto real.
Para PROJETAR (modo projeto): enquadrar_edificacao (risco e medidas exigidas) →
dimensionar_extintores / dimensionar_saidas / dimensionar_hidrantes /
requisitos_iluminacao_alarme (memorial com a citação de cada passo) → criar_planta e
desenhar_planta com os símbolos nas quantidades calculadas (e 'corte' para o esquema vertical)
→ confirmar_unidade e analisar_planta para conferir os percursos → salvar_memorial. Os dados
da edificação (ocupação, áreas, alturas, tubulação) vêm do usuário: pergunte o que faltar. O
resultado é rascunho para o responsável técnico, nunca projeto pronto para protocolo.
Regras: não invente dados que a planta não mostra; o que o motor não localizou é
"não localizado", não "ausente"; nenhum resultado tem valor normativo (rascunho).
"""

JANELA = {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4,
          "description": "[x0, y0, x1, y1] em metros, na escala em uso"}
PONTO = {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2}
ID = {"type": "string", "description": "planta_id devolvido por abrir_planta"}


def _obj(props: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": list(required),
            "additionalProperties": False}


CONTEXT_SCHEMA = _obj({
    "occupancy": {"type": "string", "description": "divisão da NT 1-04, ex. D-2, A-2, M-2"},
    "risk_class": {"type": "string", "enum": ["PEQUENO", "MEDIO", "GRANDE"],
                   "description": "se omitido, sai da NT 1-04 pela ocupação"},
    "unifamiliar": {"type": "boolean"},
    "building_area_m2": {"type": "number", "description": "área total construída (ATC)"},
    "building_floors": {"type": "integer"}, "building_height_m": {"type": "number"},
    "single_occupancy": {"type": "boolean"},
    "grouped_houses_or_lots": {"type": "integer"},
    "requires_hydrants": {"type": "boolean"}, "requires_alarm": {"type": "boolean"},
    "requires_lighting": {"type": "boolean"},
    "exit_max_distance_m": {"type": "number",
                            "description": "limite até a saída informado (prevalece sobre o "
                                           "Anexo C)"},
    "exits_confirmed": {"type": "boolean",
                        "description": "usuário conferiu que as saídas marcadas são as saídas"},
    "construction_type": {"type": "string", "enum": ["ALFA", "BETA", "GAMA"],
                          "description": "Anexo C da NT 2-08: α propagação fácil, β mediana, "
                                         "γ difícil"},
    "sprinklers_or_detection": {"type": "boolean"}, "multiple_exits": {"type": "boolean"},
    "layout_defined": {"type": "boolean",
                       "description": "planta com leiaute definido; sem ele vale a NT 2-08 "
                                      "5.3.3.3 (distância direta, limite −30%)"},
})


class Server:
    def __init__(self) -> None:
        self.ws = Workspace()
        self.tools: dict[str, tuple[dict[str, Any], Callable[[dict[str, Any]], list]]] = {}
        self._register()

    # --- ferramentas ----------------------------------------------------------------------

    def _tool(self, name: str, title: str, description: str, schema: dict[str, Any],
              fn: Callable[[dict[str, Any]], Any]) -> None:
        self.tools[name] = ({"name": name, "title": title, "description": description,
                             "inputSchema": schema}, fn)

    def _register(self) -> None:
        ws = self.ws
        self._tool(
            "abrir_planta", "Abrir planta DXF",
            "Abre um DXF ou DWG (convertido por cópia com o ODA File Converter instalado) "
            "e devolve a visão geral: camadas (com as prováveis paredes), "
            "símbolos de segurança reconhecidos por classe, blocos não reconhecidos, número de "
            "textos, extensão em metros e a unidade PROVISÓRIA (cotas ou $INSUNITS).",
            _obj({"caminho": {"type": "string",
                              "description": "caminho do arquivo .dxf ou .dwg"}},
                 ("caminho",)),
            lambda a: _text(ws.open(a["caminho"])))
        self._tool(
            "criar_planta", "Criar planta",
            "Cria uma planta DXF SINTÉTICA nova (coordenadas em metros, Y para cima) e a abre. "
            "Caminho relativo vai para COSCIP_PLANTAS_DIR (padrão: plantas-criadas/ do "
            "repositório). Nunca sobrescreve arquivo existente; retomar=true reabre uma planta "
            "criada antes pelo motor (continua do .coscip.json ao lado do DXF). Depois use "
            "desenhar_planta. Não é projeto real e não serve como prova de nada.",
            _obj({"caminho": {"type": "string", "description": "arquivo .dxf a criar"},
                  "titulo": {"type": "string", "description": "nome descritivo (opcional)"},
                  "retomar": {"type": "boolean"}}, ("caminho",)),
            lambda a: _text(ws.create(a["caminho"], a.get("titulo", ""),
                                      a.get("retomar", False))))
        self._tool(
            "desenhar_planta", "Desenhar na planta",
            "Acrescenta elementos a uma planta criada por criar_planta; o DXF é regenerado "
            "inteiro e relido pelo motor (devolve os símbolos que ele reconheceu e ALERTA se "
            "algum não foi). Tudo em metros. Cada operação tem 'tipo': "
            "'sala' {nome, retangulo [x0,y0,x1,y1] OU poligono, espessura_m, estilo_parede} — "
            "pela face INTERNA, com parede por fora e área útil = área do desenho; salas "
            "vizinhas separadas por uma espessura dividem a parede; "
            "'parede' {pontos, espessura_m, fechar, estilo} — pelo eixo; estilo: comum | "
            "corta_fogo | compartimentacao | divisoria (NT 1-03); "
            "'porta' {x, y, largura_m=0.9, angulo_graus (direção da parede), abre_para, "
            "corte_m, corta_fogo_min 60|90|120} — centro sobre a parede; recorta o vão; "
            "'simbolo' {id OU classe, x, y, rotacao_graus, tamanho_m, estado, capacidade} — "
            "use o id de listar_simbologia (toda a NT 1-03 e as placas da NT 2-05, ex. "
            "'EXTINTOR_PQS_ABC', 'HIDRANTE_DUPLO', 'DETECTOR_FUMACA', 'E-5'); ou classe: "
            "EXTINTOR (exige agente CO2|AP|ESPUMA|PQS_BC|PQS_ABC|PO_D, sobre_rodas), "
            "SINALIZACAO (exige codigo) e as demais classes do motor; "
            "'texto' {texto, x, y, altura_m, camada, centralizado} — inclua o título do "
            "pavimento ('PLANTA BAIXA - TÉRREO') para o motor reconhecer a região; "
            "'cota' {a, b, afastamento_m}; "
            "'legenda' {x, y, ids?, escala} — legenda dos símbolos usados (NT 1-03, 5.4), com "
            "o nome oficial; ponha-a fora da planta e com ≥ 3 símbolos; "
            "'corte' {x, y, largura_m, pavimentos:[{nome, pe_direito_m}] de baixo para cima, "
            "laje_m, titulo, prumada_hidrantes, reservatorio superior|inferior, rti_l} — corte "
            "ESQUEMÁTICO / esquema vertical com níveis, cota total, prumada de hidrantes e "
            "reservatório; sai das alturas informadas (pergunte ao usuário), não da planta. "
            "Desenhe só o que o usuário pediu ou confirmou; não invente ocupação, saídas ou "
            "equipamentos.",
            _obj({"planta_id": ID,
                  "operacoes": {"type": "array", "minItems": 1, "maxItems": 200,
                                "items": {"type": "object",
                                          "properties": {"tipo": {"type": "string", "enum": [
                                              "sala", "parede", "porta", "simbolo", "texto",
                                              "cota", "legenda", "corte"]}},
                                          "required": ["tipo"]}}},
                 ("planta_id", "operacoes")),
            lambda a: _text(ws.draw(a["planta_id"], a["operacoes"])))
        self._tool(
            "listar_simbologia", "Listar simbologia do COSCIP",
            "Catálogo de símbolos para desenhar plantas: os 104 símbolos da NT 1-03 (Anexo A: "
            "extintores, hidrantes, sprinklers, gás carbônico, espuma, iluminação de emergência, "
            "vasos e tanques, sistema elétrico, alarme, detecção, sistemas passivos, controle de "
            "fumaça, rotas de fuga e outros) e as 56 placas da NT 2-05 (P, A, S, E; esquemáticas, "
            "sem pictograma). Cada item traz id, nome oficial, grupo, página da norma e a "
            "classe que o motor reconhece (null = só desenho, o motor não conta como "
            "equipamento). Filtre por grupo (parte do nome) ou busca. Sem argumentos devolve "
            "os grupos e todos os itens.",
            _obj({"grupo": {"type": "string", "description": "ex. EXTINTORES, DETEC, PLACAS"},
                  "busca": {"type": "string", "description": "parte do id ou do nome oficial"},
                  "incluir_placas": {"type": "boolean"}}),
            lambda a: _text(ws.symbology(a.get("grupo"), a.get("busca"),
                                         a.get("incluir_placas", True))))
        self._tool(
            "listar_elementos", "Listar elementos criados",
            "Operações que compõem uma planta criada pelo motor, com o índice 'i' de cada uma "
            "(para remover_elementos) e as classes de símbolo desenháveis.",
            _obj({"planta_id": ID}, ("planta_id",)),
            lambda a: _text(ws.list_elements(a["planta_id"])))
        self._tool(
            "remover_elementos", "Remover elementos criados",
            "Remove operações (índices de listar_elementos) de uma planta criada pelo motor e "
            "regenera o DXF. Os índices seguintes mudam.",
            _obj({"planta_id": ID,
                  "indices": {"type": "array", "items": {"type": "integer", "minimum": 0},
                              "minItems": 1}}, ("planta_id", "indices")),
            lambda a: _text(ws.remove_elements(a["planta_id"], a["indices"])))
        self._tool(
            "ver_planta", "Ver planta",
            "Imagem PNG da planta com grade e coordenadas em metros nas margens, paredes em "
            "preto, símbolos coloridos e numerados (mesmo n de listar_simbolos) e pavimentos "
            "em azul. Sem janela mostra o desenho principal; use janela para aproximar. "
            "percurso desenha o pior caminho da última análise.",
            _obj({"planta_id": ID, "janela": JANELA,
                  "camadas": {"type": "array", "items": {"type": "string"},
                              "description": "mostrar só estas camadas"},
                  "largura_px": {"type": "integer", "minimum": 400, "maximum": 2400},
                  "mostrar_textos": {"type": "boolean"},
                  "mostrar_simbolos": {"type": "boolean"},
                  "percurso": {"type": "string", "enum": list(SYSTEM_KEYS)}}, ("planta_id",)),
            self._view)
        self._tool(
            "listar_textos", "Listar textos",
            "Textos do desenho com posição (x, y em metros), camada e handle, de cima para "
            "baixo. Use para ler nomes de ambientes, títulos de pavimento, áreas e cotas.",
            _obj({"planta_id": ID, "janela": JANELA,
                  "contem": {"type": "string", "description": "filtro, sem diferenciar caixa"},
                  "limite": {"type": "integer", "minimum": 1, "maximum": 2000}},
                 ("planta_id",)),
            lambda a: _text(ws.texts(a["planta_id"], a.get("janela"), a.get("contem"),
                                     a.get("limite", 200))))
        self._tool(
            "listar_simbolos", "Listar símbolos",
            "Símbolos de segurança reconhecidos (extintor, hidrante, acionador, saída, "
            "iluminação, sinalização…) com número, posição, bloco, camada, handle e como foram "
            "reconhecidos; também os blocos frequentes que o dicionário não reconheceu.",
            _obj({"planta_id": ID, "classe": {"type": "string"}, "janela": JANELA,
                  "incluir_excluidos": {"type": "boolean",
                                        "description": "incluir legenda e demolir"}},
                 ("planta_id",)),
            lambda a: _text(ws.symbols(a["planta_id"], a.get("classe"), a.get("janela"),
                                       a.get("incluir_excluidos", False))))
        self._tool(
            "classificar_blocos", "Classificar blocos",
            "Diz ao motor que um bloco não reconhecido é de uma classe do dicionário (ex. "
            "{\"EXT_PQS_4KG\": \"EXTINTOR\"}). Confirme com o usuário: é interpretação.",
            _obj({"planta_id": ID, "mapa": {"type": "object",
                                            "additionalProperties": {"type": "string"}}},
                 ("planta_id", "mapa")),
            lambda a: _text(ws.classify_blocks(a["planta_id"], a["mapa"])))
        self._tool(
            "medir", "Medir",
            "Comprimento de uma linha reta ou poligonal entre pontos [x, y] em metros.",
            _obj({"planta_id": ID, "pontos": {"type": "array", "items": PONTO, "minItems": 2}},
                 ("planta_id", "pontos")),
            lambda a: _text(ws.measure(a["planta_id"], a["pontos"])))
        self._tool(
            "confirmar_unidade", "Confirmar unidade do desenho",
            "Confirma a escala com DUAS medidas de referência independentes, em direções "
            "diferentes (ex. uma cota horizontal e uma vertical): para cada uma, dois pontos "
            "na coordenada atual e o comprimento real em metros. Só use com medidas "
            "confirmadas pelo usuário. Bloqueia se as referências forem paralelas (< 30°) ou "
            "discordarem entre si mais que 0,5 %; aceita se a média bater com m, cm, mm, dm, "
            "pol ou pé (desvio ≤ 2 %).",
            _obj({"planta_id": ID,
                  "referencias": {"type": "array", "minItems": 2, "items": _obj(
                      {"ponto_a": PONTO, "ponto_b": PONTO,
                       "medida_real_m": {"type": "number", "exclusiveMinimum": 0}},
                      ("ponto_a", "ponto_b", "medida_real_m"))},
                  "justificativa": {"type": "string",
                                    "description": "de onde vêm as medidas e quem confirmou"}},
                 ("planta_id", "referencias", "justificativa")),
            lambda a: _text(ws.confirm_unit(a["planta_id"], a["referencias"],
                                            a["justificativa"])))
        self._tool(
            "definir_pavimentos", "Definir pavimentos",
            "Recorta os pavimentos a analisar (substitui os anteriores). Cada um com nome e "
            "janela [x0,y0,x1,y1] ou poligono [[x,y],...] em metros. Sem pavimentos o motor "
            "agrupa sozinho e tudo fica em revisão.",
            _obj({"planta_id": ID, "pavimentos": {"type": "array", "minItems": 1, "items": _obj(
                {"nome": {"type": "string"}, "janela": JANELA,
                 "poligono": {"type": "array", "items": PONTO, "minItems": 3}}, ("nome",))}},
                 ("planta_id", "pavimentos")),
            lambda a: _text(ws.define_floors(a["planta_id"], a["pavimentos"])))
        self._tool(
            "analisar_planta", "Analisar planta",
            "Roda o motor: área útil, paredes, percursos com incerteza, distância direta até a "
            "saída, enquadramento (NT 1-04, Anexo III, Anexo C da NT 2-08) e o Plano de "
            "Verificação (extintores, hidrantes, alarme, saídas) por pavimento, com pendências "
            "citando a norma. Exige unidade confirmada. RASCUNHO, sem valor normativo.",
            _obj({"planta_id": ID, "contexto": CONTEXT_SCHEMA,
                  "camadas_parede": {"type": "array", "items": {"type": "string"},
                                     "description": "substitui a escolha automática"}},
                 ("planta_id",)),
            lambda a: _text(ws.analyze(a["planta_id"], a.get("contexto") or {},
                                       a.get("camadas_parede"))))
        pav_ext = _obj({"nome": {"type": "string"},
                        "area_m2": {"type": "number", "exclusiveMinimum": 0},
                        "instalacoes_especiais": {
                            "type": "array", "items": {"type": "string"},
                            "description": "casa de bombas, casa de máquinas, subestação, "
                                           "gerador… (um extintor a ≤ 5 m de cada)"}},
                       ("nome", "area_m2"))
        self._tool(
            "enquadrar_edificacao", "Enquadrar a edificação",
            "PRIMEIRO passo de um projeto: pela divisão de ocupação (NT 1-04), área total "
            "construída e nº de pavimentos devolve o risco, as medidas de segurança exigidas "
            "(Decreto 42/2018, Anexo III) e o limite de distância até a saída (NT 2-08, Anexo "
            "C). Cobre o Anexo III inteiro (Tabelas 2 a 32): acima de 900 m² ou de 2 pavimentos "
            "informe também building_height_m quando passar de 6 pavimentos. Cada medida vem "
            "com a célula da tabela, as observações (ex. tipo de escada, condição por ATC) e "
            "'como_tratar': ferramenta de cálculo ou NTs a ler e símbolos a desenhar. Tabelas "
            "do grupo M por outro critério devolvem todas as colunas para escolher. O campo "
            "'conferencia' diz se a tabela foi conferida no PDF oficial; se vier 'SEM "
            "conferência visual', avise o usuário. Não invente a ocupação: pergunte.",
            CONTEXT_SCHEMA,
            lambda a: _text(ws.frame(a)))
        self._tool(
            "dimensionar_extintores", "Dimensionar extintores",
            "NT 2-01: quantidade de extintores por pavimento (área máxima por unidade e mínimo "
            "de 2), tipo e capacidade extintora mínima, sobre rodas no risco grande e os das "
            "instalações especiais. Devolve memorial com a citação de cada passo. A distância "
            "a percorrer só se confere na planta (analisar_planta).",
            _obj({"risco": {"type": "string", "enum": ["PEQUENO", "MEDIO", "GRANDE"],
                            "description": "risco_para_extintores de enquadrar_edificacao"},
                  "pavimentos": {"type": "array", "minItems": 1, "items": pav_ext},
                  "unifamiliar": {"type": "boolean"}}, ("risco", "pavimentos")),
            lambda a: _text(ws.design("extintores", a)))
        self._tool(
            "dimensionar_saidas", "Dimensionar saídas de emergência",
            "NT 2-08: população de cada pavimento (Anexo A), unidades de passagem (N = P/C), "
            "larguras mínimas de acessos, portas e escadas, mínimo de saídas no grupo F e barra "
            "antipânico. Informe por pavimento o dado que a divisão usa: area_m2 (maioria), "
            "dormitorios (A, H-2), leitos (H-1) ou vagas (G-1 a G-3); o erro diz qual falta. "
            "Tipo de escada (Anexo B) e distância máxima (Anexo C) não saem daqui.",
            _obj({"ocupacao": {"type": "string", "description": "divisão, ex. D-2"},
                  "numero_de_pavimentos": {"type": "integer", "minimum": 1},
                  "pavimentos": {"type": "array", "minItems": 1, "items": _obj({
                      "nome": {"type": "string"},
                      "area_m2": {"type": "number", "exclusiveMinimum": 0},
                      "dormitorios": {"type": "integer", "minimum": 0},
                      "area_alojamento_m2": {"type": "number", "minimum": 0},
                      "leitos": {"type": "integer", "minimum": 0},
                      "area_ambulatorio_m2": {"type": "number", "minimum": 0},
                      "vagas": {"type": "integer", "minimum": 0},
                      "populacao_informada": {"type": "integer", "minimum": 0},
                      "descarga": {"type": "boolean",
                                   "description": "pavimento com saída direta ao exterior"}},
                      ("nome",))}}, ("ocupacao", "pavimentos")),
            lambda a: _text(ws.design("saidas", a)))
        trecho = _obj({"nome": {"type": "string"},
                       "comprimento_m": {"type": "number", "minimum": 0},
                       "comprimento_equivalente_m": {
                           "type": "number", "minimum": 0,
                           "description": "soma das peças do trecho (joelhos, tês, registros, "
                                          "válvulas), informada pelo projetista"},
                       "diametro_interno_mm": {"type": "number"},
                       "vazao": {"type": "string", "enum": ["SISTEMA", "HIDRANTE"],
                                 "description": "HIDRANTE no ramal de um só hidrante"},
                       "colar": {"type": "boolean",
                                 "description": "trecho do colar hidráulico da bomba"}},
                      ("nome", "comprimento_m", "diametro_interno_mm"))
        self._tool(
            "dimensionar_hidrantes", "Dimensionar hidrantes e mangotinhos",
            "NT 2-02: tipo de sistema, vazão e pressão de trabalho (Tabela 1), reserva técnica "
            "de incêndio, perdas de carga por trecho (Hazen-Williams), velocidades, perda na "
            "mangueira, altura manométrica total no modelo do Anexo B e potência estimada da "
            "bomba. Trechos, diâmetros internos, comprimentos equivalentes e desnível vêm do "
            "projetista: pergunte, não suponha. O que a NT não fixa sai como premissa.",
            _obj({"risco": {"type": "string",
                            "enum": ["PEQUENO_MANGOTINHO", "PEQUENO", "MEDIO_1", "MEDIO_2",
                                     "GRANDE"],
                            "description": "risco_para_hidrantes de enquadrar_edificacao"},
                  "numero_de_hidrantes": {"type": "integer", "minimum": 1},
                  "material": {"type": "string",
                               "enum": ["FERRO_FUNDIDO", "ACO_PRETO", "GALVANIZADO", "COBRE"]},
                  "succao": {"type": "array", "items": trecho},
                  "recalque": {"type": "array", "items": trecho},
                  "desnivel_m": {"type": "number",
                                 "description": "cota do hidrante mais desfavorável menos o "
                                                "nível mínimo da água (negativo: reservatório "
                                                "acima do hidrante)"},
                  "mangueira_m": {"type": "number"},
                  "c_mangueira": {"type": "number"},
                  "rendimento_bomba": {"type": "number"}}, ("risco", "numero_de_hidrantes")),
            lambda a: _text(ws.design("hidrantes", a)))
        self._tool(
            "requisitos_iluminacao_alarme", "Requisitos de iluminação e alarme",
            "O que as NT 2-06 (iluminação de emergência) e NT 2-07 (alarme) fixam para o "
            "projeto: onde instalar, autonomia, distância até o acionador. Espaçamento e "
            "quantidades seguem as NBR 10898 e 17240, fora da base: saem como pendência.",
            _obj({"sistema": {"type": "string", "enum": ["iluminacao", "alarme"]},
                  "ocupacao": {"type": "string", "description": "divisão (para iluminacao)"}},
                 ("sistema",)),
            lambda a: _text(ws.design(a["sistema"], a)))
        self._tool(
            "salvar_memorial", "Salvar memorial de cálculo",
            "Grava em Markdown o memorial com todos os cálculos feitos nesta sessão (um por "
            "sistema; recalcular substitui), com premissas, pendências e a base normativa "
            "conferida. Caminho relativo vai para a pasta das plantas criadas. Não sobrescreve.",
            _obj({"caminho": {"type": "string", "description": "arquivo .md"},
                  "titulo": {"type": "string"},
                  "dados_da_edificacao": {"type": "object",
                                          "description": "endereço, ocupação, áreas… como o "
                                                         "usuário informou"}}, ("caminho",)),
            lambda a: _text(ws.save_memorial(a["caminho"], a.get("titulo", ""),
                                             a.get("dados_da_edificacao") or {})))
        self._tool(
            "consultar_norma", "Consultar norma",
            "Texto de um item (documento + item, ex. NT 2-01 + 5.2.4, NT 2-08 + Anexo C) ou "
            "busca por termos nas NTs e no Decreto 42/2018. Sem argumentos: o que está "
            "carregado e conferido.",
            _obj({"documento": {"type": "string"}, "item": {"type": "string"},
                  "busca": {"type": "string"}}),
            self._norm)

    def _view(self, a: dict[str, Any]) -> list[dict[str, Any]]:
        d = self.ws.get(a["planta_id"])
        png, caption = render(d, a.get("janela"), a.get("camadas"), a.get("largura_px", 1400),
                              a.get("mostrar_textos", False), a.get("mostrar_simbolos", True),
                              a.get("percurso"))
        return [{"type": "image", "data": base64.b64encode(png).decode("ascii"),
                 "mimeType": "image/png"}, *_text(caption)]

    def _norm(self, a: dict[str, Any]) -> list[dict[str, Any]]:
        base = norms.load_base()
        if a.get("item"):
            if not a.get("documento"):
                raise ToolError("informe o documento junto com o item")
            return _text(norms.item_text(base, a["documento"], a["item"]))
        if a.get("busca"):
            return _text({"resultados": norms.search(base, a["busca"], a.get("documento"))})
        return _text(base.summary())

    # --- protocolo ------------------------------------------------------------------------

    def handle(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        method, mid = msg.get("method"), msg.get("id")
        if mid is None:  # notificação: nunca responde
            return None
        try:
            if method == "initialize":
                asked = (msg.get("params") or {}).get("protocolVersion")
                version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
                result = {"protocolVersion": version,
                          "capabilities": {"tools": {"listChanged": False}},
                          "serverInfo": {"name": "coscip-plantas", "title": "Motor COSCIP",
                                         "version": __version__},
                          "instructions": INSTRUCTIONS}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": [spec for spec, _ in self.tools.values()]}
            elif method == "tools/call":
                result = self._call(msg.get("params") or {})
            else:
                return _error(mid, -32601, f"método não suportado: {method}")
        except Exception as exc:  # noqa: BLE001 — erro interno vira resposta, não queda
            traceback.print_exc(file=sys.stderr)
            return _error(mid, -32603, str(exc))
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def _call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if name not in self.tools:
            return {"content": _text(f"ferramenta desconhecida: {name}"), "isError": True}
        try:
            content = self.tools[name][1](params.get("arguments") or {})
            return {"content": content, "isError": False}
        except (ToolError, ValidationError, KeyError, ValueError) as exc:
            detail = exc.args[0] if isinstance(exc, KeyError) else str(exc)
            label = "argumento ausente" if isinstance(exc, KeyError) else "não foi possível"
            return {"content": _text(f"{label}: {detail}"), "isError": True}

    def serve(self, stdin=None, stdout=None) -> None:  # noqa: ANN001
        stdin = stdin or sys.stdin.buffer
        stdout = stdout or sys.stdout.buffer
        for raw in stdin:
            line = raw.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError as exc:
                reply = _error(None, -32700, f"JSON inválido: {exc}")
            else:
                reply = self.handle(msg)
            if reply is not None:
                stdout.write(json.dumps(reply, ensure_ascii=False).encode("utf-8") + b"\n")
                stdout.flush()


def _text(payload: Any) -> list[dict[str, Any]]:
    text = payload if isinstance(payload, str) else json.dumps(
        payload, ensure_ascii=False, indent=1, default=str)
    return [{"type": "text", "text": text}]


def _error(mid: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}


def main() -> None:
    print(f"coscip-plantas {__version__} (MCP stdio) pronto", file=sys.stderr)
    Server().serve()
