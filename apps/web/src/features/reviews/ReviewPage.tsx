import { Card, NotYet, PageHeader } from "@coscip/ui";

export function ReviewPage() {
  return (
    <>
      <PageHeader title="Revisão humana" />
      <Card>
        <NotYet backlog="REV-01">
          Fila por prioridade. Decisões (confirmar, contestar, solicitar dado, resolver por nova
          revisão) são registros separados, com autor e justificativa — não reescrevem o cálculo.
        </NotYet>
      </Card>
    </>
  );
}
