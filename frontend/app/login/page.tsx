import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { getServerAuth } from "@/lib/supabase/server";

export default async function LoginPage() {
  const { user, authConfigured } = await getServerAuth();
  if (!authConfigured || user) {
    redirect("/documents");
  }

  return (
    <section className="auth-shell">
      <div className="auth-shell__background" aria-hidden="true">
        <div className="auth-shell__orb auth-shell__orb--primary" />
        <div className="auth-shell__orb auth-shell__orb--secondary" />
        <div className="auth-shell__grid" />
      </div>

      <div className="auth-shell__content">
        <div className="auth-shell__story">
          <p className="auth-shell__eyebrow">Knowledge Hub</p>
          <h2 className="auth-shell__title">Work within your organization&apos;s knowledge workspace.</h2>
          {/* <p className="auth-shell__description">
            Access documents securely, keep retrieval grounded in your organization boundary, and preserve audit-ready
            history for every answer.
          </p>

          <div className="auth-shell__feature-list">
            <div className="auth-shell__feature">
              <strong>Organization-scoped access</strong>
              <span>Files, search, chat history, and citations stay inside the workspace you join or create.</span>
            </div>
            <div className="auth-shell__feature">
              <strong>Any valid email address</strong>
              <span>Gmail, Outlook, edu, and custom domains are supported without business-only restrictions.</span>
            </div>
            <div className="auth-shell__feature">
              <strong>Grounded document retrieval</strong>
              <span>Answers cite sources from your organization instead of searching across a shared global pool.</span>
            </div>
          </div> */}
        </div>

        <AuthForm initialMode="signin" />
      </div>
    </section>
  );
}
