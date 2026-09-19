"""Adaptador de filesystem local (plano §11, LOC-05/LOC-06).

Originais imutáveis, nomes gerados pela aplicação, SHA-256 e publicação atômica.
O cliente nunca fornece caminho de destino.
"""

from coscip_storage.local import (
    DataLayout,
    LocalFileStorage,
    PathOutsideRootError,
    StoredObject,
)

__all__ = ["DataLayout", "LocalFileStorage", "PathOutsideRootError", "StoredObject"]
