import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "@coscip/api-client";
import { Button, Card, EmptyState, ErrorState, PageHeader } from "@coscip/ui";

interface ReviewItem {
  id: string; file: string | null; project_name: string; revision_number: number;
  unit: { unit: string | null; frame_id: string | null };
  status: "UNCONFIRMED" | "PENDING" | "ACCEPTED";
  confirmation: null | {
    id: string; frame_id: string; author: string; created_at: string; justification: string;
    reference: { a: number[]; b: number[]; measured_m: number; real_length_m: number; deviation: number };
  };
  review: null | { reviewer_name: string; created_at: string; justification: string };
}

function ReviewCard({ item }: { item: ReviewItem }) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [note, setNote] = useState("");
  const [checked, setChecked] = useState(false);
  const accept = useMutation({
    mutationFn: () => api(`/drawings/${item.id}/unit-review`, { method: "POST", json: {
      expected_frame_id: item.unit.frame_id, confirmation_id: item.confirmation?.id,
      reviewer_name: name, justification: note, reference_checked: checked,
    } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["unit-reviews"] }),
    onError: () => void qc.invalidateQueries({ queryKey: ["unit-reviews"] }),
  });
  const c = item.confirmation;
  return (
    <Card title={`${item.project_name} · revisão ${item.revision_number} · ${item.file ?? "Desenho"}`}>
      <Link className="text-sm text-teal-800 underline" to={`/desenhos/${item.id}`}>Abrir planta e conferir referência</Link>
      {!c && <p className="mt-3 text-sm text-amber-800">Unidade ainda não confirmada. Abra a planta para informar a referência.</p>}
      {c && <>
        <dl className="my-3 grid gap-1 text-sm">
          <div><dt className="inline font-medium">Unidade: </dt><dd className="inline">{item.unit.unit}</dd></div>
          <div><dt className="inline font-medium">Conta que registrou: </dt><dd className="inline">{c.author} · {new Date(c.created_at).toLocaleString("pt-BR")}</dd></div>
          <div><dt className="inline font-medium">Justificativa original: </dt><dd className="inline whitespace-pre-wrap">{c.justification}</dd></div>
          {c.reference && <>
            <div><dt className="inline font-medium">Referência informada: </dt><dd className="inline">{c.reference.real_length_m} m · calculada {c.reference.measured_m.toFixed(4)} m · desvio {(c.reference.deviation * 100).toFixed(2)}%</dd></div>
            <div><dt className="inline font-medium">Pontos no desenho: </dt><dd className="inline">({c.reference.a.join("; ")}) → ({c.reference.b.join("; ")})</dd></div>
          </>}
        </dl>
        {item.review ? <p role="status" className="rounded bg-emerald-50 p-3 text-sm text-emerald-900">
          Aceita por {item.review.reviewer_name} em {new Date(item.review.created_at).toLocaleString("pt-BR")}. {item.review.justification}
        </p> : <form className="grid max-w-xl gap-3 text-sm" onSubmit={(e) => { e.preventDefault(); accept.mutate(); }}>
          <label>Nome de quem revisou<input className="mt-1 block w-full rounded border p-2" value={name} onChange={(e) => setName(e.target.value)} required minLength={3} maxLength={200} /></label>
          <label>O que foi conferido<textarea className="mt-1 block w-full rounded border p-2" value={note} onChange={(e) => setNote(e.target.value)} required minLength={10} maxLength={2000} placeholder="Identifique a referência que você verificou" /></label>
          <label className="flex items-start gap-2"><input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} required />Conferi os pontos, a unidade e a medida de referência desta confirmação.</label>
          {accept.error && <ErrorState error={accept.error} />}
          <Button disabled={!checked || accept.isPending} type="submit">Aceitar confirmação revisada</Button>
        </form>}
      </>}
    </Card>
  );
}

export function UnitReviewPage() {
  const [offset, setOffset] = useState(0);
  const q = useQuery({ queryKey: ["unit-reviews", offset],
    queryFn: () => api<{ items: ReviewItem[]; next_offset: number | null }>(`/unit-reviews?offset=${offset}`) });
  return <>
    <PageHeader title="Revisão das unidades" />
    <p className="mb-4 text-sm text-slate-600">Confira cada referência antes de aceitar. A conta local pode ter sido usada por um assistente; leia a justificativa original. Esta revisão não substitui a medida independente necessária para validar o motor.</p>
    {q.isPending && <p>Carregando confirmações…</p>}
    {q.error && <ErrorState error={q.error} />}
    {q.data?.items.length === 0 && <EmptyState>Nenhum desenho nesta página.</EmptyState>}
    <div className="grid gap-4">{q.data?.items.map((item) => <ReviewCard key={`${item.id}:${item.unit.frame_id}`} item={item} />)}</div>
    <div className="mt-4 flex gap-3">
      <Button variant="ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>Anterior</Button>
      <Button variant="ghost" disabled={q.data?.next_offset == null} onClick={() => setOffset(q.data!.next_offset!)}>Próxima</Button>
    </div>
  </>;
}
