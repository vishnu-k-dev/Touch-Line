import Link from "next/link";
import { BallMark } from "./BallMark";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t-2 border-rule bg-surface">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-[1fr_auto]">
        <div>
          <p className="flex items-center gap-3 font-display text-4xl font-bold uppercase leading-none tracking-tight">
            <BallMark size={34} /> Full time.
          </p>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-muted">
            Match data:{" "}
            <a className="underline decoration-card decoration-2 underline-offset-2 hover:text-fg" href="https://github.com/statsbomb/open-data" target="_blank" rel="noreferrer">
              StatsBomb Open Data
            </a>
            , FIFA World Cup 2022 sample. Built on event data only: no player tracking, no video-derived formations. The 360 shooting-lane count is a lower bound. Every
            AI claim cites its tool call and match events; what can&apos;t be checked is flagged, not hidden.
          </p>
        </div>
        <nav aria-label="Footer" className="flex gap-6 font-display text-lg font-semibold uppercase tracking-wide md:flex-col md:gap-2 md:text-right">
          <Link href="/" className="hover:text-turf">
            Match Centre
          </Link>
          <Link href="/about" className="hover:text-turf">
            How it works
          </Link>
          <a href="https://github.com/vishnu-k-dev/touchline-ai" target="_blank" rel="noreferrer" className="hover:text-turf">
            Source code
          </a>
        </nav>
      </div>
    </footer>
  );
}
