import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type LocalStatus } from "@coscip/api-client";
import { Button, Card, ErrorState, NotYet, PageHeader } from "@coscip/ui";

export function OperationPage() {
  const status = useQuery({ queryKey: ["status"], queryFn: () => api<LocalStatus>("/local/status") });
  const backup = useMutation({
    mutationFn: () => api<{ state: string; destination_label: string }>("/backups", { method: "POST" }),
    onSuccess: () => void status.refetch(),
  });

  return (
    <>
      <PageHeader title="Operação" />
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Backup">
          <p className="mb-3 text-sm text-slate-600">
            Cópia consistente do banco e dos artefatos, verificada por hash. Guarde em outro
            dispositivo: uma segunda pasta no mesmo SSD não protege contra falha do disco.
          </p>
          {backup.error && <ErrorState error={backup.error} />}
          {backup.data && <p className="mb-2 text-sm text-emerald-800">✓ {backup.data.state} em {backup.data.destination_label}</p>}
          <Button onClick={() => backup.mutate()} disabled={backup.isPending}>Fazer backup agora</Button>
        </Card>
        <Card title="Recursos">
          <p className="text-sm">Disco livre: {status.data ? `${(status.data.free_disk_bytes / 1e9).toFixed(1)} GB` : "—"}</p>
          <p className="text-sm">Execuções ativas ou na fila: {status.data?.queue.active_or_waiting ?? "—"}</p>
        </Card>
        <Card title="Jobs e falhas">
          <NotYet backlog="LOC-10">Lista de execuções com estágio, duração, memória máxima e erro.</NotYet>
        </Card>
        <Card title="Consumo de API">
          <NotYet backlog="AI-03">Reservado × liquidado por projeto e mês, com teto configurado.</NotYet>
        </Card>
      </div>
    </>
  );
}
