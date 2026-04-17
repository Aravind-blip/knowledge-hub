import Link from "next/link";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { getSessions } from "@/lib/server-api";
import { formatDate } from "@/lib/utils";

export default async function HistoryPage() {
  const data = await getSessions();

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
