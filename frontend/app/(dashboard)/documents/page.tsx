import { DocumentsTable } from "@/components/documents-table";
import { EmptyState } from "@/components/empty-state";
import { MetricGrid } from "@/components/metric-grid";
import { PageHeader } from "@/components/page-header";
import { getDocuments } from "@/lib/server-api";


export default async function DocumentsPage() {
  const data = await getDocuments();
  const indexedCount = data.items.filter((item) => item.status === "indexed").length;
  const totalChunks = data.items.reduce((sum, item) => sum + Number(item.metadata?.chunk_count ?? 0), 0);

  return (
    <section className="page">
      <PageHeader
        eyebrow="Operations"
        title="Indexed files"
        description="Track uploaded documents, indexing status, and source coverage across the workspace."
      />
      <MetricGrid
        metrics={[
          { label: "Indexed files", value: String(indexedCount), detail: "Files currently available for retrieval." },
          { label: "Total files", value: String(data.items.length), detail: "Uploaded records across the workspace." },
          { label: "Indexed chunks", value: String(totalChunks), detail: "Searchable source segments stored in Postgres." },
        ]}
      />
      {data.items.length === 0 ? (
        <EmptyState
          title="No files indexed yet"
          description="Upload a source document to start building a searchable reference workspace."
          actionHref="/documents/upload"
          actionLabel="Upload documents"
        />
      ) : (
        <DocumentsTable documents={data.items} />
      )}
    </section>
  );
}
