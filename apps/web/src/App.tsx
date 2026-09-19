import { lazy, Suspense } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { HomePage } from "./features/home/HomePage";
import { ProjectsPage } from "./features/projects/ProjectsPage";
import { ProjectPage } from "./features/projects/ProjectPage";
import { UploadPage } from "./features/uploads/UploadPage";
import { DiagnosticsPage } from "./features/uploads/DiagnosticsPage";
import { PreparationPage } from "./features/model-preparation/PreparationPage";
import { UnitReviewPage } from "./features/reviews/UnitReviewPage";
import { ReviewPage } from "./features/reviews/ReviewPage";
import { HistoryPage } from "./features/reviews/HistoryPage";
import { ReportPage } from "./features/reports/ReportPage";
import { SettingsPage } from "./features/local-settings/SettingsPage";
import { OperationPage } from "./features/operation/OperationPage";

// Three.js só carrega ao abrir a análise.
const AnalysisPage = lazy(() =>
  import("./features/analysis/AnalysisPage").then((m) => ({ default: m.AnalysisPage })),
);

const DrawingPage = lazy(() =>
  import("./features/drawing/DrawingPage").then((m) => ({ default: m.DrawingPage })),
);

const NAV = [
  { to: "/", label: "Início" },
  { to: "/projetos", label: "Projetos" },
  { to: "/unidades", label: "Revisar unidades" },
  { to: "/operacao", label: "Operação" },
  { to: "/configuracoes", label: "Configurações" },
];

export function App() {
  return (
    <div className="min-h-screen md:flex">
      <aside className="bg-[#102e38] px-5 py-6 text-white md:w-60 md:shrink-0">
        <p className="text-lg font-bold leading-tight">Motor CAD/COSCIP</p>
        <p className="mt-1 text-xs text-teal-100/70">Local · DXF · um operador</p>
        <nav className="mt-6 flex gap-1 md:flex-col" aria-label="Principal">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                `rounded px-3 py-2 text-sm ${isActive ? "bg-white/15 font-semibold" : "text-teal-50/80 hover:bg-white/10"}`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 md:px-10">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/projetos" element={<ProjectsPage />} />
          <Route path="/unidades" element={<UnitReviewPage />} />
          <Route path="/projetos/:projectId" element={<ProjectPage />} />
          <Route path="/revisoes/:revisionId/arquivos" element={<UploadPage />} />
          <Route path="/revisoes/:revisionId/diagnostico" element={<DiagnosticsPage />} />
          <Route path="/revisoes/:revisionId/preparacao" element={<PreparationPage />} />
          <Route
            path="/analises/:analysisId"
            element={<Suspense fallback={<p>Carregando planta…</p>}><AnalysisPage /></Suspense>}
          />
          <Route
            path="/desenhos/:drawingId"
            element={<Suspense fallback={<p>Carregando planta…</p>}><DrawingPage /></Suspense>}
          />
          <Route path="/analises/:analysisId/revisao" element={<ReviewPage />} />
          <Route path="/projetos/:projectId/historico" element={<HistoryPage />} />
          <Route path="/analises/:analysisId/relatorio" element={<ReportPage />} />
          <Route path="/configuracoes" element={<SettingsPage />} />
          <Route path="/operacao" element={<OperationPage />} />
        </Routes>
      </main>
    </div>
  );
}

