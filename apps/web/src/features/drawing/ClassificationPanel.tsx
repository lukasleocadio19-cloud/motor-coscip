import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@coscip/api-client";
import { Button, Card, ErrorState } from "@coscip/ui";

export const CLASS_NAMES: Record<string, string> = {
  SPACE: "Ambiente", DOOR: "Porta", OPENING: "Abertura", EXIT: "Saída", EXTINGUISHER: "Extintor",
  WALL: "Parede", STAIR: "Escada", OBSTACLE: "Obstáculo", UNKNOWN: "Não identificado",
};
interface Property { value: string; status: string; justification: string }
interface Classification {
  model_snapshot_id: string; conflict: boolean;
  candidates: { element_class: string; evidence: string; stage: string }[];
  items: { id: string; floor_id: string; properties: Record<string, Property> }[];
}

export function ClassificationPanel({ drawingId, row, floors, confirmed }: {
  drawingId: string; row: number; floors: { id: string; name: string }[]; confirmed: boolean;
}) {
  const qc = useQueryClient();
  const [floorId, setFloorId] = useState(floors[0]?.id ?? "");
  const [property, setProperty] = useState("element_class");
  const [elementClass, setElementClass] = useState("DOOR");
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [checked, setChecked] = useState(false);
  const q = useQuery({ queryKey: ["classification", drawingId, row],
    queryFn: () => api<Classification>(`/drawings/${drawingId}/entities/${row}/classification`) });
  const item = q.data?.items.find((e) => e.floor_id === floorId);
  useEffect(() => {
    const value = item?.properties.element_class?.value ?? q.data?.candidates[0]?.element_class;
    if (value && CLASS_NAMES[value]) setElementClass(value);
    setName(item?.properties.name?.value ?? "");
    setChecked(false);
  }, [item, q.data]);
  const save = useMutation({
    mutationFn: () => api(`/drawings/${drawingId}/entities/${row}/classification`, {
      method: "POST", json: { floor_id: floorId, expected_snapshot_id: q.data?.model_snapshot_id,
        property, value: property === "element_class" ? elementClass : name,
        justification: note, source_checked: checked },
    }),
    onSuccess: () => {
      setNote(""); setChecked(false);
      void qc.invalidateQueries({ queryKey: ["classification", drawingId] });
      void qc.invalidateQueries({ queryKey: ["drawing", drawingId] });
    },
    onError: () => void qc.invalidateQueries({ queryKey: ["classification", drawingId] }),
  });
  return <Card title="Classificação assistida">
    <p className="mb-2 text-xs text-slate-600">Confirme uma propriedade da entidade selecionada por vez. Nome de layer ou bloco é apenas uma sugestão.</p>
    {q.isPending && <p className="text-sm">Buscando sugestões…</p>}
    {q.error && <ErrorState error={q.error} />}
    {q.data?.conflict && <p role="alert" className="my-2 text-xs text-amber-900">Há sugestões conflitantes. Confira o elemento na planta.</p>}
    <ul className="mb-3 text-xs">{q.data?.candidates.map((c, i) => <li key={i}>Sugestão: {CLASS_NAMES[c.element_class] ?? c.element_class} · {c.evidence}</li>)}</ul>
    {!confirmed && <p className="text-sm text-amber-900">Confirme a unidade antes de classificar.</p>}
    {!floors.length && <p className="text-sm text-amber-900">Recorte o pavimento antes de classificar.</p>}
    {confirmed && floors.length > 0 && <form className="space-y-2 text-sm" onSubmit={(e) => { e.preventDefault(); save.mutate(); }}>
      <label className="block">Pavimento<select className="mt-1 w-full rounded border p-1" value={floorId} onChange={(e) => { setFloorId(e.target.value); setChecked(false); }}>
        {floors.map((f) => <option value={f.id} key={f.id}>{f.name}</option>)}
      </select></label>
      {item && <ul className="rounded bg-slate-50 p-2 text-xs">{Object.entries(item.properties).map(([key, p]) => <li key={key}>
        {key === "element_class" ? "Classe" : "Nome"}: {CLASS_NAMES[p.value] ?? p.value} · {p.status === "HUMAN_CONFIRMED" ? "confirmado" : "revisar"}
      </li>)}</ul>}
      <label className="block">Propriedade<select className="mt-1 w-full rounded border p-1" value={property} onChange={(e) => { setProperty(e.target.value); setChecked(false); }}>
        <option value="element_class">Classe do elemento</option><option value="name">Nome do elemento</option>
      </select></label>
      {property === "element_class" ? <label className="block">Classe<select className="mt-1 w-full rounded border p-1" value={elementClass} onChange={(e) => { setElementClass(e.target.value); setChecked(false); }}>
        {Object.entries(CLASS_NAMES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
      </select></label> : <label className="block">Nome<input className="mt-1 w-full rounded border p-1" value={name} onChange={(e) => { setName(e.target.value); setChecked(false); }} required maxLength={200} /></label>}
      <label className="block">Justificativa<textarea className="mt-1 w-full rounded border p-1" value={note} onChange={(e) => setNote(e.target.value)} required minLength={10} maxLength={2000} /></label>
      <label className="flex items-start gap-2 text-xs"><input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} required />Conferi a origem e esta propriedade na planta.</label>
      {save.error && <ErrorState error={save.error} />}
      {save.isSuccess && <p role="status" className="text-xs text-emerald-800">Propriedade registrada no histórico.</p>}
      <Button disabled={!checked || !q.data || save.isPending}>Confirmar propriedade</Button>
    </form>}
  </Card>;
}
