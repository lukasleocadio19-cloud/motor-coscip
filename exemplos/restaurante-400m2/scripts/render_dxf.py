"""Renderiza uma janela do DXF (em metros) para PDF vetorial. Uso: importar render_window()."""
from pathlib import Path

SAIDAS_EXEMPLO = Path(__file__).resolve().parents[1] / "saidas"
import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext, layout
from ezdxf.addons.drawing import pymupdf as ezpdf
from ezdxf.addons.drawing.config import BackgroundPolicy, Configuration

DXF = str(Path(__file__).resolve().parents[1] / "saidas" / "restaurante-400m2.dxf")


def render_window(win, scale, exclude_text=(), exclude_pred=None):
    """win=[x0,y0,x1,y1] em metros. scale = mm de papel por metro (ex. 10 p/ 1:100).
    Devolve bytes de um PDF cuja página é a janela inteira (moldura incluída)."""
    d = ezdxf.readfile(DXF)
    msp = d.modelspace()
    x0, y0, x1, y1 = win
    keep = set()
    for e in list(msp):
        t = e.dxftype()
        if t == "TEXT" and any(s in e.dxf.text for s in exclude_text):
            msp.delete_entity(e)
            continue
        ext = bbox.extents([e])
        if not ext.has_data:
            msp.delete_entity(e)
            continue
        c = ext.center
        if not (x0 <= c.x <= x1 and y0 <= c.y <= y1) or (exclude_pred and exclude_pred(e)):
            msp.delete_entity(e)
    if "MOLDURA" not in d.layers:
        d.layers.add("MOLDURA", color=8)
    msp.add_lwpolyline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], close=True,
                       dxfattribs={"layer": "MOLDURA", "color": 8, "lineweight": 25})
    ctx = RenderContext(d)
    backend = ezpdf.PyMuPdfBackend()
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE)
    Frontend(ctx, backend, config=cfg).draw_layout(msp)
    page = layout.Page(0, 0, layout.Units.mm)
    settings = layout.Settings(scale=scale, fit_page=False)
    return backend.get_pdf_bytes(page, settings=settings)


if __name__ == "__main__":
    import pymupdf
    pdf = render_window([-3, -3.6, 28.5, 21], 10, exclude_text=("PLANTA BAIXA", "RESTAURANTE (F-8)"))
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    r = doc[0].rect
    print("pagina pt", r.width, r.height, "mm", r.width / 72 * 25.4, r.height / 72 * 25.4)
    print("esperado mm", 31.5 * 10, 24.6 * 10)
    doc[0].get_pixmap(dpi=60).save(rf"{SAIDAS_EXEMPLO}\teste_plan.png")
