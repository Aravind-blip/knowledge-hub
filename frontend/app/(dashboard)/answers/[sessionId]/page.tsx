import { notFound } from "next/navigation";

import { PageHeader } from "@/components/page-header";
import { SearchWorkspace } from "@/components/search-workspace";
import { getSession } from "@/lib/server-api";


export default async function AnswersPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;

  try {
    const session = await getSession(sessionId);
    return (
      <section className="page">
        <PageHeader
          eyebrow="Results"
          title={session.title}
          description="Review cited excerpts, continue the session, and keep each result tied to source material."
        />
        <SearchWorkspace initialSession={session} />
      </section>
    );
  } catch {
    notFound();
  }
}
