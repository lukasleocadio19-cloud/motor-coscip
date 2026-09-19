"""Transformações 4×4 com inversa, incluindo escala não uniforme e espelhamento."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Transform:
    matrix: np.ndarray

    def __post_init__(self) -> None:
        if self.matrix.shape != (4, 4):
            raise ValueError("Transform exige matriz 4x4")

    @classmethod
    def identity(cls) -> Transform:
        return cls(np.eye(4))

    @classmethod
    def from_rows(cls, rows: list[list[float]]) -> Transform:
        return cls(np.asarray(rows, dtype=float))

    @classmethod
    def translation(cls, dx: float, dy: float, dz: float = 0.0) -> Transform:
        m = np.eye(4)
        m[:3, 3] = (dx, dy, dz)
        return cls(m)

    @classmethod
    def rotation_z(cls, radians: float) -> Transform:
        c, s = np.cos(radians), np.sin(radians)
        m = np.eye(4)
        m[0, 0], m[0, 1], m[1, 0], m[1, 1] = c, -s, s, c
        return cls(m)

    @classmethod
    def scale(cls, sx: float, sy: float | None = None, sz: float = 1.0) -> Transform:
        m = np.diag([sx, sx if sy is None else sy, sz, 1.0])
        return cls(m)

    def __matmul__(self, other: Transform) -> Transform:
        return Transform(self.matrix @ other.matrix)

    def inverse(self) -> Transform:
        return Transform(np.linalg.inv(self.matrix))

    @property
    def is_uniform_scale(self) -> bool:
        """Falso quando um círculo transformado deixa de ser círculo."""
        sx = np.linalg.norm(self.matrix[:3, 0])
        sy = np.linalg.norm(self.matrix[:3, 1])
        return bool(np.isclose(sx, sy))

    @property
    def is_mirrored(self) -> bool:
        return bool(np.linalg.det(self.matrix[:3, :3]) < 0)

    def apply(self, points: np.ndarray) -> np.ndarray:
        pts = np.atleast_2d(np.asarray(points, dtype=float))
        if pts.shape[1] == 2:
            pts = np.column_stack([pts, np.zeros(len(pts))])
        homo = np.column_stack([pts, np.ones(len(pts))])
        return (homo @ self.matrix.T)[:, :3]

    def to_rows(self) -> list[list[float]]:
        return self.matrix.tolist()
