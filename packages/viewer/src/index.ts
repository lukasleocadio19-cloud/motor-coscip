/**
 * Viewer 2D de planta (plano §12). Three.js só fornece o renderizador;
 * seleção, layers e fidelidade CAD são trabalho do produto.
 *
 * - Câmera ortográfica; buffers AGRUPADOS por layer (nunca um objeto por entidade).
 * - Coordenadas relativas à origem local da cena, para preservar precisão em Float32.
 * - Medidas na tela são exploratórias; a medida oficial vem do servidor.
 * - Desligar layer na tela NÃO exclui elementos da análise.
 */
import * as THREE from "three";

export interface SceneLayerInfo {
  name: string;
  color: string;
  dxf_off: boolean;
  offset: number; // em segmentos
  count: number;
}

export interface SceneManifest {
  scene_schema_version: string;
  drawing_id: string;
  local_origin: [number, number];
  bbox: [number, number, number, number];
  fit_bbox: [number, number, number, number];
  segment_count: number;
  entity_count: number;
  max_sagitta: number;
  layers: SceneLayerInfo[];
  segments_artifact_id: string;
  entity_ids_artifact_id: string;
}

/** Resultado de um clique: coordenadas ABSOLUTAS do desenho (unidades do desenho). */
export interface Pick {
  x: number;
  y: number;
  entityRow: number | null;
  layer: string | null;
  snappedToVertex: boolean;
  pickTolerance: number; // tamanho de um pixel, em unidades do desenho
}

export interface Overlay {
  points?: [number, number][]; // absolutas
  lines?: [number, number, number, number][];
  rects?: { x0: number; y0: number; x1: number; y1: number; active?: boolean }[];
  highlightRow?: number | null;
}

const CLICK_MOVE_PX = 4;

export class PlanViewer {
  private renderer: THREE.WebGLRenderer;
  private camera: THREE.OrthographicCamera;
  private scene = new THREE.Scene();
  private overlayGroup = new THREE.Group();
  private layerObjects = new Map<string, THREE.LineSegments>();
  private manifest?: SceneManifest;
  private segments?: Float32Array; // relativos à origem: x1,y1,x2,y2 por segmento
  private rows?: Uint32Array;
  private raf = 0;
  private dirty = true;
  private cleanup: (() => void)[] = [];
  onPick?: (p: Pick) => void;
  onHover?: (p: { x: number; y: number } | null) => void;

  constructor(private host: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setClearColor(0xffffff);
    host.appendChild(this.renderer.domElement);
    this.renderer.domElement.style.cursor = "crosshair";
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -10, 10);
    this.overlayGroup.renderOrder = 10;
    this.scene.add(this.overlayGroup);
    this.resize();
    this.bindControls();
    const loop = () => {
      if (this.dirty) {
        this.renderer.render(this.scene, this.camera);
        this.dirty = false;
      }
      this.raf = requestAnimationFrame(loop);
    };
    loop();
  }

  load(manifest: SceneManifest, segments: Float32Array, rows: Uint32Array): void {
    this.clearLayers();
    this.manifest = manifest;
    this.segments = segments;
    this.rows = rows;
    for (const layer of manifest.layers) {
      const src = segments.subarray(layer.offset * 4, (layer.offset + layer.count) * 4);
      const pos = new Float32Array(layer.count * 6);
      for (let i = 0, j = 0; i < src.length; i += 2, j += 3) {
        pos[j] = src[i];
        pos[j + 1] = src[i + 1];
      }
      const geom = new THREE.BufferGeometry();
      geom.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      const obj = new THREE.LineSegments(geom, new THREE.LineBasicMaterial({ color: layer.color }));
      obj.visible = !layer.dxf_off;
      this.layerObjects.set(layer.name, obj);
      this.scene.add(obj);
    }
    this.fit();
  }

  /** Refaz apenas a vista a partir dos buffers; não altera o artefato nem medidas. */
  recomputeFit(): void {
    if (!this.segments?.length || !this.manifest) return;
    const n = this.segments.length / 2;
    const xs = new Float64Array(n);
    const ys = new Float64Array(n);
    const [ox, oy] = this.manifest.local_origin;
    for (let i = 0; i < n; i++) {
      xs[i] = this.segments[i * 2] + ox;
      ys[i] = this.segments[i * 2 + 1] + oy;
    }
    xs.sort(); ys.sort();
    const lo = Math.floor((n - 1) * .01), hi = Math.ceil((n - 1) * .99);
    const sx = Math.max(xs[hi] - xs[lo], 1e-9), sy = Math.max(ys[hi] - ys[lo], 1e-9);
    this.fit([Math.max(xs[0], xs[lo] - sx / 2), Math.max(ys[0], ys[lo] - sy / 2),
      Math.min(xs[n - 1], xs[hi] + sx / 2), Math.min(ys[n - 1], ys[hi] + sy / 2)]);
  }

  isLayerVisible(name: string): boolean {
    return this.layerObjects.get(name)?.visible ?? false;
  }

  setLayerVisible(name: string, visible: boolean): void {
    const obj = this.layerObjects.get(name);
    if (obj) {
      obj.visible = visible;
      this.dirty = true;
    }
  }

  /** Enquadra o retângulo absoluto (padrão: enquadramento robusto da cena). */
  fit(box?: [number, number, number, number]): void {
    if (!this.manifest) return;
    const [x0, y0, x1, y1] = box ?? this.manifest.fit_bbox;
    const [ox, oy] = this.manifest.local_origin;
    const cx = (x0 + x1) / 2 - ox;
    const cy = (y0 + y1) / 2 - oy;
    const aspect = this.host.clientWidth / Math.max(this.host.clientHeight, 1);
    const halfH = Math.max((y1 - y0) / 2, (x1 - x0) / 2 / aspect, 1e-6) * 1.05;
    Object.assign(this.camera, {
      left: cx - halfH * aspect, right: cx + halfH * aspect, top: cy + halfH, bottom: cy - halfH,
    });
    this.camera.updateProjectionMatrix();
    this.dirty = true;
  }

  setOverlay(o: Overlay): void {
    for (const c of [...this.overlayGroup.children]) {
      this.overlayGroup.remove(c);
      const m = c as THREE.Mesh;
      m.geometry?.dispose();
      (m.material as THREE.Material)?.dispose();
    }
    if (!this.manifest) return;
    const [ox, oy] = this.manifest.local_origin;
    const segs: number[] = [];
    const push = (a: number, b: number, c: number, d: number) =>
      segs.push(a - ox, b - oy, 0, c - ox, d - oy, 0);
    for (const l of o.lines ?? []) push(...l);
    const px = this.pixelSize() * 5;
    for (const [x, y] of o.points ?? []) {
      push(x - px, y - px, x + px, y + px);
      push(x - px, y + px, x + px, y - px);
    }
    this.addOverlay(segs, 0xdc2626);

    const rects: number[] = [];
    const active: number[] = [];
    for (const r of o.rects ?? []) {
      const target = r.active ? active : rects;
      const pts: [number, number][] = [[r.x0, r.y0], [r.x1, r.y0], [r.x1, r.y1], [r.x0, r.y1]];
      for (let i = 0; i < 4; i++) {
        const [a, b] = pts[i];
        const [c, d] = pts[(i + 1) % 4];
        target.push(a - ox, b - oy, 0, c - ox, d - oy, 0);
      }
    }
    this.addOverlay(rects, 0x0f766e);
    this.addOverlay(active, 0x0d9488);

    if (o.highlightRow != null && this.segments && this.rows) {
      const hl: number[] = [];
      const s = this.segments;
      for (let i = 0; i < this.rows.length; i++) {
        if (this.rows[i] === o.highlightRow) {
          hl.push(s[i * 4], s[i * 4 + 1], 0, s[i * 4 + 2], s[i * 4 + 3], 0);
        }
      }
      this.addOverlay(hl, 0x2563eb);
    }
    this.dirty = true;
  }

  resize(): void {
    this.renderer.setSize(this.host.clientWidth, this.host.clientHeight);
    this.dirty = true;
  }

  dispose(): void {
    cancelAnimationFrame(this.raf);
    for (const fn of this.cleanup) fn();
    this.clearLayers();
    this.setOverlay({});
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  private addOverlay(segs: number[], color: number): void {
    if (!segs.length) return;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(segs), 3));
    const mat = new THREE.LineBasicMaterial({ color, depthTest: false });
    const obj = new THREE.LineSegments(g, mat);
    obj.renderOrder = 10;
    this.overlayGroup.add(obj);
  }

  private pixelSize(): number {
    return (this.camera.right - this.camera.left) / Math.max(this.host.clientWidth, 1);
  }

  private toWorldRel(clientX: number, clientY: number): [number, number] {
    const r = this.renderer.domElement.getBoundingClientRect();
    const c = this.camera;
    const x = c.left + ((clientX - r.left) / r.width) * (c.right - c.left);
    const y = c.top - ((clientY - r.top) / r.height) * (c.top - c.bottom);
    return [x, y];
  }

  /** Segmento visível mais próximo; ajusta ao vértice se estiver a poucos pixels. */
  pickAt(clientX: number, clientY: number, tolPx = 6): Pick {
    const [wx, wy] = this.toWorldRel(clientX, clientY);
    const pxs = this.pixelSize();
    const [ox, oy] = this.manifest?.local_origin ?? [0, 0];
    const free: Pick = {
      x: wx + ox, y: wy + oy, entityRow: null, layer: null, snappedToVertex: false,
      pickTolerance: pxs,
    };
    if (!this.manifest || !this.segments || !this.rows) return free;
    const s = this.segments;
    const tol = tolPx * pxs;
    let best = Infinity;
    let bestSeg = -1;
    let bestLayer: string | null = null;
    for (const layer of this.manifest.layers) {
      if (!this.isLayerVisible(layer.name)) continue;
      for (let i = layer.offset; i < layer.offset + layer.count; i++) {
        const ax = s[i * 4], ay = s[i * 4 + 1], bx = s[i * 4 + 2], by = s[i * 4 + 3];
        if (Math.min(ax, bx) - tol > wx || Math.max(ax, bx) + tol < wx) continue;
        if (Math.min(ay, by) - tol > wy || Math.max(ay, by) + tol < wy) continue;
        const dx = bx - ax, dy = by - ay;
        const len2 = dx * dx + dy * dy;
        const t = len2 > 0 ? Math.max(0, Math.min(1, ((wx - ax) * dx + (wy - ay) * dy) / len2)) : 0;
        const d = Math.hypot(wx - (ax + t * dx), wy - (ay + t * dy));
        if (d < best) {
          best = d;
          bestSeg = i;
          bestLayer = layer.name;
        }
      }
    }
    if (bestSeg < 0 || best > tol) return free;
    const i = bestSeg;
    const ends: [number, number][] = [[s[i * 4], s[i * 4 + 1]], [s[i * 4 + 2], s[i * 4 + 3]]];
    const [vx, vy] = ends.reduce((a, b) =>
      Math.hypot(a[0] - wx, a[1] - wy) <= Math.hypot(b[0] - wx, b[1] - wy) ? a : b);
    const snapped = Math.hypot(vx - wx, vy - wy) <= tol;
    return {
      x: (snapped ? vx : wx) + ox,
      y: (snapped ? vy : wy) + oy,
      entityRow: this.rows[i],
      layer: bestLayer,
      snappedToVertex: snapped,
      pickTolerance: pxs,
    };
  }

  private clearLayers(): void {
    for (const obj of this.layerObjects.values()) {
      obj.geometry.dispose();
      (obj.material as THREE.Material).dispose();
      this.scene.remove(obj);
    }
    this.layerObjects.clear();
  }

  private bindControls(): void {
    const el = this.renderer.domElement;
    const onWheel = (ev: WheelEvent) => {
      ev.preventDefault();
      // Proporcional à rolagem (roda comum ≈ 100 por passo; touchpad envia valores menores).
      const steps = Math.max(-10, Math.min(10, ev.deltaY / 100));
      const f = Math.pow(1.2, steps);
      const [mx, my] = this.toWorldRel(ev.clientX, ev.clientY); // zoom no cursor
      const c = this.camera;
      Object.assign(c, {
        left: mx + (c.left - mx) * f, right: mx + (c.right - mx) * f,
        top: my + (c.top - my) * f, bottom: my + (c.bottom - my) * f,
      });
      c.updateProjectionMatrix();
      this.dirty = true;
    };
    let drag: { x: number; y: number; sx: number; sy: number } | null = null;
    const onDown = (ev: PointerEvent) => {
      drag = { x: ev.clientX, y: ev.clientY, sx: ev.clientX, sy: ev.clientY };
    };
    const onUp = (ev: PointerEvent) => {
      if (drag && Math.hypot(ev.clientX - drag.sx, ev.clientY - drag.sy) < CLICK_MOVE_PX &&
          ev.target === el) {
        this.onPick?.(this.pickAt(ev.clientX, ev.clientY));
      }
      drag = null;
    };
    const onMove = (ev: PointerEvent) => {
      if (ev.target === el && this.manifest) {
        const [x, y] = this.toWorldRel(ev.clientX, ev.clientY);
        const [ox, oy] = this.manifest.local_origin;
        this.onHover?.({ x: x + ox, y: y + oy });
      }
      if (!drag) return;
      const c = this.camera;
      const sx = (c.right - c.left) / el.clientWidth;
      const sy = (c.top - c.bottom) / el.clientHeight;
      const dx = (ev.clientX - drag.x) * sx;
      const dy = (ev.clientY - drag.y) * sy;
      Object.assign(c, { left: c.left - dx, right: c.right - dx, top: c.top + dy, bottom: c.bottom + dy });
      c.updateProjectionMatrix();
      drag = { ...drag, x: ev.clientX, y: ev.clientY };
      this.dirty = true;
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    el.addEventListener("pointerdown", onDown);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointermove", onMove);
    this.cleanup.push(() => {
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointermove", onMove);
    });
  }
}

/** Baixa manifesto + binários da cena de um desenho. */
export async function fetchScene(
  get: <T>(path: string) => Promise<T>,
  drawingId: string,
): Promise<{ manifest: SceneManifest; segments: Float32Array; rows: Uint32Array }> {
  const manifest = await get<SceneManifest>(`/drawings/${drawingId}/scene`);
  const [seg, ids] = await Promise.all([
    fetch(`/v1/artifacts/${manifest.segments_artifact_id}/content`, { credentials: "same-origin" }),
    fetch(`/v1/artifacts/${manifest.entity_ids_artifact_id}/content`, { credentials: "same-origin" }),
  ]);
  if (!seg.ok || !ids.ok) throw new Error("Falha ao baixar a cena");
  return {
    manifest,
    segments: new Float32Array(await seg.arrayBuffer()),
    rows: new Uint32Array(await ids.arrayBuffer()),
  };
}
