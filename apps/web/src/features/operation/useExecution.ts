import { useQuery } from "@tanstack/react-query";
import { api, type ExecutionOut } from "@coscip/api-client";

const TERMINAL = new Set(["SUCCEEDED", "PARTIAL", "FAILED", "CANCELLED", "WAITING_INPUT"]);

/** Consulta em intervalo moderado até estado terminal (SSE disponível em /events). */
export function useExecution(id: string | null) {
  return useQuery({
    queryKey: ["execution", id],
    queryFn: () => api<ExecutionOut>(`/executions/${id}`),
    enabled: !!id,
    refetchInterval: (q) => (q.state.data && TERMINAL.has(q.state.data.state) ? false : 1500),
  });
}
