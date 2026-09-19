import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@coscip/api-client";
import { Button, Card, ErrorState } from "@coscip/ui";
import type { Pick } from "@coscip/viewer";

const WIDTHS: Record<string, string> = { OPENING: "Vão", LEAF: "Folha", CLEAR: "Largura livre" };
interface Prepared {
  model_snapshot_id: string;
  semantic_elements: { id: string; floor_id: string; entity_row: number; properties: Record<string, { value: string; status: string }> }[];
  analytical_contours: { id: string; name: string; area_m2: number; uncertainty_m2: number; status: string; floor_id: string }[];
  door_widths: { id: string; kind: string; value_m: number; status: string }[];
}
const point = (p: Pick) => ({ x: p.x, y: p.y, entity_row: p.entityRow, pick_tolerance: p.pickTolerance });

export function AnalyticalPanel({ drawingId, mode, picks, floors, onSaved }: {
  drawingId: string; mode: "contour" | "width"; picks: Pick[];
  floors: { id: string; name: string }[]; onSaved: () => void;
}) {
  const qc = useQueryClient();
  const [floor, setFloor] = useState(floors[0]?.id ?? "");
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [door, setDoor] = useState("");
  const [kind, setKind] = useState("OPENING");
  const [replaces, setReplaces] = useState("");
  const q = useQuery({ queryKey: ["preparation", drawingId],
    queryFn: () => api<Prepared>(`/drawings/${drawingId}/preparation`) });
  const doors = q.data?.semantic_elements.filter((e) => e.floor_id === floor && e.properties.element_class?.value === "DOOR" && e.properties.element_class.status === "HUMAN_CONFIRMED") ?? [];
  const save = useMutation({
    mutationFn: () => api(`/drawings/${drawingId}/${mode === "contour" ? "contours" : "door-widths"}`, {
      method: "POST", json: { floor_id: floor, expected_snapshot_id: q.data?.model_snapshot_id,
        justification: note, ...(mode === "contour" ? { name, points: picks.map(point), replaces_id: replaces || null }
          : { element_id: door, kind, a: point(picks[0]), b: point(picks[1]) }) },
    }),
    onSuccess: () => {
      onSaved(); setNote("");
      void qc.invalidateQueries({ queryKey: ["preparation", drawingId] });
      void qc.invalidateQueries({ queryKey: ["drawing", drawingId] });
      void qc.invalidateQueries({ queryKey: ["classification", drawingId] });
    },
    onError: () => void qc.invalidateQueries({ queryKey: ["preparation", drawingId] }),
  });
  return <Card title={mode === "contour" ? "Área do contorno" : "Larguras da porta"}>
    <p className="mb-3 text-xs text-slate-600">{mode === "contour" ? "Clique nos vértices em ordem. Ao salvar, o contorno será fechado e sua área calculada. Pontos livres mantêm a incerteza do clique." : "Meça cada dimensão separadamente. A largura livre não é deduzida do vão ou da folha."}</p>
    {q.error && <ErrorState error={q.error} />}
    {!floors.length && <p className="text-sm text-amber-900">Recorte um pavimento primeiro.</p>}
    <form className="space-y-2 text-sm" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <label className="block">Pavimento<select className="mt-1 w-full rounded border p-1" value={floor} onChange={(e) => { setFloor(e.target.value); setDoor(""); setReplaces(""); }} required>
        <option value="" disabled>Escolher pavimento</option>{floors.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
      </select></label>
      {mode === "contour" ? <>
        <label className="block">Contorno<select className="mt-1 w-full rounded border p-1" value={replaces} onChange={(e) => setReplaces(e.target.value)}>
          <option value="">Novo contorno</option>{q.data?.analytical_contours.filter((c) => c.floor_id === floor).map((c) => <option key={c.id} value={c.id}>Redesenhar: {c.name}</option>)}
        </select></label>
        <label className="block">Nome do ambiente<input className="mt-1 w-full rounded border p-1" value={name} onChange={(e) => setName(e.target.value)} required maxLength={100} /></label>
      </> : <>
        <label className="block">Porta confirmada<select className="mt-1 w-full rounded border p-1" value={door} onChange={(e) => setDoor(e.target.value)} required>
          <option value="">Escolher porta</option>{doors.map((d) => <option value={d.id} key={d.id}>{d.properties.name?.value ?? `Porta · entidade ${d.entity_row}`}</option>)}
        </select></label>
        {doors.length === 0 && <p className="text-xs text-amber-900">Use Selecionar para confirmar a classe de uma porta neste pavimento.</p>}
        <label className="block">Dimensão<select className="mt-1 w-full rounded border p-1" value={kind} onChange={(e) => setKind(e.target.value)}>
          {Object.entries(WIDTHS).map(([k, label]) => <option value={k} key={k}>{label}</option>)}
        </select></label>
      </>}
      <label className="block">Justificativa<textarea className="mt-1 w-full rounded border p-1" value={note} onChange={(e) => setNote(e.target.value)} required minLength={10} maxLength={2000} /></label>
      {save.error && <ErrorState error={save.error} />}
      {save.isSuccess && <p role="status" className="text-xs text-emerald-800">Geometria e medida registradas.</p>}
      <Button disabled={!floor || !q.data || save.isPending || (mode === "contour" ? picks.length < 3 : picks.length !== 2 || !door)}>Confirmar e salvar</Button>
    </form>
    <ul className="mt-3 space-y-1 text-xs">
      {mode === "contour" ? q.data?.analytical_contours.map((c) => <li key={c.id}>{c.name}: {c.area_m2.toFixed(3)} m² ± {c.uncertainty_m2.toPrecision(2)} m² {c.status === "REVIEW_REQUIRED" && "· revisar unidade"}</li>)
        : q.data?.door_widths.map((w) => <li key={w.id}>{WIDTHS[w.kind]}: {w.value_m.toFixed(3)} m {w.status === "REVIEW_REQUIRED" && "· revisar"}</li>)}
    </ul>
  </Card>;
}
