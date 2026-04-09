import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { MetricGrid } from "@/components/metric-grid";
import { PageHeader } from "@/components/page-header";
import { SearchWorkspace } from "@/components/search-workspace";
import { getDocuments } from "@/lib/server-api";


export default async function SearchPage() {
  const documents = await getDocuments();

  return (
    <section className="page">
      <PageHeader
        eyebrow="Search"
        title="Search answers"
        description="Search across indexed files and review grounded source excerpts for each response."
        actions={
          <Link className="button button--secondary" href="/documents/upload">
            Upload documents
          </Link>
        }
      />
      <MetricGrid
        metrics={[
          { label: "Indexed files", value: String(documents.items.length), detail: "Available sources in the current workspace." },
          { label: "Evidence policy", value: "Strict", detail: "Low-confidence retrieval returns an explicit information gap." },
          { label: "Source format", value: "Cited", detail: "Each result includes file attribution and excerpt text." },
        ]}
      />
      {documents.items.length === 0 ? (
        <EmptyState
          title="Documents are required before searching"
          description="Upload at least one file so the workspace has source material to retrieve from."
          actionHref="/documents/upload"
          actionLabel="Upload documents"
        />
      ) : (
        <SearchWorkspace standalone />
      )}
    </section>
  );
}
