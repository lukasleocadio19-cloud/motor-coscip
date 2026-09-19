"""Leitura DXF e origem das entidades (plano §8, POC-04, CAD-01..03).

O CBM não depende de ezdxf: este pacote é o único que o importa.
"""

from coscip_cad.dxf_reader import DxfReader, DxfReadError, ExtractedEntity, Inventory

__all__ = ["DxfReadError", "DxfReader", "ExtractedEntity", "Inventory"]
