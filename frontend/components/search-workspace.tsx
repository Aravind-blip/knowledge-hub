"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import { useSessionTitle } from "@/hooks/use-session-title";
import type { AskResponse, SessionResponse } from "@/types";
import { formatDate } from "@/lib/utils";


async function askQuestion(question: string, sessionId?: string) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId ?? null }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? payload.error ?? "Unable to retrieve a result.");
  }
  return payload as AskResponse;
}


export function SearchWorkspace({
  initialSession,
  standalone = false,
}: {
  initialSession?: SessionResponse;
  standalone?: boolean;
}) {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const sessionTitle = useSessionTitle(initialSession);
  const mutation = useMutation({
    mutationFn: ({ prompt, sessionId }: { prompt: string; sessionId?: string }) => askQuestion(prompt, sessionId),
    onSuccess: (data) => {
      setQuestion("");
      router.push(`/answers/${data.session_id}`);
      router.refresh();
    },
  });

  const messages = useMemo(() => initialSession?.messages ?? [], [initialSession]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!question.trim()) return;
    mutation.mutate({ prompt: question.trim(), sessionId: initialSession?.id });
  }

  return (
    <div className={standalone ? "workspace workspace--standalone" : "workspace"}>
      <div className="panel panel--form">
        <div className="panel__header">
          <div>
            <h2>{initialSession ? `Continue: ${sessionTitle}` : "Search answers"}</h2>
            <p>Responses are generated only from indexed organization files. If the evidence is weak, the system returns a clear information gap.</p>
          </div>
        </div>
        <div className="guidance-card guidance-card--stacked">
          <div className="guidance-card__item">
            <strong>Best results</strong>
            <span>Use specific questions about process, policy, operations, or support workflows.</span>
          </div>
          <div className="guidance-card__item">
            <strong>Sources returned</strong>
            <span>Every answer includes document citations and supporting excerpts from your organization workspace.</span>
          </div>
        </div>
        <form className="ask-form" onSubmit={onSubmit}>
          <label className="ask-form__field">
            <span>Search request</span>
            <textarea
              name="question"
              rows={5}
              placeholder="Example: What is the escalation process for a delayed shipment?"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </label>
          <div className="ask-form__actions">
            <button className="button button--primary" disabled={mutation.isPending || !question.trim()} type="submit">
              {mutation.isPending ? "Searching..." : "Search answers"}
            </button>
          </div>
          {mutation.isError ? (
            <div className="callout callout--error">{(mutation.error as Error).message}</div>
          ) : null}
        </form>
      </div>

      <div className="panel">
        <div className="panel__header">
          <div>
            <h2>{initialSession ? "Results" : "How search behaves"}</h2>
            <p>
              {initialSession
                ? `Session opened ${formatDate(initialSession.created_at)}`
                : "Search runs only against indexed documents inside your organization. Results stay grounded to cited source material."}
            </p>
          </div>
        </div>

        {!initialSession ? (
          <div className="ops-list">
            <div className="ops-list__item">
              <strong>Scoped retrieval</strong>
              <span>Documents outside your organization are never part of the retrieval set.</span>
            </div>
            <div className="ops-list__item">
              <strong>Grounded responses</strong>
              <span>Low-confidence requests return an explicit information gap instead of a fabricated answer.</span>
            </div>
            <div className="ops-list__item">
              <strong>Reopenable history</strong>
              <span>Each submitted question creates a session that can be reopened and continued later.</span>
            </div>
          </div>
        ) : (
          <div className="conversation">
            {messages.map((message) => (
              <article className={`message-card message-card--${message.role}`} key={message.id}>
                <header className="message-card__header">
                  <span>{message.role === "user" ? "Request" : "Result"}</span>
                  <time>{formatDate(message.created_at)}</time>
                </header>
                <p className="message-card__content">{message.content}</p>
                {message.role === "system" && typeof message.metadata?.confidence_note === "string" ? (
                  <div className="callout callout--subtle">
                    {message.metadata.confidence_note}
                  </div>
                ) : null}
                {message.role === "system" && message.citations.length > 0 ? (
                  <div className="sources">
                    <h3>Sources</h3>
                    <ul className="source-list">
                      {message.citations.map((citation) => (
                        <li className="source-card" key={citation.chunk_id}>
                          <div className="source-card__meta">
                            <strong>{citation.file_name}</strong>
                            <span>
                              {citation.page_number ? `Page ${citation.page_number}` : "Text file"} · Relevance{" "}
                              {(citation.relevance_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p>{citation.snippet}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
