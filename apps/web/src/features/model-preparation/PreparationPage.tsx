import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "@coscip/api-client";
import { Button, Card, EmptyState, ErrorState, PageHeader } from "@coscip/ui";

interface Drawing {
  id: string; file: string; scene_available: boolean;
  unit: { confirmed: boolean; unit: string | null };
  floors: { id: string; name: string }[];
  model_snapshot: { id: string } | null;
}

export function PreparationPage() {
  const { revisionId = "" } = useParams();
  const q = useQuery({ queryKey: ["drawings", revisionId],
    queryFn: () => api<{ items: Drawing[] }>(`/revisions/${revisionId}/drawings`) });
  const report = useMutation({
    mutationFn: (modelId: string) => api<{ content_url: string; sha256: string }>(`/models/${modelId}/preparation-report`, { method: "POST" }),
  });
  return <>
    <PageHeader title="Preparação da planta"><Link className="text-sm text-teal-800 underline" to="/unidades">Revisar confirmações de unidade</Link></PageHeader>
    <p className="mb-4 text-sm text-slate-600">Abra o desenho, confira a unidade e recorte um pavimento. Selecione os elementos para preparar suas propriedades.</p>
    {q.isPending && <p>Carregando desenhos…</p>}
    {q.error && <ErrorState error={q.error} />}
    {q.data?.items.length === 0 && <EmptyState>Importe um DXF para iniciar a preparação.</EmptyState>}
    {report.error && <ErrorState error={report.error} />}
    {report.data && <p role="status" className="mb-4 break-all text-sm"><a className="text-teal-800 underline" href={report.data.content_url} target="_blank" rel="noreferrer">Abrir relatório de preparação</a><br />SHA-256: {report.data.sha256}</p>}
    <div className="grid gap-4">{q.data?.items.map((d) => <Card key={d.id} title={d.file}>
      <p className="mb-2 text-sm">{d.unit.confirmed ? `Unidade confirmada: ${d.unit.unit}` : "Unidade pendente"} · {d.floors.length} pavimento(s)</p>
      <Link className="text-sm text-teal-800 underline" to={`/desenhos/${d.id}`}>{d.scene_available ? "Abrir planta e preparar" : "Abrir diagnóstico do desenho"}</Link>
      {d.model_snapshot && <Button className="ml-3" variant="ghost" disabled={report.isPending} onClick={() => report.mutate(d.model_snapshot!.id)}>Emitir relatório da preparação</Button>}
    </Card>)}</div>
  </>;
}
