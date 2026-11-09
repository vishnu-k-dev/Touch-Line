# Touchline AI web app

Next.js 16 + TypeScript + Tailwind dashboard. Client components fetch from the API (`NEXT_PUBLIC_API_URL`, default
http://localhost:8000); the selected match and tab live in the URL hash.

```
npm run dev        # http://localhost:3000 (start the API first)
npm run lint && npm run typecheck && npm test
npm run e2e        # Playwright: needs the API running; only the LLM endpoint is mocked
node scripts/screenshots.mjs   # regenerate the README screenshots
```

See the repository README and docs/architecture.md.
