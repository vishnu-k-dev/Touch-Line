import Link from "next/link";
import type { ReactNode } from "react";
import { Reveal } from "@/components/ui/Reveal";
import { SectionTitle } from "@/components/ui/Badge";

const stroke = { fill: "none", stroke: "currentColor", strokeWidth: 2.2, strokeLinecap: "square", strokeLinejoin: "miter" } as const;

const CARDS: { n: string; title: string; line: string; text: string; href: string; icon: ReactNode }[] = [
  {
    n: "01",
    title: "The numbers",
    line: "Counted, not guessed.",
    text: "xG, PPDA, minutes and heatmaps are recounted from the raw StatsBomb files in tests. Every team always adds up to eleven players on the pitch.",
    href: "/about#numbers",
    icon: (
      <svg viewBox="0 0 48 48" className="h-11 w-11" {...stroke}>
        <rect x="5" y="9" width="38" height="30" />
        <line x1="24" y1="9" x2="24" y2="39" />
        <circle cx="24" cy="24" r="6" />
        <rect x="5" y="17" width="7" height="14" />
        <rect x="36" y="17" width="7" height="14" />
      </svg>
    ),
  },
  {
    n: "02",
    title: "The moments",
    line: "Search by meaning.",
    text: "Ask for a header from a corner, or why the better team lost. A local embedding model searches the match, and exact filters catch what meaning can't.",
    href: "/about#moments",
    icon: (
      <svg viewBox="0 0 48 48" className="h-11 w-11" {...stroke}>
        <circle cx="20" cy="20" r="12" />
        <line x1="29" y1="29" x2="43" y2="43" strokeWidth="4" />
        <polyline points="14,20 19,25 27,15" />
      </svg>
    ),
  },
  {
    n: "03",
    title: "The VAR check",
    line: "Every claim, reviewed.",
    text: "Each finding cites its tool call and match events. A validator checks every number against what the tools returned. No match, no goal.",
    href: "/about#var",
    icon: (
      <svg viewBox="0 0 48 48" className="h-11 w-11" {...stroke}>
        <rect x="4" y="8" width="40" height="27" />
        <line x1="16" y1="42" x2="32" y2="42" />
        <line x1="24" y1="35" x2="24" y2="42" />
        <polyline points="14,22 21,29 34,15" strokeWidth="3.5" />
      </svg>
    ),
  },
];

export function TrustTrio() {
  return (
    <section aria-labelledby="trust" className="mx-auto max-w-7xl px-4 pt-14">
      <Reveal>
        <SectionTitle id="trust" kicker="The back three" title="Why you can trust the answer">
          Three lines of defence between a question and a claim.
        </SectionTitle>
      </Reveal>
      <div className="grid gap-5 md:grid-cols-3">
        {CARDS.map((c, i) => (
          <Reveal key={c.n} delay={i * 110}>
            <Link href={c.href} className="lift group relative flex h-full flex-col border-2 border-rule bg-surface p-5">
              <span aria-hidden className="absolute inset-x-0 top-0 h-1.5 origin-left scale-x-0 bg-card transition-transform duration-300 group-hover:scale-x-100" />
              <div className="flex items-start justify-between text-turf">
                <span className="transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-110">{c.icon}</span>
                <span className="font-display text-5xl font-extrabold leading-none text-line">{c.n}</span>
              </div>
              <h3 className="mt-4 font-display text-3xl font-bold uppercase leading-none tracking-tight">{c.title}</h3>
              <p className="mt-1 font-display text-lg font-semibold uppercase tracking-wide text-turf">{c.line}</p>
              <p className="mt-3 flex-1 text-[15px] leading-relaxed text-muted">{c.text}</p>
              <span className="mt-4 inline-flex items-center gap-1 font-display text-lg font-semibold uppercase tracking-wide">
                See the proof
                <span aria-hidden className="transition-transform duration-200 group-hover:translate-x-1.5">
                  →
                </span>
              </span>
            </Link>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
