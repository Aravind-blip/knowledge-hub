"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import { classNames } from "@/lib/utils";


const navItems = [
  { href: "/documents", label: "Indexed files" },
  { href: "/documents/upload", label: "Upload documents" },
  { href: "/search", label: "Search answers" },
  { href: "/history", label: "Chat history" },
];


export function DashboardShell({
  children,
  userEmail,
  userName,
  authEnabled,
  organizationName,
  role,
}: {
  children: ReactNode;
  userEmail: string | null;
  userName: string | null;
  authEnabled: boolean;
  organizationName: string | null;
  role: string | null;
}) {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    const supabase = createSupabaseBrowserClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="app-shell">
      <aside className="app-shell__sidebar">
        <div className="brand">
          <div className="brand__mark">KH</div>
          <div>
            <p className="brand__name">Knowledge Hub</p>
            <p className="brand__meta">Internal document research workspace</p>
          </div>
        </div>
        <div className="sidebar-panel">
          <p className="sidebar-panel__title">{authEnabled ? "Organization" : "Workspace mode"}</p>
          <p className="sidebar-panel__text" data-testid="workspace-organization">
            {authEnabled ? organizationName ?? "Provisioning workspace" : "Development workspace"}
          </p>
          {authEnabled ? (
            <p className="sidebar-panel__text" data-testid="workspace-user">
              {userName ?? userEmail ?? "Signed-in user"} · {role ?? "member"}
            </p>
          ) : null}
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <Link
              className={classNames(
                "nav__link",
                pathname === item.href || pathname.startsWith(`${item.href}/`) ? "nav__link--active" : "",
              )}
              href={item.href}
              key={item.href}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <p className="sidebar-footer__label">Controls</p>
          <p className="sidebar-footer__text">
            Files, search, and cited excerpts stay isolated to your organization boundary.
          </p>
          {authEnabled ? (
            <button className="button button--secondary" data-testid="sign-out-button" onClick={signOut} type="button">
              Sign out
            </button>
          ) : null}
        </div>
      </aside>
      <main className="app-shell__content">
        <div className="content-chrome">
          <div className="content-chrome__title-group">
            <p className="content-chrome__eyebrow">Knowledge Operations</p>
            <p className="content-chrome__title">{organizationName ?? "Organization workspace"}</p>
            <p className="content-chrome__meta">{userName ?? userEmail ?? "Signed-in user"}</p>
          </div>
          <div className="content-chrome__badge">{authEnabled ? "Organization scoped" : "Local mode"}</div>
        </div>
        {children}
      </main>
    </div>
  );
}
