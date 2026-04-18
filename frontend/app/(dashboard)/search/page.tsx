import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { MetricGrid } from "@/components/metric-grid";
import { PageHeader } from "@/components/page-header";
import { SearchWorkspace } from "@/components/search-workspace";
import { getWorkspaceSummary } from "@/lib/server-api";


export default async function SearchPage() {
  const workspace = await getWorkspaceSummary();
  const hasDocuments = workspace.activity.total_documents > 0;

  return (
    <section className="page">
      <PageHeader
        eyebrow="Search"
        title="Search answers"
        description={`Search across ${workspace.organization_name} documents and review grounded source excerpts for each response.`}
        actions={
          <Link className="button button--secondary" href="/documents/upload">
            Upload documents
          </Link>
        }
      />
      <MetricGrid metrics={workspace.quality_metrics} />
      {hasDocuments ? (
        <SearchWorkspace standalone />
      ) : (
        <EmptyState
          title="Documents are required before searching"
          description="Upload at least one organization document so the workspace has source material to retrieve from."
          actionHref="/documents/upload"
          actionLabel="Upload documents"
        />
      )}
    </section>
  );
}
