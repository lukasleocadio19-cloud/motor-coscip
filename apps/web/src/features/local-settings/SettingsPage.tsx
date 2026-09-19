import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@coscip/api-client";
import { Button, Card, ErrorState, PageHeader } from "@coscip/ui";

interface SettingsOut {
  ai_enabled: boolean;
  ai_provider: string | null;
  ai_per_analysis_usd: string;
  ai_per_month_usd: string;
  worker_memory_mb: number;
  worker_timeout_s: number;
  credential_ids: string[];
  backup_destination_label: string | null;
}

export function SettingsPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["settings"], queryFn: () => api<SettingsOut>("/settings") });
  const save = useMutation({
    mutationFn: (changes: Partial<SettingsOut>) => api("/settings", { method: "PATCH", json: changes }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["settings"] }),
  });
  const s = q.data;

  return (
    <>
      <PageHeader title="Configurações locais" />
      {q.error && <ErrorState error={q.error} />}
      {s && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="IA por API (opcional)">
            <p className="mb-3 text-sm text-slate-600">
              Desligada por padrão. Cálculos, regras implementadas e relatórios por template
              funcionam sem IA. Ao habilitar, apenas trechos necessários são enviados.
            </p>
            <p className="text-sm">Estado: <strong>{s.ai_enabled ? "habilitada" : "desativada"}</strong></p>
            <p className="text-sm">Teto: US$ {s.ai_per_analysis_usd}/análise · US$ {s.ai_per_month_usd}/mês</p>
            <p className="text-sm">Credenciais cadastradas: {s.credential_ids.length || "nenhuma"}</p>
            <p className="mt-2 text-xs text-slate-500">
              Chaves ficam no cofre do Windows e nunca voltam para esta tela.
            </p>
            {save.error && <ErrorState error={save.error} />}
            <Button className="mt-3" variant="ghost" disabled={save.isPending || (!s.ai_enabled && !s.credential_ids.length)}
              onClick={() => save.mutate({ ai_enabled: !s.ai_enabled })}>
              {s.ai_enabled ? "Desativar IA" : "Habilitar IA"}
            </Button>
          </Card>
          <Card title="Limites do worker">
            <p className="text-sm">Memória: {s.worker_memory_mb} MB</p>
            <p className="text-sm">Tempo máximo por estágio: {Math.round(s.worker_timeout_s / 60)} min</p>
            <p className="mt-2 text-xs text-slate-500">Uma análise pesada por vez. Ajustar após benchmark.</p>
          </Card>
          <Card title="Backup">
            <p className="text-sm">Destino: {s.backup_destination_label ?? "não configurado"}</p>
            <p className="mt-2 text-xs text-slate-500">
              O caminho de destino é cadastrado pelo launcher (scripts/backup), não pela página.
            </p>
          </Card>
        </div>
      )}
    </>
  );
}
