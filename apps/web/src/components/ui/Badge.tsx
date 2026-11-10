import type { ReactNode } from "react";

const TONES = {
  neutral: "border-line bg-surface2 text-muted",
  ok: "border-ok/40 bg-ok/10 text-ok",
  review: "border-warn/50 bg-warn/10 text-warn",
  card: "border-card bg-card text-cardfg",
  hot: "border-red/40 bg-red/10 text-red",
};

export function Badge({ tone = "neutral", children, className = "" }: { tone?: keyof typeof TONES; children: ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 border px-1.5 py-0.5 font-display text-[13px] font-semibold uppercase leading-none tracking-wider ${TONES[tone]} ${className}`}>
      {children}
    </span>
  );
}

/** A section heading: small kicker, big condensed title, and a chalk rule that draws in. */
export function SectionTitle({ kicker, title, id, children }: { kicker: string; title: string; id?: string; children?: ReactNode }) {
  return (
    <header className="mb-6">
      <p className="font-display text-sm font-semibold uppercase tracking-[0.2em] text-turf">{kicker}</p>
      <h2 id={id} className="mt-1 font-display text-4xl font-bold uppercase leading-none tracking-tight sm:text-5xl">{title}</h2>
      <span aria-hidden className="grow-x mt-3 block h-1 w-20 bg-card" />
      {children && <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-muted">{children}</p>}
    </header>
  );
}
