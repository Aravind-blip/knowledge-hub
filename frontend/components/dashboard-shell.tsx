"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

import { classNames } from "@/lib/utils";


const navItems = [
  { href: "/documents", label: "Indexed files" },
  { href: "/documents/upload", label: "Upload documents" },
  { href: "/search", label: "Search answers" },
];


export function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

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
          <p className="sidebar-panel__title">Workspace status</p>
          <p className="sidebar-panel__text">Focused on indexed policies, procedures, and support references.</p>
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
          <p className="sidebar-footer__text">PDF and text-based sources in this MVP. Responses stay tied to cited material.</p>
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
