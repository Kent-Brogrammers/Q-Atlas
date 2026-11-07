# Preserved React scaffold

This is the React scaffold introduced on main, retained for Developer 5's review.
The primary frontend is the SvelteKit application in the parent directory. The
original React entry point, pages, panels, and styles are preserved here.

```sh
npm ci
npm run typecheck
npm run build
npm run dev
```

The dev server uses port **5174** so it can run alongside SvelteKit on 5173. Its
`/api` proxy forwards to port 8000 without changing the backend's CORS policy. Start
the backend separately on 8000 to use the original health/request panels. Its
experiment endpoints currently return structured HTTP 501 responses.

If port 8000 is occupied, start FastAPI on another port and set
`QATLAS_DEV_API_TARGET=http://127.0.0.1:<port>` when starting this dev server.

`src/api/client.ts` and `src/types/index.ts` re-export the parent's canonical client
and OpenAPI-generated types. There is one shared transport and one generated API
schema. After installing the parent frontend and backend, `npm run types:generate`
and `npm run types:check` delegate to the parent code-generation workspace.

The project specification remains unchanged; this directory preserves the team's
React work while the SvelteKit framework choice is reviewed.
