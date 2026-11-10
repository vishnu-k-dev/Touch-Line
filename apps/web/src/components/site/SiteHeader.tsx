"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApi } from "@/lib/api";
import type { AnalystStatus } from "@/lib/types";
import { BallMark } from "./BallMark";

const LINKS = [
  { href: "/", label: "Match Centre" },
  { href: "/about", label: "How it works" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const status = useApi<AnalystStatus>("/api/v1/analyst/status");
  const open = status.data?.configured;
  return (
    <header className="sticky top-0 z-40 border-b-2 border-rule bg-bg/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-2.5 sm:gap-8">
        <Link href="/" className="group flex items-center gap-2" aria-label="Touchline AI home">
          <span className="transition-transform duration-500 ease-out group-hover:rotate-[144deg]">
            <BallMark />
          </span>
          <span className="font-display text-[26px] font-bold uppercase leading-none tracking-tight">
            Touchline<span className="ml-1 bg-card px-1.5 text-cardfg">AI</span>
          </span>
        </Link>
        <nav aria-label="Primary" className="flex gap-1">
          {LINKS.map((l) => {
            const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                aria-current={active ? "page" : undefined}
                className={`group relative px-3 py-2 font-display text-lg font-semibold uppercase leading-none tracking-wide transition-colors ${active ? "text-fg" : "text-muted hover:text-fg"}`}
              >
                {l.label}
                <span className={`absolute inset-x-3 -bottom-[11px] h-1 origin-left bg-card transition-transform duration-200 ${active ? "scale-x-100" : "scale-x-0 group-hover:scale-x-100"}`} />
              </Link>
            );
          })}
        </nav>
        <p
          className="ml-auto hidden items-center gap-2 font-display text-sm font-semibold uppercase tracking-wider text-muted sm:flex"
          title={open ? `The analyst is online (${status.data?.model})` : "The analyst needs an LLM key on the server. Everything else works."}
        >
          <span className={`h-2.5 w-2.5 rounded-full ${open ? "bg-ok" : "bg-muted/60"}`} />
          VAR room {status.loading ? "…" : open ? "open" : "closed"}
        </p>
      </div>
    </header>
  );
}
