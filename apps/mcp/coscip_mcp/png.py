"""Tela RGB em numpy e gravação PNG com a biblioteca padrão (zlib), sem dependência nova.

Inclui uma fonte mínima 3×5 (dígitos, sinal, ponto, vírgula e algumas letras) para rotular
coordenadas da grade e números de símbolos: é o que permite à IA ler posições na imagem.
"""

from __future__ import annotations

import struct
import zlib

import numpy as np

_GLYPHS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "-": ("000", "000", "111", "000", "000"),
    ".": ("000", "000", "000", "000", "010"),
    ",": ("000", "000", "000", "010", "100"),
    " ": ("000", "000", "000", "000", "000"),
    "m": ("000", "000", "111", "111", "101"),
    "x": ("000", "101", "010", "101", "000"),
    "y": ("101", "101", "011", "001", "110"),
    "P": ("110", "101", "110", "100", "100"),
}


class Canvas:
    def __init__(self, width: int, height: int, background=(255, 255, 255)) -> None:
        self.w, self.h = int(width), int(height)
        self.px = np.empty((self.h, self.w, 3), dtype=np.uint8)
        self.px[:] = background

    def points(self, xs: np.ndarray, ys: np.ndarray, color) -> None:  # noqa: ANN001
        xs = np.asarray(xs).astype(np.int64)
        ys = np.asarray(ys).astype(np.int64)
        ok = (xs >= 0) & (xs < self.w) & (ys >= 0) & (ys < self.h)
        self.px[ys[ok], xs[ok]] = color

    def lines(self, x0, y0, x1, y1, color, max_samples: int = 40_000_000) -> None:  # noqa: ANN001
        """Desenha segmentos (arrays em pixels) amostrando cada um a cada pixel."""
        x0, y0, x1, y1 = (np.asarray(a, dtype=np.float64) for a in (x0, y0, x1, y1))
        if not len(x0):
            return
        n = np.maximum(np.abs(x1 - x0), np.abs(y1 - y0)).astype(np.int64) + 1
        n = np.minimum(n, 4 * max(self.w, self.h))
        start = 0
        while start < len(n):
            # Lotes limitados em amostras: plantas grandes têm milhões de segmentos.
            csum = np.cumsum(n[start:])
            stop = start + max(1, int(np.searchsorted(csum, max_samples)))
            idx = np.repeat(np.arange(start, stop), n[start:stop])
            first = np.repeat(np.cumsum(n[start:stop]) - n[start:stop], n[start:stop])
            t = (np.arange(len(idx)) - first) / np.maximum(n[idx] - 1, 1)
            self.points(np.rint(x0[idx] + (x1[idx] - x0[idx]) * t),
                        np.rint(y0[idx] + (y1[idx] - y0[idx]) * t), color)
            start = stop

    def rect(self, x0: int, y0: int, x1: int, y1: int, color) -> None:  # noqa: ANN001
        x0, x1 = sorted((max(0, x0), min(self.w, x1)))
        y0, y1 = sorted((max(0, y0), min(self.h, y1)))
        if x1 > x0 and y1 > y0:
            self.px[y0:y1, x0:x1] = color

    def disc(self, cx: float, cy: float, r: int, color) -> None:  # noqa: ANN001
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        keep = xx * xx + yy * yy <= r * r
        self.points(np.rint(cx) + xx[keep], np.rint(cy) + yy[keep], color)

    def text(self, x: int, y: int, s: str, color=(0, 0, 0), scale: int = 2,  # noqa: ANN001
             halo: bool = True) -> int:
        """Escreve com a fonte 3×5; devolve a largura em pixels. Caracteres fora da fonte
        viram espaço."""
        cx = x
        for ch in s:
            glyph = _GLYPHS.get(ch, _GLYPHS[" "])
            if halo:
                self.rect(cx - 1, y - 1, cx + 3 * scale + 1, y + 5 * scale + 1, (255, 255, 255))
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == "1":
                        self.rect(cx + c * scale, y + r * scale,
                                  cx + (c + 1) * scale, y + (r + 1) * scale, color)
            cx += 4 * scale
        return cx - x

    def png(self) -> bytes:
        raw = b"".join(b"\x00" + self.px[r].tobytes() for r in range(self.h))

        def chunk(kind: bytes, data: bytes) -> bytes:
            body = kind + data
            return struct.pack(">I", len(data)) + body + struct.pack(
                ">I", zlib.crc32(body) & 0xFFFFFFFF)

        header = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
