import type { Metadata } from "next";
import Link from "next/link";
import { Facts, RetrievalTable } from "@/components/about/Facts";
import { Formation } from "@/components/about/Formation";
import { Pipeline } from "@/components/about/Pipeline";
import { VarDemo } from "@/components/about/VarDemo";
import { SectionTitle } from "@/components/ui/Badge";
import { Reveal } from "@/components/ui/Reveal";

export const metadata: Metadata = {
  title: "How it works",
  description: "The stack, the pipeline, the VAR check on every AI claim, and the numbers measured along the way, including where Touchline AI falls short.",
};

const LIMITS = [
  { t: "Event data only.", d: "No player tracking and no video-derived formations. Ask for a formation or a sprint speed and the analyst has to say it can't tell you." },
  { t: "Small sample.", d: "Five World Cup 2022 matches. One game is also a noisy sample, and the analyst is told to say so." },
  { t: "The 360 lane count is a lower bound.", d: "11 of 25 blocked shots show no visible defender in the lane, so a zero never proves a clear lane." },
  { t: "xG is not the whole story.", d: "It ignores game state: a team that scored early may simply have sat back." },
  { t: "Search is exact, not tuned.", d: "A plain vector scan over 156 documents. That is right at this size and would need an index at ten thousand." },
  { t: "One model at a time.", d: "The loop is provider-neutral (OpenAI by default, Anthropic wired in), but it has been tuned for neither. Swap models and compare with the eval." },
];

export default function About() {
  return (
    <main>
      <section className="night-pitch border-b-2 border-rule">
        <div className="mx-auto max-w-7xl px-4 py-14 lg:py-20">
          <p className="anim-slide-up font-display text-sm font-semibold uppercase tracking-[0.25em] text-card">How it works</p>
          <h1 className="anim-slide-up mt-3 font-display text-6xl font-extrabold uppercase leading-[0.92] tracking-tight sm:text-8xl" style={{ animationDelay: "80ms" }}>
            Under the hood
          </h1>
          <p className="anim-slide-up mt-5 max-w-2xl text-lg leading-relaxed text-[#f1eedf]/85" style={{ animationDelay: "180ms" }}>
            A football question goes in. A checked answer comes out. This page shows the machinery: the stack as a starting eleven, the path one question takes, a VAR check you can try
            to fool, and the numbers I measured, including where it comes up short.
          </p>
          <nav aria-label="On this page" className="anim-fade mt-8 flex flex-wrap gap-2" style={{ animationDelay: "300ms" }}>
            {[
              ["stack", "The Starting XI"],
              ["pipeline", "The move"],
              ["var", "The VAR check"],
              ["moments", "Search"],
              ["numbers", "The numbers"],
              ["limits", "Offside lines"],
            ].map(([id, label]) => (
              <a key={id} href={`#${id}`} className="border-2 border-[#f1eedf]/60 px-3 py-1.5 font-display text-base font-semibold uppercase tracking-wide transition-colors hover:border-card hover:bg-card hover:text-cardfg">
                {label}
              </a>
            ))}
          </nav>
        </div>
      </section>

      <div className="mx-auto max-w-7xl space-y-20 px-4 pt-14">
        <section id="stack" className="scroll-mt-20">
          <Reveal>
            <SectionTitle kicker="The stack" title="The Starting XI">
              Eleven pieces, drawn as a 4-3-3. Hover, focus or tap a player to see what it does and where it lives in the code.
            </SectionTitle>
          </Reveal>
          <Reveal delay={80}>
            <Formation />
          </Reveal>
        </section>

        <section id="pipeline" className="scroll-mt-20">
          <Reveal>
            <SectionTitle kicker="The build-up" title="One question, five touches">
              Every answer follows the same move, and each step can be tested on its own.
            </SectionTitle>
          </Reveal>
          <Pipeline />
        </section>

        <section id="var" className="scroll-mt-20">
          <Reveal>
            <SectionTitle kicker="The big idea" title="The VAR check">
              A language model will happily state a number it made up. So the analyst can&apos;t just say things: each finding must cite the tool call that produced its numbers, and a
              validator checks them. The same rule runs here, in your browser, on a real slice of a tool result.
            </SectionTitle>
          </Reveal>
          <Reveal delay={80}>
            <VarDemo />
          </Reveal>
        </section>

        <section id="moments" className="scroll-mt-20">
          <Reveal>
            <SectionTitle kicker="The moments" title="Search by meaning, filter by fact">
              156 documents (tactical concepts, match summaries, and one entry per shot) are embedded with a small local model and searched in Postgres with pgvector. Meaning-based
              search is great at “why does the better team lose?” and bad at exact attributes, which the table shows honestly. Exact filters (corner, header, penalty, player) cover that.
            </SectionTitle>
          </Reveal>
          <Reveal delay={80}>
            <RetrievalTable />
          </Reveal>
        </section>

        <section id="numbers" className="scroll-mt-20">
          <Reveal>
            <SectionTitle kicker="The numbers" title="What I measured">
              Every figure here came from running the code. Where a check failed on the first try, that is in the notes too.
            </SectionTitle>
          </Reveal>
          <Facts />
        </section>

        <section id="limits" className="scroll-mt-20">
          <Reveal>
            <SectionTitle kicker="The limits" title="Offside lines">
              Where Touchline AI stops, so nobody has to find out the hard way.
            </SectionTitle>
          </Reveal>
          <ul className="grid gap-3 md:grid-cols-2">
            {LIMITS.map((l, i) => (
              <li key={l.t}>
                <Reveal delay={(i % 2) * 80}>
                  <div className="lift h-full border-2 border-line border-l-[6px] border-l-card bg-surface p-4 hover:border-rule hover:border-l-card">
                    <p className="font-display text-xl font-bold uppercase leading-tight tracking-wide">{l.t}</p>
                    <p className="mt-1 text-sm leading-relaxed text-muted">{l.d}</p>
                  </div>
                </Reveal>
              </li>
            ))}
          </ul>
        </section>

        <section id="data" className="scroll-mt-20 border-t-2 border-rule pt-8">
          <p className="max-w-3xl text-sm leading-relaxed text-muted">
            Match data comes from{" "}
            <a className="underline decoration-card decoration-2 underline-offset-2 hover:text-fg" href="https://github.com/statsbomb/open-data" target="_blank" rel="noreferrer">
              StatsBomb Open Data
            </a>
            , used under their terms with attribution. The embedding model is BAAI/bge-small-en-v1.5 (MIT). Built by Vishnu K. Source on{" "}
            <a className="underline decoration-card decoration-2 underline-offset-2 hover:text-fg" href="https://github.com/vishnu-k-dev/Touch-Line" target="_blank" rel="noreferrer">
              GitHub
            </a>
            .
          </p>
          <Link
            href="/#match-centre"
            className="mt-6 inline-block border-2 border-rule bg-card px-6 py-3 font-display text-xl font-bold uppercase tracking-wide text-cardfg shadow-[4px_4px_0_var(--rule)] transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-[6px_6px_0_var(--rule)]"
          >
            Kick off in the Match Centre
          </Link>
        </section>
      </div>
    </main>
  );
}
