"use client";

import { FormEvent, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

type Mode = "signin" | "signup";

type AuthFormProps = {
  initialMode?: Mode;
};

function formatAuthError(message: string) {
  const normalized = message.toLowerCase();

  if (normalized.includes("invalid login credentials")) {
    return "Email or password is incorrect. Check your credentials and try again.";
  }
  if (normalized.includes("email rate limit exceeded") || normalized.includes("over_email_send_rate_limit")) {
    return "Too many email requests were sent recently. Wait a moment, then try again.";
  }
  if (normalized.includes("user already registered")) {
    return "An account already exists for this email. Sign in instead, or reset your password if needed.";
  }
  if (normalized.includes("password should be at least")) {
    return "Choose a stronger password that meets the minimum length requirement.";
  }
  if (normalized.includes("unable to validate email address") || normalized.includes("email address invalid")) {
    return "Enter a valid email address.";
  }
  if (normalized.includes("signup is disabled")) {
    return "New account creation is currently disabled for this environment.";
  }
  if (normalized.includes("email not confirmed")) {
    return "Check your inbox and confirm your email address before signing in.";
  }

  return message;
}

export function AuthForm({ initialMode = "signin" }: AuthFormProps) {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  const submitLabel = useMemo(() => {
    if (isPending) {
      return mode === "signin" ? "Signing in..." : "Creating workspace...";
    }
    return mode === "signin" ? "Sign in" : "Create workspace";
  }, [isPending, mode]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsPending(true);
    setError(null);
    setMessage(null);

    const supabase = createSupabaseBrowserClient();
    const trimmedEmail = email.trim();
    const trimmedPassword = password.trim();
    const trimmedFullName = fullName.trim();
    const trimmedOrganizationName = organizationName.trim();

    if (mode === "signup") {
      if (!trimmedFullName) {
        setError("Enter your full name.");
        setIsPending(false);
        return;
      }
      if (!trimmedOrganizationName) {
        setError("Enter your organization name.");
        setIsPending(false);
        return;
      }
    }

    const result =
      mode === "signin"
        ? await supabase.auth.signInWithPassword({
            email: trimmedEmail,
            password: trimmedPassword,
          })
        : await supabase.auth.signUp({
            email: trimmedEmail,
            password: trimmedPassword,
            options: {
              emailRedirectTo:
                typeof window !== "undefined" ? `${window.location.origin}/login` : undefined,
              data: {
                full_name: trimmedFullName,
                organization_name: trimmedOrganizationName,
              },
            },
          });

    setIsPending(false);

    if (result.error) {
      setError(formatAuthError(result.error.message));
      return;
    }

    if (mode === "signup" && !result.data.session) {
      setMessage(
        "Your workspace account was created. If email confirmation is enabled, confirm your email first, then sign in.",
      );
      setMode("signin");
      setPassword("");
      return;
    }

    router.push("/documents");
    router.refresh();
  }

  return (
    <div className="auth-card">
      <div className="auth-card__topline">
        <span className="auth-card__eyebrow">Secure workspace access</span>
        <div className="auth-card__mode-toggle" role="tablist" aria-label="Authentication mode">
          <button
            className={`auth-card__mode-pill ${mode === "signin" ? "auth-card__mode-pill--active" : ""}`}
            type="button"
            onClick={() => {
              setMode("signin");
              setMessage(null);
              setError(null);
            }}
          >
            Sign in
          </button>
          <button
            className={`auth-card__mode-pill ${mode === "signup" ? "auth-card__mode-pill--active" : ""}`}
            type="button"
            onClick={() => {
              setMode("signup");
              setMessage(null);
              setError(null);
            }}
          >
            Create workspace
          </button>
        </div>
      </div>

      <div className="auth-card__header">
        <div>
          <h1>{mode === "signin" ? "Access your organization workspace" : "Create your workspace"}</h1>
          <p>
            {mode === "signin"
              ? "Review documents, retrieval, and chat history inside your organization boundary."
              : "Use any valid email address. Your organization name controls workspace ownership and isolation."}
          </p>
        </div>
      </div>

      <form className="auth-form" onSubmit={onSubmit}>
        {mode === "signup" ? (
          <>
            <label className="auth-form__field">
              <span>Full name</span>
              <input
                required
                autoComplete="name"
                placeholder="Ava Johnson"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </label>
            <label className="auth-form__field">
              <span>Organization name</span>
              <input
                required
                autoComplete="organization"
                placeholder="Acme Operations"
                value={organizationName}
                onChange={(event) => setOrganizationName(event.target.value)}
              />
            </label>
          </>
        ) : null}

        <label className="auth-form__field">
          <span>Email</span>
          <input
            required
            autoComplete="email"
            type="email"
            placeholder="name@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>

        <label className="auth-form__field">
          <span>Password</span>
          <input
            required
            autoComplete={mode === "signin" ? "current-password" : "new-password"}
            minLength={8}
            type="password"
            placeholder={mode === "signin" ? "Enter your password" : "At least 8 characters"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>

        <div className="auth-form__footer">
          <button className="button button--primary auth-form__submit" disabled={isPending} type="submit">
            {submitLabel}
          </button>
          <p className="auth-form__hint">
            {mode === "signin"
              ? "Need a workspace? Switch to create workspace."
              : "Already have access? Switch to sign in."}
          </p>
        </div>

        {message ? <div className="callout callout--success">{message}</div> : null}
        {error ? <div className="callout callout--error">{error}</div> : null}
      </form>
    </div>
  );
}
