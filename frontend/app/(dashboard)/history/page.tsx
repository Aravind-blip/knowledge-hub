import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { ListPagination } from "@/components/list-pagination";
import { PageHeader } from "@/components/page-header";
import { getSessions } from "@/lib/server-api";
import { formatDate } from "@/lib/utils";

function parsePage(value?: string) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}

export default async function HistoryPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const resolvedSearchParams = await searchParams;
  const page = parsePage(
    typeof resolvedSearchParams?.page === "string" ? resolvedSearchParams.page : undefined,
  );
  const data = await getSessions(page, 15);

  return (
    <section className="page">
      <PageHeader
        eyebrow="History"
        title="Chat history"
        description="Review previous sessions that belong to your organization workspace and reopen any answer thread you own."
      />
      {data.items.length === 0 ? (
        <EmptyState
          title="No saved sessions yet"
          description="Ask a question after indexing documents and your session history will appear here."
          actionHref="/search"
          actionLabel="Search answers"
        />
      ) : (
        <div className="panel">
          <div className="panel__header">
            <div>
              <h2>Recent sessions</h2>
              <p>Review the answer threads you own inside your organization workspace.</p>
            </div>
          </div>
          <ListPagination basePath="/history" page={data.page} pageSize={data.page_size} total={data.total} />
          <div className="conversation">
            {data.items.map((session) => (
              <article className="message-card" key={session.id}>
                <header className="message-card__header">
                  <span>{session.title}</span>
                  <time>{formatDate(session.updated_at)}</time>
                </header>
                <p className="message-card__content">
                  Created {formatDate(session.created_at)}. Continue this session to ask follow-up questions.
                </p>
                <div className="ask-form__actions">
                  <Link className="button button--secondary" href={`/answers/${session.id}`}>
                    Open session
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
