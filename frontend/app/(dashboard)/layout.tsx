import { ReactNode } from "react";
import { redirect } from "next/navigation";

import { DashboardShell } from "@/components/dashboard-shell";
import { getServerAuth } from "@/lib/supabase/server";


export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const { user, authConfigured } = await getServerAuth();
  if (authConfigured && !user) {
    redirect("/login");
  }

  return <DashboardShell authEnabled={authConfigured} userEmail={user?.email ?? null}>{children}</DashboardShell>;
}
