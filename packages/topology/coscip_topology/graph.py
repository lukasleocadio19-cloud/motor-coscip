from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx


@dataclass(frozen=True)
class Connection:
    source: str
    target: str
    kind: str  # DOOR, OPENING, PASSAGE
    cost_m: float
    traversable: bool
    confirmed: bool
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Route:
    origin: str
    destination: str
    nodes: tuple[str, ...]
    cost_m: float
    algorithm: str
    assumptions: tuple[str, ...] = field(default_factory=tuple)


class UnconfirmedTopologyError(RuntimeError):
    pass


class FloorGraph:
    """Grafo de um pavimento. Só aceita conexões confirmadas para percursos."""

    def __init__(self, floor_id: str) -> None:
        self.floor_id = floor_id
        self._g: nx.Graph = nx.Graph()
        self._unconfirmed: list[Connection] = []

    def add(self, conn: Connection) -> None:
        if not conn.confirmed:
            self._unconfirmed.append(conn)
            return
        if conn.traversable:
            self._g.add_edge(conn.source, conn.target, weight=conn.cost_m, conn=conn)

    @property
    def unconfirmed(self) -> tuple[Connection, ...]:
        return tuple(self._unconfirmed)

    def shortest_route(self, origin: str, destination: str) -> Route | None:
        if self._unconfirmed:
            raise UnconfirmedTopologyError(
                f"{len(self._unconfirmed)} conexão(ões) sem confirmação no pavimento"
            )
        try:
            nodes = nx.dijkstra_path(self._g, origin, destination, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
        cost = nx.path_weight(self._g, nodes, weight="weight")
        return Route(
            origin=origin,
            destination=destination,
            nodes=tuple(nodes),
            cost_m=cost,
            algorithm="dijkstra-graph/1.0",
            assumptions=("custos de aresta confirmados; grafo de espaços, não área transitável",),
        )
