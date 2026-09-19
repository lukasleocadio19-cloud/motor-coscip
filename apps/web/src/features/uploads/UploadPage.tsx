import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, uploadFile, type ExecutionOut } from "@coscip/api-client";
import { Button, Card, ErrorState, ExecutionBadge, PageHeader } from "@coscip/ui";
import { useExecution } from "../operation/useExecution";

type Role = "ANALYTIC_DXF" | "XREF_DXF" | "SOURCE_DWG" | "DOCUMENT";

export function UploadPage() {
  const { revisionId = "" } = useParams();
  const [file, setFile] = useState<File | null>(null);
  const [role, setRole] = useState<Role>("ANALYTIC_DXF");
  const [progress, setProgress] = useState<[number, number] | null>(null);
  const [uploaded, setUploaded] = useState<string[]>([]);
  const [executionId, setExecutionId] = useState<string | null>(null);
  const execution = useExecution(executionId);

  const upload = useMutation({
    mutationFn: () => uploadFile(revisionId, file!, role, (s, t) => setProgress([s, t])),
    onSuccess: (r) => setUploaded((u) => [...u, `${file!.name} · ${r.sha256.slice(0, 12)}…`]),
  });
  const sealAndImport = useMutation({
    mutationFn: async () => {
      await api(`/revisions/${revisionId}/seal`, { method: "POST" });
      return api<ExecutionOut>(`/revisions/${revisionId}/imports`, {
        method: "POST",
        idempotencyKey: `import-${revisionId}`,
      });
    },
    onSuccess: (r) => setExecutionId(r.execution_id),
  });

  return (
    <>
      <PageHeader title="Arquivos da revisão" />
      <div className="grid gap-4 md:grid-cols-2">
        <Card title="Enviar arquivo">
          <p className="mb-3 text-xs text-slate-500">
            DXF é a entrada analítica. DWG entra apenas como documento de origem: solicite ou
            exporte o DXF correspondente.
          </p>
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (file) upload.mutate();
            }}
          >
            <label className="block text-sm">
              Função
              <select className="mt-1 w-full rounded border border-slate-300 px-2 py-1.5" value={role}
                onChange={(e) => setRole(e.target.value as Role)}>
                <option value="ANALYTIC_DXF">DXF analítico</option>
                <option value="XREF_DXF">XRef DXF (pacote)</option>
                <option value="SOURCE_DWG">DWG de origem</option>
                <option value="DOCUMENT">Documento (PDF/texto)</option>
              </select>
            </label>
            <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            {progress && (
              <p className="text-xs text-slate-600">{(progress[0] / 1e6).toFixed(1)} de {(progress[1] / 1e6).toFixed(1)} MB</p>
            )}
            {upload.error && <ErrorState error={upload.error} />}
            <Button type="submit" disabled={!file || upload.isPending}>Enviar</Button>
          </form>
        </Card>
        <Card title="Submissão">
          <ul className="mb-3 text-sm">
            {uploaded.map((u) => <li key={u}>✓ {u}</li>)}
          </ul>
          <p className="mb-3 text-xs text-slate-500">
            Selar congela o manifesto; a revisão passa a ser imutável.
          </p>
          {sealAndImport.error && <ErrorState error={sealAndImport.error} />}
          <Button onClick={() => sealAndImport.mutate()} disabled={sealAndImport.isPending || !uploaded.length}>
            Selar e importar
          </Button>
          {execution.data && (
            <div className="mt-4 text-sm">
              <ExecutionBadge state={execution.data.state} /> {execution.data.stage && `estágio ${execution.data.stage}`}
              {execution.data.error_code && <p className="mt-1 text-amber-800">{execution.data.error_code}</p>}
              <p className="mt-2"><Link className="text-teal-800 underline" to={`/revisoes/${revisionId}/diagnostico`}>Ver diagnóstico</Link></p>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
