import type { ReactNode } from "react";

/** Estados sempre com cor + ícone + texto (plano §12, acessibilidade). */
const STATUS = {
  PASS: { label: "Conforme", icon: "✓", cls: "bg-emerald-50 text-emerald-800 ring-emerald-600/30" },
  FAIL: { label: "Pendência", icon: "✕", cls: "bg-red-50 text-red-800 ring-red-600/30" },
  REVIEW_REQUIRED: { label: "Revisão humana", icon: "?", cls: "bg-amber-50 text-amber-900 ring-amber-600/30" },
  NOT_APPLICABLE: { label: "Não se aplica", icon: "–", cls: "bg-slate-50 text-slate-700 ring-slate-500/30" },
  MISSING_DATA: { label: "Dado ausente", icon: "!", cls: "bg-orange-50 text-orange-900 ring-orange-600/30" },
  UNSUPPORTED: { label: "Fora de cobertura", icon: "∅", cls: "bg-slate-100 text-slate-600 ring-slate-400/30" },
} as const;

export type StatusKey = keyof typeof STATUS;

export function StatusBadge({ status }: { status: StatusKey }) {
  const s = STATUS[status];
  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium ring-1 ${s.cls}`}>
      <span aria-hidden="true">{s.icon}</span>
      {s.label}
    </span>
  );
}

const EXEC_LABELS: Record<string, string> = {
  CREATED: "Criada",
  QUEUED: "Na fila",
  RUNNING: "Em execução",
  CANCEL_REQUESTED: "Cancelando",
  SUCCEEDED: "Concluída",
  PARTIAL: "Parcial",
  WAITING_INPUT: "Aguardando informação",
  FAILED: "Falhou",
  CANCELLED: "Cancelada",
};

export function ExecutionBadge({ state }: { state: string }) {
  return (
    <span className="inline-flex rounded bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700 ring-1 ring-slate-300">
      {EXEC_LABELS[state] ?? state}
    </span>
  );
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{title}</h1>
      <div className="flex gap-2">{children}</div>
    </header>
  );
}

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-5">
      {title && <h2 className="mb-3 text-sm font-semibold text-slate-700">{title}</h2>}
      {children}
    </section>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className="rounded border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">{children}</p>;
}

export function ErrorState({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
      {msg}
    </p>
  );
}

export function NotYet({ backlog, children }: { backlog: string; children?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-5 text-sm text-slate-600">
      <p className="font-medium text-slate-700">Ainda não construído — backlog {backlog}</p>
      {children && <div className="mt-2">{children}</div>}
    </div>
  );
}

export function Button(props: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" }) {
  const { variant = "primary", className = "", ...rest } = props;
  const base = "rounded-md px-3 py-1.5 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50";
  const look = variant === "primary"
    ? "bg-teal-700 text-white hover:bg-teal-800 focus-visible:outline-teal-700"
    : "text-slate-700 ring-1 ring-slate-300 hover:bg-slate-50";
  return <button className={`${base} ${look} ${className}`} {...rest} />;
}
