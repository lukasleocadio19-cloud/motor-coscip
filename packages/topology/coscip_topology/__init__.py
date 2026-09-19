"""Conectividade e percursos sobre topologia validada (plano §8, GEO-04).

NetworkX fica atrás desta interface de domínio. Centros de salas sozinhos não definem
uma rota correta; escada não é término válido de fuga automaticamente.
"""

from coscip_topology.graph import Connection, FloorGraph, Route

__all__ = ["Connection", "FloorGraph", "Route"]
