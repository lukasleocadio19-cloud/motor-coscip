/**
 * Viewer 2D de planta (plano §12). Three.js só fornece o renderizador;
 * seleção, layers e fidelidade CAD são trabalho do produto.
 *
 * - Câmera ortográfica; buffers AGRUPADOS por layer (nunca um objeto por entidade).
 * - Coordenadas relativas à origem local da cena, para preservar precisão.
 * - Medidas na tela são exploratórias; a medida oficial vem do servidor.
 * - Desligar layer na tela NÃO exclui elementos da análise.
 */
import * as THREE from "three";

export interface SceneLayer {
  name: string;
  color: string;
  /** Segmentos [x1,y1,x2,y2,...] relativos à origem local, em metros. */
  segments: Float32Array;
  /** ID de entidade por segmento, para seleção. */
  entityIds: string[];
}

export interface SceneManifest {
  scene_schema_version: string;
  model_snapshot_id: string;
  floor_id: string;
  local_origin: [number, number];
  bbox: [number, number, number, number];
  layers: SceneLayer[];
}

export class PlanViewer {
  private renderer: THREE.WebGLRenderer;
  private camera: THREE.OrthographicCamera;
  private scene = new THREE.Scene();
  private layerObjects = new Map<string, THREE.LineSegments>();
  private manifest?: SceneManifest;
  private raf = 0;
  private dirty = true;

  constructor(private host: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setClearColor(0xffffff);
    host.appendChild(this.renderer.domElement);
    this.camera = new THREE.OrthographicCamera(-1, 1, 1, -1, -10, 10);
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

  load(manifest: SceneManifest): void {
    this.clear();
    this.manifest = manifest;
    for (const layer of manifest.layers) {
      const geom = new THREE.BufferGeometry();
      const pos = new Float32Array((layer.segments.length / 2) * 3);
      for (let i = 0, j = 0; i < layer.segments.length; i += 2, j += 3) {
        pos[j] = layer.segments[i];
        pos[j + 1] = layer.segments[i + 1];
      }
      geom.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      const obj = new THREE.LineSegments(geom, new THREE.LineBasicMaterial({ color: layer.color }));
      obj.userData = { layer: layer.name, entityIds: layer.entityIds };
      this.layerObjects.set(layer.name, obj);
      this.scene.add(obj);
    }
    this.fit();
  }

  setLayerVisible(name: string, visible: boolean): void {
    const obj = this.layerObjects.get(name);
    if (obj) {
      obj.visible = visible;
      this.dirty = true;
    }
  }

  fit(): void {
    if (!this.manifest) return;
    const [x0, y0, x1, y1] = this.manifest.bbox;
    const [ox, oy] = this.manifest.local_origin;
    const cx = (x0 + x1) / 2 - ox;
    const cy = (y0 + y1) / 2 - oy;
    const half = Math.max(x1 - x0, y1 - y0) / 2 || 1;
    const aspect = this.host.clientWidth / Math.max(this.host.clientHeight, 1);
    Object.assign(this.camera, {
      left: cx - half * aspect, right: cx + half * aspect, top: cy + half, bottom: cy - half,
    });
    this.camera.updateProjectionMatrix();
    this.dirty = true;
  }

  resize(): void {
    this.renderer.setSize(this.host.clientWidth, this.host.clientHeight);
    this.dirty = true;
  }

  dispose(): void {
    cancelAnimationFrame(this.raf);
    this.clear();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }

  private clear(): void {
    for (const obj of this.layerObjects.values()) {
      obj.geometry.dispose();
      (obj.material as THREE.Material).dispose();
      this.scene.remove(obj);
    }
    this.layerObjects.clear();
  }

  private bindControls(): void {
    const el = this.renderer.domElement;
    el.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      const f = ev.deltaY > 0 ? 1.15 : 1 / 1.15;
      const c = this.camera;
      const mx = (c.left + c.right) / 2;
      const my = (c.top + c.bottom) / 2;
      Object.assign(c, {
        left: mx + (c.left - mx) * f, right: mx + (c.right - mx) * f,
        top: my + (c.top - my) * f, bottom: my + (c.bottom - my) * f,
      });
      c.updateProjectionMatrix();
      this.dirty = true;
    }, { passive: false });
    let drag: { x: number; y: number } | null = null;
    el.addEventListener("pointerdown", (ev) => (drag = { x: ev.clientX, y: ev.clientY }));
    window.addEventListener("pointerup", () => (drag = null));
    window.addEventListener("pointermove", (ev) => {
      if (!drag) return;
      const c = this.camera;
      const sx = (c.right - c.left) / el.clientWidth;
      const sy = (c.top - c.bottom) / el.clientHeight;
      const dx = (ev.clientX - drag.x) * sx;
      const dy = (ev.clientY - drag.y) * sy;
      Object.assign(c, { left: c.left - dx, right: c.right - dx, top: c.top + dy, bottom: c.bottom + dy });
      c.updateProjectionMatrix();
      drag = { x: ev.clientX, y: ev.clientY };
      this.dirty = true;
    });
  }
}
