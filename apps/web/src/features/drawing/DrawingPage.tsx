import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "@coscip/api-client";
import { fetchScene, PlanViewer, type Pick, type SceneManifest } from "@coscip/viewer";
import { Button, Card, ErrorState, PageHeader } from "@coscip/ui";

import { AnalyticalPanel } from "./AnalyticalPanel";
import { ClassificationPanel } from "./ClassificationPanel";

type Mode = "select" | "reference" | "measure" | "clip" | "polygon" | "contour" | "width";

interface DrawingOut {
  id: string;
  revision_id: string;
  file: string | null;
  declared_unit: string | null;
  unit_suggestion: { unit: string | null; strength: string; note: string } | null;
  unit: { confirmed: boolean; frame_id: string | null; unit: string | null; scale_to_m: string | null };
  scene_available: boolean;
  floors: { id: string; name: string; clip: { type?: string; points?: [number, number][]; x0: number; y0: number; x1: number; y1: number } }[];
  model_snapshot: { id: string; quality: { units_confirmed: boolean; blocking_issue_ids: string[] } } | null;
}

interface EntityOrigin {
  row: number;
  handle: string;
  type: string;
  layer: string;
  source_layer: string | null;
  layout: string;
  instance_path: string[];
  block: string | null;
  quality: string;
  text: string | null;
  vertex_count: number;
  source_file: { name: string | null; sha256: string };
}

interface MeasureOut {
  length_m: number;
  uncertainty_m: number;
  snapped_to_vertex: [boolean, boolean];
  exploratory: boolean;
  measurement_id?: string;
}

const UNITS: [string, string][] = [
  ["m", "metros"], ["cm", "centímetros"], ["mm", "milímetros"], ["dm", "decímetros"],
  ["in", "polegadas"], ["ft", "pés"],
];

const MODE_HELP: Record<Mode, string> = {
  select: "Clique numa linha para ver de onde ela veio no DXF.",
  reference: "Clique nas duas pontas de uma medida conhecida (ex.: folha de porta cotada).",
  measure: "Clique em dois pontos. Perto de uma linha, o clique se ajusta ao vértice exato.",
  clip: "Clique em dois cantos opostos do retângulo do pavimento.",
  polygon: "Clique nos vértices do pavimento em ordem. Salvar fecha o polígono.",
  contour: "Clique nos vértices do contorno do ambiente em ordem.",
  width: "Clique nas duas extremidades da dimensão da porta que você deseja medir.",
};

function pointBody(p: Pick) {
  return { x: p.x, y: p.y, entity_row: p.entityRow, pick_tolerance: p.pickTolerance };
}

function fmt(n: number, d = 3) {
  return n.toLocaleString("pt-BR", { maximumFractionDigits: d, minimumFractionDigits: d });
}

export function DrawingPage() {
  const { drawingId = "" } = useParams();
  const qc = useQueryClient();
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<PlanViewer | null>(null);
  const [manifest, setManifest] = useState<SceneManifest | null>(null);
  const [sceneError, setSceneError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [visible, setVisible] = useState<Record<string, boolean>>({});
  const [mode, setMode] = useState<Mode>("select");
  const [picks, setPicks] = useState<Pick[]>([]);
  const [origin, setOrigin] = useState<EntityOrigin | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number } | null>(null);
  const [floorId, setFloorId] = useState<string>("");
  const [result, setResult] = useState<MeasureOut | null>(null);
  const [unit, setUnit] = useState("m");
  const [realLength, setRealLength] = useState("");
  const [justification, setJustification] = useState("");
  const [floorName, setFloorName] = useState("Térreo");

  const drawing = useQuery({
    queryKey: ["drawing", drawingId],
    queryFn: () => api<DrawingOut>(`/drawings/${drawingId}`),
  });
  const d = drawing.data;

  useEffect(() => {
    if (d?.unit_suggestion?.unit) setUnit(d.unit_suggestion.unit);
  }, [d?.unit_suggestion?.unit]);

  // Cria o viewer e carrega a cena binária.
  useEffect(() => {
    if (!host.current) return;
    const v = new PlanViewer(host.current);
    viewer.current = v;
    const onResize = () => v.resize();
    window.addEventListener("resize", onResize);
    v.onHover = setHover;
    let alive = true;
    fetchScene(api, drawingId)
      .then(({ manifest: m, segments, rows }) => {
        if (!alive) return;
        v.load(m, segments, rows);
        setManifest(m);
        setVisible(Object.fromEntries(m.layers.map((l) => [l.name, !l.dxf_off])));
      })
      .catch((e) => alive && setSceneError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
      window.removeEventListener("resize", onResize);
      v.dispose();
      viewer.current = null;
    };
  }, [drawingId]);

  // Clique na planta conforme o modo.
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    let selection = 0;
    v.onPick = (p) => {
      const request = ++selection;
      setResult(null);
      if (mode === "select") {
        setPicks([]);
        if (p.entityRow == null) return setOrigin(null);
        setOrigin(null);
        api<EntityOrigin>(`/drawings/${drawingId}/entities/${p.entityRow}`)
          .then((value) => { if (request === selection) setOrigin(value); })
          .catch((e) => { if (request === selection) setSceneError(e); });
        return;
      }
      setPicks((prev) => (mode === "polygon" || mode === "contour" ? [...prev, p].slice(0, 256) : prev.length >= 2 ? [p] : [...prev, p]));
    };
    return () => { selection++; v.onPick = undefined; };
  }, [mode, drawingId]);

  const activeFloor = d?.floors.find((f) => f.id === floorId);

  // Sobreposições: pontos, linha em construção, recortes e entidade selecionada.
  useEffect(() => {
    const v = viewer.current;
    if (!v || !manifest) return;
    const pts = picks.map((p) => [p.x, p.y] as [number, number]);
    const lines: [number, number, number, number][] = [];
    const rects = (d?.floors ?? []).filter((f) => f.clip.type !== "POLYGON").map((f) => ({ ...f.clip, active: f.id === floorId }));
    for (const floor of d?.floors ?? []) {
      const polygon = floor.clip.points;
      if (polygon) polygon.forEach((p, i) => lines.push([...p, ...polygon[(i + 1) % polygon.length]]));
    }
    if ((mode === "polygon" || mode === "contour") && pts.length > 1) {
      pts.forEach((p, i) => lines.push([...p, ...pts[(i + 1) % pts.length]]));
    }
    if (pts.length === 2 && mode !== "clip") lines.push([...pts[0], ...pts[1]]);
    if (pts.length === 2 && mode === "clip") {
      rects.push({
        x0: Math.min(pts[0][0], pts[1][0]), y0: Math.min(pts[0][1], pts[1][1]),
        x1: Math.max(pts[0][0], pts[1][0]), y1: Math.max(pts[0][1], pts[1][1]), active: true,
      });
    }
    v.setOverlay({ points: pts, lines, rects, highlightRow: origin?.row ?? null });
  }, [picks, mode, manifest, d?.floors, floorId, origin]);

  const drawingUnits = useMemo(
    () => (picks.length === 2 ? Math.hypot(picks[1].x - picks[0].x, picks[1].y - picks[0].y) : null),
    [picks],
  );

  const confirm = useMutation({
    mutationFn: () => api(`/drawings/${drawingId}/unit-confirmation`, {
      method: "POST",
      json: {
        unit, reference_a: pointBody(picks[0]), reference_b: pointBody(picks[1]),
        real_length_m: Number(realLength.replace(",", ".")), justification,
        expected_frame_id: d?.unit.frame_id,
      },
    }),
    onSuccess: () => {
      setPicks([]);
      setMode("measure");
      void qc.invalidateQueries({ queryKey: ["drawing", drawingId] });
    },
  });

  const measure = useMutation({
    mutationFn: (save: boolean) => api<MeasureOut>(`/drawings/${drawingId}/measure`, {
      method: "POST",
      json: { a: pointBody(picks[0]), b: pointBody(picks[1]), floor_id: floorId || null, save },
    }),
    onSuccess: setResult,
  });

  const createFloor = useMutation({
    mutationFn: () => {
      const [a, b] = picks;
      return api<{ id: string }>(`/drawings/${drawingId}/floors`, {
        method: "POST",
        json: {
          name: floorName,
          clip: mode === "polygon" ? { type: "POLYGON", points: picks.map((p) => [p.x, p.y]) } : { x0: Math.min(a.x, b.x), y0: Math.min(a.y, b.y), x1: Math.max(a.x, b.x), y1: Math.max(a.y, b.y) },
        },
      });
    },
    onSuccess: (f) => {
      setPicks([]);
      setFloorId(f.id);
      void qc.invalidateQueries({ queryKey: ["drawing", drawingId] });
    },
  });

  // Medir automaticamente ao completar dois pontos.
  useEffect(() => {
    if (mode === "measure" && picks.length === 2 && d?.unit.confirmed) measure.mutate(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [picks, mode]);

  const layers = [...(manifest?.layers ?? [])].sort((a, b) => b.count - a.count);
  const confirmed = d?.unit.confirmed ?? false;

  return (
    <>
      <PageHeader title={d?.file ?? "Planta"}>
        <Link to="/unidades" className="text-sm text-teal-800 underline">Revisar unidades</Link>
        {d && (
          <Link to={`/revisoes/${d.revision_id}/diagnostico`} className="rounded-md px-3 py-1.5 text-sm ring-1 ring-slate-300">
            Diagnóstico
          </Link>
        )}
      </PageHeader>
      {drawing.error && <ErrorState error={drawing.error} />}
      <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
        <span className={`rounded px-2 py-0.5 ring-1 ${confirmed ? "bg-emerald-50 text-emerald-800 ring-emerald-600/30" : "bg-amber-50 text-amber-900 ring-amber-600/30"}`}>
          {confirmed ? `✓ Unidade confirmada: ${UNITS.find((u) => u[0] === d?.unit.unit)?.[1] ?? d?.unit.unit}` : "! Unidade não confirmada — medidas bloqueadas"}
        </span>
        {d?.declared_unit && <span className="text-slate-500">Declarada no arquivo: {d.declared_unit} (só indício)</span>}
      </div>
      <div className="grid gap-3 lg:grid-cols-[220px_1fr_300px]">
        <Card title="Camadas">
          <p className="mb-2 text-xs text-slate-500">Ocultar uma camada não a exclui da análise.</p>
          <div className="mb-2 flex gap-2 text-xs">
            <button className="text-teal-800 underline" onClick={() => {
              layers.forEach((l) => viewer.current?.setLayerVisible(l.name, true));
              setVisible(Object.fromEntries(layers.map((l) => [l.name, true])));
            }}>todas</button>
            <button className="text-teal-800 underline" onClick={() => {
              layers.forEach((l) => viewer.current?.setLayerVisible(l.name, false));
              setVisible(Object.fromEntries(layers.map((l) => [l.name, false])));
            }}>nenhuma</button>
          </div>
          <ul className="max-h-[520px] space-y-0.5 overflow-auto text-xs">
            {layers.map((l) => (
              <li key={l.name}>
                <label className="flex items-center gap-1.5">
                  <input type="checkbox" checked={visible[l.name] ?? false} onChange={(e) => {
                    viewer.current?.setLayerVisible(l.name, e.target.checked);
                    setVisible((v) => ({ ...v, [l.name]: e.target.checked }));
                  }} />
                  <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} aria-hidden="true" />
                  <span className="truncate" title={l.name}>{l.name}</span>
                  <span className="ml-auto text-slate-400">{l.count}</span>
                </label>
              </li>
            ))}
          </ul>
        </Card>

        <div>
          <div ref={host} className="relative h-[620px] overflow-hidden rounded-lg border border-slate-200 bg-white" aria-label="Planta navegável">
            {loading && <p className="absolute inset-0 grid place-items-center text-sm text-slate-500">Carregando planta…</p>}
          </div>
          {sceneError != null && <ErrorState error={sceneError} />}
          <div className="mt-1 flex flex-wrap justify-between gap-2 text-xs text-slate-500">
            <span>Arraste para mover · roda do mouse para zoom</span>
            <span>
              {manifest && `${manifest.segment_count.toLocaleString("pt-BR")} segmentos · curvas com flecha máx. ${manifest.max_sagitta.toPrecision(2)} un.`}
              {hover && ` · x ${fmt(hover.x, 2)} y ${fmt(hover.y, 2)}`}
            </span>
          </div>
          <button className="mt-1 text-xs text-teal-800 underline" onClick={() => viewer.current?.fit()}>enquadrar</button>
          <button className="ml-3 mt-1 text-xs text-teal-800 underline" onClick={() => viewer.current?.recomputeFit()}>recalcular enquadramento</button>
          {activeFloor && (
            <button className="ml-3 mt-1 text-xs text-teal-800 underline"
              onClick={() => viewer.current?.fit([activeFloor.clip.x0, activeFloor.clip.y0, activeFloor.clip.x1, activeFloor.clip.y1])}>
              enquadrar pavimento
            </button>
          )}
        </div>

        <div className="space-y-3">
          <Card title="Ferramenta">
            <div className="grid grid-cols-2 gap-1.5" role="radiogroup" aria-label="Ferramenta">
              {([["select", "Selecionar"], ["reference", "Confirmar unidade"], ["measure", "Medir"], ["clip", "Recorte retangular"], ["polygon", "Recorte poligonal"], ["contour", "Contorno e área"], ["width", "Larguras de porta"]] as [Mode, string][]).map(([m, label]) => (
                <button key={m} role="radio" aria-checked={mode === m}
                  className={`rounded px-2 py-1.5 text-xs ring-1 ${mode === m ? "bg-teal-700 text-white ring-teal-700" : "ring-slate-300 hover:bg-slate-50"}`}
                  onClick={() => { setMode(m); setPicks([]); setResult(null); }}>
                  {label}
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-600">{MODE_HELP[mode]}</p>
            {picks.length > 0 && <button className="mt-2 text-xs text-teal-800 underline" onClick={() => { setPicks((prev) => prev.slice(0, -1)); setResult(null); }}>Desfazer último ponto</button>}
            {picks.length > 0 && mode !== "select" && (
              <ul className="mt-2 text-xs text-slate-600">
                {picks.map((p, i) => (
                  <li key={i}>Ponto {i + 1}: {p.snappedToVertex ? "vértice exato" : "ponto livre"} ({fmt(p.x, 3)}; {fmt(p.y, 3)})</li>
                ))}
              </ul>
            )}
          </Card>

          {mode === "select" && (
            <Card title="Origem no DXF">
              {!origin && <p className="text-sm text-slate-500">Nenhuma linha selecionada.</p>}
              {origin && (
                <dl className="grid grid-cols-[90px_1fr] gap-x-2 gap-y-1 text-xs">
                  <dt className="text-slate-500">Tipo</dt><dd>{origin.type}</dd>
                  <dt className="text-slate-500">Handle</dt><dd className="font-mono">{origin.handle}</dd>
                  <dt className="text-slate-500">Layer</dt><dd>{origin.layer}{origin.source_layer && origin.source_layer !== origin.layer && ` (no bloco: ${origin.source_layer})`}</dd>
                  <dt className="text-slate-500">Bloco</dt><dd>{origin.block ?? "—"}</dd>
                  <dt className="text-slate-500">Espaço</dt><dd>{origin.layout}</dd>
                  <dt className="text-slate-500">Caminho</dt><dd className="break-all font-mono">{origin.instance_path.join(" › ")}</dd>
                  <dt className="text-slate-500">Qualidade</dt><dd>{origin.quality}</dd>
                  <dt className="text-slate-500">Arquivo</dt><dd className="break-all">{origin.source_file.name} · <span className="font-mono">{origin.source_file.sha256.slice(0, 12)}…</span></dd>
                </dl>
              )}
            </Card>
          )}

          {mode === "select" && origin && <ClassificationPanel
            key={`${drawingId}:${origin.row}`} drawingId={drawingId} row={origin.row}
            floors={d?.floors ?? []} confirmed={confirmed} />}

          {mode === "reference" && (
            <Card title="Confirmar unidade do desenho">
              {d?.unit_suggestion?.unit && (
                <p className="mb-2 text-xs text-slate-600">
                  Sugestão pelas cotas: <strong>{UNITS.find((u) => u[0] === d.unit_suggestion?.unit)?.[1]}</strong> (indício {d.unit_suggestion.strength}). Não é decisão.
                </p>
              )}
              {drawingUnits != null && <p className="mb-2 text-xs">Distância entre os pontos: {fmt(drawingUnits, 4)} unidades do desenho</p>}
              <form className="space-y-2 text-sm" onSubmit={(e) => { e.preventDefault(); confirm.mutate(); }}>
                <label className="block">Unidade
                  <select className="mt-1 w-full rounded border border-slate-300 px-2 py-1" value={unit} onChange={(e) => setUnit(e.target.value)}>
                    {UNITS.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
                  </select>
                </label>
                <label className="block">Medida real conhecida (m)
                  <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1" inputMode="decimal" value={realLength}
                    onChange={(e) => setRealLength(e.target.value)} placeholder="ex.: 0,90" required />
                </label>
                <label className="block">Justificativa
                  <textarea className="mt-1 w-full rounded border border-slate-300 px-2 py-1" rows={2} value={justification}
                    onChange={(e) => setJustification(e.target.value)} placeholder="De onde vem a medida conhecida" required minLength={10} />
                </label>
                {confirm.error && <ErrorState error={(confirm.error as ApiError).problem?.title ?? confirm.error} />}
                <Button type="submit" disabled={picks.length !== 2 || confirm.isPending}>Confirmar unidade</Button>
              </form>
            </Card>
          )}

          {(mode === "contour" || mode === "width") && <AnalyticalPanel
            key={`${drawingId}:${mode}`} drawingId={drawingId} mode={mode} picks={picks}
            floors={d?.floors ?? []} onSaved={() => setPicks([])} />}

          {mode === "measure" && (
            <Card title="Medida">
              {!confirmed && <p className="text-sm text-amber-800">Confirme a unidade antes de medir.</p>}
              {(d?.floors.length ?? 0) > 0 && (
                <label className="mb-2 block text-xs">Limitar ao pavimento
                  <select className="mt-1 w-full rounded border border-slate-300 px-2 py-1" value={floorId} onChange={(e) => { setFloorId(e.target.value); setResult(null); setPicks([]); }}>
                    <option value="">(nenhum)</option>
                    {d?.floors.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                  </select>
                </label>
              )}
              {measure.error && <ErrorState error={(measure.error as ApiError).problem?.title ?? measure.error} />}
              {result && (
                <div className="text-sm">
                  <p className="text-2xl font-semibold">{fmt(result.length_m)} m</p>
                  <p className="text-xs text-slate-600">± {result.uncertainty_m < 1e-6 ? "< 0,001 mm" : `${fmt(result.uncertainty_m * 1000, 1)} mm`} ·{" "}
                    {result.exploratory ? "exploratória (ponto livre)" : "entre vértices exatos"}</p>
                  {result.measurement_id ? <p className="mt-1 text-xs text-emerald-800">✓ Medida registrada</p> : (
                    <Button className="mt-2" variant="ghost" onClick={() => measure.mutate(true)}>Registrar medida</Button>
                  )}
                </div>
              )}
            </Card>
          )}

          {(mode === "clip" || mode === "polygon") && (
            <Card title="Recorte do pavimento">
              <form className="space-y-2 text-sm" onSubmit={(e) => { e.preventDefault(); createFloor.mutate(); }}>
                <label className="block">Nome
                  <input className="mt-1 w-full rounded border border-slate-300 px-2 py-1" value={floorName} onChange={(e) => setFloorName(e.target.value)} required />
                </label>
                {createFloor.error && <ErrorState error={(createFloor.error as ApiError).problem?.title ?? createFloor.error} />}
                <Button type="submit" disabled={(mode === "polygon" ? picks.length < 3 : picks.length !== 2) || createFloor.isPending}>Salvar pavimento</Button>
              </form>
              {(d?.floors.length ?? 0) > 0 && (
                <ul className="mt-3 text-xs">
                  {d?.floors.map((f) => <li key={f.id}>▭ {f.name}</li>)}
                </ul>
              )}
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
