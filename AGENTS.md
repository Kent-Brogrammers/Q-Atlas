# Q-Atlas working agreement

- Read `docs/Project_Spec.md` completely before changing code. It is the source of truth; preserve it.
- This repository currently provides scaffolding. Implement features only when assigned.
- Respect ownership: Developer 1 materials; Developer 2 compiler; Developer 3 optimization, shared QAOA, and benchmarks; Developer 4 search; Developer 5 frontend and integration.
- Make small, reviewable changes within the assigned module. Avoid unrelated changes.
- Propose shared schema, API, bit order, objective sense, or timing changes to impacted owners before changing them.
- Reuse `backend/app/schemas/`; regenerate frontend types with `npm run types:generate` after contract changes.
- Developer 3 owns `app.quantum.qaoa.run_qaoa`; the compiler consumes it. Never duplicate QAOA engines.
- Write tests for implemented behavior. Run pytest, Ruff, frontend type checks, and the build for affected areas.
- Never claim quantum advantage without recorded evidence and fair classical comparisons. Label simulator results and cached measurements accurately.
- Never execute untrusted user-submitted Python: no eval, exec, or dynamic imports. Compiler code must parse and validate an allowlisted AST.
- Never inspect or expose secret values, and never commit API keys, credentials, or local environment files.
- Ask before hardware jobs using external quotas or credentials. Local simulation is the default.
