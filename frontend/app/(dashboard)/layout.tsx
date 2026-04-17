import { ReactNode } from "react";
import { redirect } from "next/navigation";

import { DashboardShell } from "@/components/dashboard-shell";
import { getWorkspaceSummary } from "@/lib/server-api";
import { getServerAuth } from "@/lib/supabase/server";


export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const { user, authConfigured } = await getServerAuth();
  if (authConfigured && !user) {
    redirect("/login");
  }

  const workspace = authConfigured ? await getWorkspaceSummary() : null;

  return (
    <DashboardShell
      authEnabled={authConfigured}
      userEmail={user?.email ?? null}
      organizationName={workspace?.organization_name ?? null}
      role={workspace?.role ?? null}
    >
      {children}
    </DashboardShell>
  );
}
