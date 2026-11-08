"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  ArrowUpRight,
  Box,
  Braces,
  ChevronDown,
  CircleHelp,
  Command,
  GitBranch,
  LayoutDashboard,
  Terminal,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
const links = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/features", label: "Feature explorer", icon: GitBranch },
  { href: "/playground", label: "Query playground", icon: Terminal },
  { href: "/traces", label: "Trace explorer", icon: Activity },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api<{ status: string; as_of: string }>("/health"),
    refetchInterval: 30000,
  });
  return (
    <div className="shell">
      <aside className="sidebar">
        <Link href="/" className="brand">
          <span className="brand-mark">
            <Braces size={20} />
          </span>{" "}
          minichalk <span className="version">/ 0.1</span>
        </Link>
        <div className="workspace">
          <span className="workspace-icon">
            <Box size={15} />
          </span>
          <div>
            Fraud detection<small>Local workspace</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              href={href}
              key={href}
              className={path === href ? "nav-link active" : "nav-link"}
            >
              <Icon size={16} />
              {label}
              {path === href && <span className="nav-dot" />}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <GitBranch size={16} />
          <div>
            From definition to decision.
            <p>Explore the graph behind every computed feature.</p>
          </div>
        </div>
        <div className="sidebar-bottom">
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">
            <CircleHelp size={15} /> API documentation{" "}
            <ArrowUpRight size={13} />
          </a>
          <div>
            <span className={`dot ${health.isSuccess ? "green" : "amber"}`} />
            {health.isSuccess
              ? "Engine connected"
              : health.isError
                ? "Engine unavailable"
                : "Connecting…"}
            <span className="local-tag">LOCAL</span>
          </div>
        </div>
      </aside>
      <div className="main-wrap">
        <header className="topbar">
          <div>
            <span className="muted">Workspace</span>
            <span className="slash">/</span>Fraud detection
            <span className="environment">Development</span>
          </div>
          <span className="top-hint">
            <Command size={12} /> Python definitions · async execution
          </span>
        </header>
        <main id="main-content">{children}</main>
        <footer>
          <span>MiniChalk · Independent educational prototype</span>
          <span>
            Single process <span className="footer-dot">·</span> SQLite
          </span>
        </footer>
      </div>
    </div>
  );
}
