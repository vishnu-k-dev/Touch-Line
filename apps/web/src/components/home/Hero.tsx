import Link from "next/link";
import { FACTS } from "@/content/facts";
import { CountUp } from "@/components/ui/CountUp";
import { BallMark } from "@/components/site/BallMark";
import { HeroBoard } from "./HeroBoard";

const STATS = [
  { label: "World Cup matches", value: FACTS.matches },
  { label: "Match events logged", value: FACTS.events },
  { label: "Searchable moments and concepts", value: FACTS.documents },
  { label: "Analyst tools", value: FACTS.tools },
];

export function Hero() {
  return (
    <section className="night-pitch relative overflow-hidden border-b-2 border-rule">
      <div className="mx-auto grid max-w-7xl items-center gap-10 px-4 pb-12 pt-12 lg:grid-cols-[1.02fr_1fr] lg:pb-16 lg:pt-16">
        <div>
          <p className="anim-slide-up font-display text-sm font-semibold uppercase tracking-[0.25em] text-card">FIFA World Cup 2022 · event data · 360 freeze-frames</p>
          <h1 className="mt-3 font-display text-[56px] font-extrabold uppercase leading-[0.92] tracking-tight sm:text-7xl lg:text-[88px]">
            <span className="anim-slide-up block" style={{ animationDelay: "90ms" }}>
              Read the game.
            </span>
            <span className="anim-slide-up block" style={{ animationDelay: "190ms" }}>
              Show your{" "}
              <span className="relative inline-block px-2 text-cardfg">
                <span aria-hidden className="grow-x absolute inset-0 -skew-x-6 bg-card" style={{ animationDelay: "500ms" }} />
                <span className="relative">workings.</span>
              </span>
            </span>
          </h1>
          <p className="anim-slide-up mt-6 max-w-xl text-lg leading-relaxed text-[#f1eedf]/85" style={{ animationDelay: "320ms" }}>
            Touchline AI is a football analyst that has to prove every claim. Ask a question and it chooses its own tools, quotes the numbers, and points at the exact match
            events behind them. If a number doesn&apos;t check out, VAR flags it.
          </p>
          <div className="anim-slide-up mt-8 flex flex-wrap items-center gap-4" style={{ animationDelay: "430ms" }}>
            <Link
              href="/#match-centre"
              className="group inline-flex items-center gap-3 border-2 border-[#f1eedf] bg-card px-6 py-3 font-display text-xl font-bold uppercase tracking-wide text-cardfg shadow-[4px_4px_0_#f1eedf] transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-[6px_6px_0_#f1eedf] active:translate-x-0.5 active:translate-y-0.5 active:shadow-none"
            >
              Open the Match Centre
              <span aria-hidden className="inline-block transition-transform duration-500 group-hover:translate-x-1.5 group-hover:rotate-[360deg]">
                <BallMark size={24} />
              </span>
            </Link>
            <Link
              href="/about"
              className="group inline-flex items-center gap-2 border-2 border-[#f1eedf]/70 px-6 py-3 font-display text-xl font-bold uppercase tracking-wide transition-colors hover:border-card hover:text-card"
            >
              How it works
              <span aria-hidden className="transition-transform duration-200 group-hover:translate-x-1">
                →
              </span>
            </Link>
          </div>
          <p className="anim-fade mt-6 font-display text-base uppercase tracking-[0.18em] text-[#f1eedf]/55" style={{ animationDelay: "700ms" }}>
            xG, but make it honest.
          </p>
        </div>
        <div className="anim-fade" style={{ animationDelay: "250ms" }}>
          <HeroBoard />
        </div>
      </div>
      <dl className="mx-auto grid max-w-7xl grid-cols-2 gap-px border-t border-white/20 bg-white/15 sm:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className="bg-[#0b3022] px-4 py-4">
            <dd className="font-display text-4xl font-bold leading-none sm:text-5xl">
              <CountUp to={s.value} />
            </dd>
            <dt className="mt-1 font-display text-xs uppercase tracking-[0.18em] text-white/60">{s.label}</dt>
          </div>
        ))}
      </dl>
    </section>
  );
}
