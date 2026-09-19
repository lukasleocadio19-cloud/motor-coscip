import { Card, NotYet, PageHeader } from "@coscip/ui";

export function ReportPage() {
  return (
    <>
      <PageHeader title="Relatório" />
      <Card>
        <NotYet backlog="REP-01 / REP-02">
          Resumo, cobertura, pendências, hashes, fontes e decisões humanas. HTML por template e PDF
          local; um relatório emitido nunca muda — nova emissão recebe novo ID.
        </NotYet>
      </Card>
    </>
  );
}
