import { DocumentsTable } from "@/components/documents-table";
import { EmptyState } from "@/components/empty-state";
import { MetricGrid } from "@/components/metric-grid";
import { PageHeader } from "@/components/page-header";
import { getDocuments, getWorkspaceSummary } from "@/lib/server-api";


export default async function DocumentsPage() {
  const [data, workspace] = await Promise.all([getDocuments(), getWorkspaceSummary()]);

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
        <DocumentsTable documents={data.items} />
      )}
    </section>
  );
}
