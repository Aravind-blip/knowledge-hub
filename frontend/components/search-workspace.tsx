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
        <div className="guidance-card">
          <div className="guidance-card__item">
            <strong>Best results</strong>
            <span>Use specific process, policy, or exception questions.</span>
          </div>
          <div className="guidance-card__item">
            <strong>Sources returned</strong>
            <span>Every result includes the file name and supporting excerpt.</span>
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
            <h2>{initialSession ? "Results" : "Before you search"}</h2>
            <p>
              {initialSession
                ? `Session opened ${formatDate(initialSession.created_at)}`
                : "Upload organization reference material first, then ask specific questions about policy, support, or operations content."}
            </p>
          </div>
        </div>

        {!initialSession ? (
          <div className="empty-state empty-state--inline">
            <div className="empty-state__badge">Ready</div>
            <h2>No active session</h2>
            <p>Results will appear here with source excerpts and file references once you submit a request.</p>
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
