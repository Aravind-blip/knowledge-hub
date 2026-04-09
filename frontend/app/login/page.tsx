import { redirect } from "next/navigation";

import { AuthForm } from "@/components/auth-form";
import { getServerAuth } from "@/lib/supabase/server";

export default async function LoginPage() {
  const { user, authConfigured } = await getServerAuth();
  if (!authConfigured || user) {
    redirect("/documents");
  }

  return (
    <section className="page">
      <div className="content-chrome">
        <div className="content-chrome__title-group">
          <p className="content-chrome__eyebrow">Knowledge Hub</p>
          <p className="content-chrome__title">Secure document workspace</p>
        </div>
      </div>
      <AuthForm />
    </section>
  );
}
