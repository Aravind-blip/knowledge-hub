"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

type Mode = "signin" | "signup";

export function AuthForm() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsPending(true);
    setError(null);
    setMessage(null);

    const supabase = createSupabaseBrowserClient();
    const result =
      mode === "signin"
        ? await supabase.auth.signInWithPassword({ email, password })
        : await supabase.auth.signUp({ email, password });

    setIsPending(false);

    if (result.error) {
      setError(result.error.message);
      return;
    }

    if (mode === "signup" && !result.data.session) {
      setMessage("Account created. Check your email if confirmation is enabled, then sign in.");
      return;
    }

    router.push("/documents");
    router.refresh();
  }

  return (
    <div className="panel panel--form">
      <div className="panel__header">
        <div>
          <h2>{mode === "signin" ? "Sign in" : "Create account"}</h2>
          <p>Each account gets its own document workspace, retrieval index, and chat history.</p>
        </div>
      </div>
      <form className="ask-form" onSubmit={onSubmit}>
        <label className="ask-form__field">
          <span>Email</span>
          <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="ask-form__field">
          <span>Password</span>
          <input
            required
            minLength={6}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <div className="ask-form__actions">
          <button className="button button--primary" disabled={isPending} type="submit">
            {isPending ? "Working..." : mode === "signin" ? "Sign in" : "Create account"}
          </button>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => {
              setMode(mode === "signin" ? "signup" : "signin");
              setError(null);
              setMessage(null);
            }}
          >
            {mode === "signin" ? "Need an account?" : "Have an account?"}
          </button>
        </div>
        {message ? <div className="callout callout--success">{message}</div> : null}
        {error ? <div className="callout callout--error">{error}</div> : null}
      </form>
    </div>
  );
}
