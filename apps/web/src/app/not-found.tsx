import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-24 text-center">
      <p className="font-display text-sm font-semibold uppercase tracking-[0.25em] text-turf">404</p>
      <h1 className="mt-2 font-display text-7xl font-extrabold uppercase leading-none">Offside!</h1>
      <p className="mx-auto mt-4 max-w-md text-muted">That page isn&apos;t in play. The linesman has raised the flag, and the free kick goes back to the Match Centre.</p>
      <Link
        href="/"
        className="mt-8 inline-block border-2 border-rule bg-card px-6 py-3 font-display text-xl font-bold uppercase tracking-wide text-cardfg shadow-[4px_4px_0_var(--rule)] transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-[6px_6px_0_var(--rule)]"
      >
        Back to the Match Centre
      </Link>
    </main>
  );
}
