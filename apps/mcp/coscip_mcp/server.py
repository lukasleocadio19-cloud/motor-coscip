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
3. confirmar_unidade SOMENTE com medida confirmada pelo usuário ou cota legível que o
   usuário aceite. Nunca suponha a unidade: o cabeçalho do DXF errou em 5 de 5 projetos.
4. definir_pavimentos com janelas/polígonos em metros (leia os títulos com listar_textos).
5. analisar_planta com o enquadramento que o usuário informar.
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
            "Confirma a escala com uma medida de referência: dois pontos na coordenada atual e "
            "o comprimento real em metros (ex. uma cota, a largura de uma porta). Só use com "
            "medida confirmada pelo usuário. Aceita se bater com m, cm, mm, dm, pol ou pé "
            "(desvio ≤ 2 %).",
            _obj({"planta_id": ID, "ponto_a": PONTO, "ponto_b": PONTO,
                  "medida_real_m": {"type": "number", "exclusiveMinimum": 0},
                  "justificativa": {"type": "string",
                                    "description": "de onde vem a medida e quem confirmou"}},
                 ("planta_id", "ponto_a", "ponto_b", "medida_real_m", "justificativa")),
            lambda a: _text(ws.confirm_unit(a["planta_id"], a["ponto_a"], a["ponto_b"],
                                            a["medida_real_m"], a["justificativa"])))
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
