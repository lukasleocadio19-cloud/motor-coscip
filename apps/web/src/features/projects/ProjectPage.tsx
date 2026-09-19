import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, type Revision } from "@coscip/api-client";
import { Button, Card, EmptyState, ErrorState, NotYet, PageHeader } from "@coscip/ui";

export function ProjectPage() {
  const { projectId = "" } = useParams();
  const qc = useQueryClient();
  const revisions = useQuery({
    queryKey: ["revisions", projectId],
    queryFn: () => api<{ items: Revision[] }>(`/projects/${projectId}/revisions`),
  });
  const newRevision = useMutation({
    mutationFn: () => api<Revision>(`/projects/${projectId}/revisions`, { method: "POST" }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["revisions", projectId] }),
  });

  return (
    <>
      <PageHeader title="Projeto">
        <Link to={`/projetos/${projectId}/historico`} className="rounded-md px-3 py-1.5 text-sm ring-1 ring-slate-300">
          Histórico
        </Link>
        <Button onClick={() => newRevision.mutate()} disabled={newRevision.isPending}>Nova revisão</Button>
      </PageHeader>
      <div className="grid gap-4">
        <Card title="Cadastro e contexto de aplicabilidade">
          <NotYet backlog="REG-03">
            Ocupações, áreas, alturas e datas com a fonte de cada informação. Uso misto pode ter
            valores por setor; o recorte geométrico não redefine o contexto da edificação.
          </NotYet>
        </Card>
        <Card title="Revisões">
          {revisions.error && <ErrorState error={revisions.error} />}
          {revisions.data?.items.length === 0 && <EmptyState>Crie a primeira revisão para enviar arquivos.</EmptyState>}
          <ul className="divide-y divide-slate-100">
            {revisions.data?.items.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  Revisão {r.number} · {r.state === "SEALED" ? "selada" : "rascunho"}
                  {r.manifest_sha256 && <code className="ml-2 text-xs text-slate-500">{r.manifest_sha256.slice(0, 12)}…</code>}
                </span>
                <span className="flex gap-3">
                  <Link className="text-teal-800 hover:underline" to={`/revisoes/${r.id}/arquivos`}>Arquivos</Link>
                  <Link className="text-teal-800 hover:underline" to={`/revisoes/${r.id}/diagnostico`}>Diagnóstico</Link>
                  <Link className="text-teal-800 hover:underline" to={`/revisoes/${r.id}/preparacao`}>Preparação</Link>
                </span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
