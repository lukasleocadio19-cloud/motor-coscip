import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@coscip/api-client";
import { Button, ErrorState, StatusBadge } from "@coscip/ui";

import type { ReviewDecision, ReviewItem, RuleResult } from "./types";

type Verdict = "PASS" | "FAIL" | "NOT_APPLICABLE" | "REQUEST_DATA";

const VERDICTS: { v: Verdict; label: string }[] = [
  { v: "PASS", label: "Conforme" },
  { v: "FAIL", label: "Não conforme" },
  { v: "NOT_APPLICABLE", label: "Não se aplica" },
  { v: "REQUEST_DATA", label: "Pedir dado" },
];

const DECISION_LABEL: Record<ReviewDecision["decision"], string> = {
  CONFIRM: "concluiu",
  CONTEST: "divergiu do cálculo",
  REQUEST_DATA: "pediu dado",
  RESOLVED_BY_NEW_REVISION: "resolvido em nova revisão",
};

/**
 * Decisão do analista sobre um resultado (append-only). CONFIRM quando o veredito coincide com
 * o cálculo (ou o indicativo) ou quando o cálculo foi inconclusivo; CONTEST quando diverge.
 */
export function ReviewBox({ result, item, analysisId }: { result: RuleResult; item?: ReviewItem; analysisId: string }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [verdict, setVerdict] = useState<Verdict | "">("");
  const [text, setText] = useState("");
  const [history, setHistory] = useState(false);
  const last = item?.decisions[0];

  const save = useMutation({
    mutationFn: () => {
      const machine = result.status === "PASS" || result.status === "FAIL" || result.status === "NOT_APPLICABLE"
        ? result.status : result.trace?.indicative;
      // Cálculo inconclusivo (sem indicativo atende/não atende): o veredito não diverge de nada.
      const conclusive = machine === "PASS" || machine === "FAIL" || machine === "NOT_APPLICABLE";
      const decision = verdict === "REQUEST_DATA" ? "REQUEST_DATA"
        : !conclusive || verdict === machine ? "CONFIRM" : "CONTEST";
      return api(`/results/${item!.result_id}/reviews`, {
        method: "POST",
        json: {
          decision,
          final_status: verdict === "REQUEST_DATA" ? null : verdict,
          justification: text.trim(),
        },
      });
    },
    onSuccess: () => {
      setOpen(false);
      setVerdict("");
      setText("");
      void qc.invalidateQueries({ queryKey: ["plant-reviews", analysisId] });
    },
  });

  if (!item) return null;
  return (
    <div className="mt-2 border-t border-slate-100 pt-2">
      {last && (
        <div className="text-xs text-slate-700">
          <span className="font-medium">Analista:</span>{" "}
          {last.final_status ? <StatusBadge status={last.final_status} /> : <span className="text-orange-900">dado solicitado</span>}{" "}
          <span className="text-slate-500">({DECISION_LABEL[last.decision]}{last.created_at ? `, ${new Date(last.created_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}` : ""})</span>
          <p className="mt-0.5 text-slate-600">“{last.justification}”</p>
          {item.decisions.length > 1 && (
            <button className="text-slate-500 underline" onClick={() => setHistory(!history)}>
              {history ? "ocultar" : "ver"} histórico ({item.decisions.length})
            </button>
          )}
          {history && (
            <ul className="mt-1 space-y-0.5 text-slate-500">
              {item.decisions.slice(1).map((d) => (
                <li key={d.id}>{DECISION_LABEL[d.decision]}{d.final_status ? ` → ${d.final_status}` : ""} — {d.justification}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {!open ? (
        <button className="mt-1 text-xs font-medium text-teal-800 underline" onClick={() => setOpen(true)}>
          {last ? "Nova decisão" : "Revisar"}
        </button>
      ) : (
        <form
          className="mt-1 space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (verdict && text.trim().length >= 3) save.mutate();
          }}
        >
          <fieldset className="flex flex-wrap gap-3 text-xs">
            <legend className="sr-only">Veredito</legend>
            {VERDICTS.map((v) => (
              <label key={v.v} className="flex items-center gap-1">
                <input type="radio" name={`v-${item.result_id}`} checked={verdict === v.v} onChange={() => setVerdict(v.v)} />
                {v.label}
              </label>
            ))}
          </fieldset>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={2}
            maxLength={2000}
            placeholder="Justificativa (o que foi conferido, em qual folha ou documento)"
            aria-label="Justificativa"
            className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
          />
          <div className="flex gap-2">
            <Button type="submit" disabled={!verdict || text.trim().length < 3 || save.isPending}>
              {save.isPending ? "Salvando…" : "Registrar decisão"}
            </Button>
            <Button type="button" variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
          </div>
          {save.error && <ErrorState error={save.error} />}
        </form>
      )}
    </div>
  );
}
