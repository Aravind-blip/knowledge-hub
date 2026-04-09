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
  authEnabled,
}: {
  children: ReactNode;
  userEmail: string | null;
  authEnabled: boolean;
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
          <p className="sidebar-panel__title">{authEnabled ? "Workspace owner" : "Workspace mode"}</p>
          <p className="sidebar-panel__text">{authEnabled ? userEmail ?? "Signed-in user" : "Local demo user"}</p>
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
          <p className="sidebar-footer__label">Coverage</p>
          <p className="sidebar-footer__text">PDF and text-based sources stay isolated to your account and cited material.</p>
          {authEnabled ? (
            <button className="button button--secondary" onClick={signOut} type="button">
              Sign out
            </button>
          ) : null}
        </div>
      </aside>
      <main className="app-shell__content">
        <div className="content-chrome">
          <div className="content-chrome__title-group">
            <p className="content-chrome__eyebrow">Knowledge Operations</p>
            <p className="content-chrome__title">Reference search and source review</p>
          </div>
          <div className="content-chrome__badge">MVP</div>
        </div>
        {children}
      </main>
    </div>
  );
}
