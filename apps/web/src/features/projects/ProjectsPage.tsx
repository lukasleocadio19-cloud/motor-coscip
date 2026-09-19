import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, type Project } from "@coscip/api-client";
import { Button, Card, EmptyState, ErrorState, PageHeader } from "@coscip/ui";

export function ProjectsPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [name, setName] = useState("");
  const list = useQuery({
    queryKey: ["projects", q],
    queryFn: () => api<{ items: Project[] }>(`/projects?q=${encodeURIComponent(q)}`),
  });
  const create = useMutation({
    mutationFn: (n: string) => api<Project>("/projects", { method: "POST", json: { name: n } }),
    onSuccess: () => {
      setName("");
      void qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  return (
    <>
      <PageHeader title="Projetos" />
      <div className="grid gap-4 md:grid-cols-[1fr_320px]">
        <Card>
          <label className="mb-3 block text-sm">
            <span className="sr-only">Buscar</span>
            <input
              className="w-full rounded border border-slate-300 px-3 py-1.5"
              placeholder="Buscar por nome"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </label>
          {list.error && <ErrorState error={list.error} />}
          {list.data?.items.length === 0 && <EmptyState>Nenhum projeto encontrado.</EmptyState>}
          <table className="w-full text-sm">
            <thead className="text-left text-xs text-slate-500">
              <tr><th className="py-1">Nome</th><th>Responsável</th><th>Criado em</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {list.data?.items.map((p) => (
                <tr key={p.id}>
                  <td className="py-2"><Link className="text-teal-800 hover:underline" to={`/projetos/${p.id}`}>{p.name}</Link></td>
                  <td>{p.responsible ?? "—"}</td>
                  <td>{new Date(p.created_at).toLocaleDateString("pt-BR")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Novo projeto">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) create.mutate(name.trim());
            }}
            className="space-y-3"
          >
            <label className="block text-sm">
              Nome
              <input
                className="mt-1 w-full rounded border border-slate-300 px-3 py-1.5"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            {create.error && <ErrorState error={create.error} />}
            <Button type="submit" disabled={create.isPending}>Criar projeto</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
