import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type LocalStatus, type Project } from "@coscip/api-client";
import { Card, EmptyState, ErrorState, PageHeader } from "@coscip/ui";

export function HomePage() {
  const status = useQuery({ queryKey: ["status"], queryFn: () => api<LocalStatus>("/local/status") });
  const projects = useQuery({
    queryKey: ["projects", "recent"],
    queryFn: () => api<{ items: Project[] }>("/projects?limit=5"),
  });

  return (
    <>
      <PageHeader title="Início" />
      {status.error && <ErrorState error={status.error} />}
      <div className="grid gap-4 md:grid-cols-3">
        <Card title="Pasta de dados">
          <p className="text-lg font-semibold">{status.data?.data_dir_label ?? "—"}</p>
          <p className="text-xs text-slate-500">
            {status.data ? `${(status.data.free_disk_bytes / 1e9).toFixed(1)} GB livres` : ""}
          </p>
        </Card>
        <Card title="Último backup verificado">
          <p className="text-lg font-semibold">
            {status.data?.last_verified_backup_at
              ? new Date(status.data.last_verified_backup_at).toLocaleString("pt-BR")
              : "Nenhum"}
          </p>
          {!status.data?.last_verified_backup_at && (
            <p className="text-xs text-amber-700">Configure o destino e faça o primeiro backup.</p>
          )}
        </Card>
        <Card title="Fila">
          <p className="text-lg font-semibold">{status.data?.queue.active_or_waiting ?? 0} execução(ões)</p>
          <p className="text-xs text-slate-500">IA {status.data?.ai_enabled ? "habilitada" : "desativada"}</p>
        </Card>
      </div>
      <div className="mt-6">
        <Card title="Projetos recentes">
          {projects.error && <ErrorState error={projects.error} />}
          {projects.data?.items.length === 0 && (
            <EmptyState>
              Nenhum projeto ainda. <Link className="text-teal-700 underline" to="/projetos">Criar projeto</Link>
            </EmptyState>
          )}
          <ul className="divide-y divide-slate-100">
            {projects.data?.items.map((p) => (
              <li key={p.id} className="py-2">
                <Link className="text-teal-800 hover:underline" to={`/projetos/${p.id}`}>{p.name}</Link>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
