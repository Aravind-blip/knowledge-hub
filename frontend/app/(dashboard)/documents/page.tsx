import { DocumentsTable } from "@/components/documents-table";
import { EmptyState } from "@/components/empty-state";
import { MetricGrid } from "@/components/metric-grid";
import { PageHeader } from "@/components/page-header";
import { getDocuments, getWorkspaceSummary } from "@/lib/server-api";

function parsePage(value?: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

export default async function DocumentsPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolvedSearchParams = await searchParams;
  const page = parsePage(
    typeof resolvedSearchParams?.page === "string" ? resolvedSearchParams.page : undefined,
  );
  const [data, workspace] = await Promise.all([getDocuments(page, 20), getWorkspaceSummary()]);

  return (
    <section className="page">
      <PageHeader
        eyebrow="Operations"
        title="Indexed files"
        description={`Track organization documents, indexing status, and operational readiness inside ${workspace.organization_name}.`}
      />
      <MetricGrid metrics={workspace.performance_metrics} />
      {data.items.length === 0 ? (
        <EmptyState
          title="No files indexed yet"
          description="Upload a source document to start building a searchable organization knowledge workspace."
          actionHref="/documents/upload"
          actionLabel="Upload documents"
        />
      ) : (
        <DocumentsTable documents={data.items} page={data.page} pageSize={data.page_size} total={data.total} />
      )}
    </section>
  );
}
