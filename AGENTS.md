# LLM Wiki Agent Rules

This project is a demo of an LLM-maintained knowledge base.

## Core Layers

- `raw/` contains immutable source materials. Do not rewrite raw sources during ingest.
- `wiki/` contains compiled knowledge pages maintained by agents.
- `wiki/index.md` is the navigation layer. Keep it concise.
- `wiki/log.md` is the chronological operation log. Append every ingest, query archive, and lint run.
- `templates/` contains page patterns used by the demo.

## Demo Agents

### Programming Agent

Focus on technical architecture, implementation patterns, API integration, debugging notes, and reusable engineering decisions.

Write pages under `wiki/programming/`.

### UI Design Agent

Focus on product experience, screen structure, interaction patterns, layout constraints, affordances, and design tradeoffs.

Write pages under `wiki/ui-design/`.

### Project Manager Agent

Focus on goals, scope, roadmap, risks, decisions, milestones, dependencies, and execution planning.

Write pages under `wiki/project-management/`.

### Personal Knowledge Agent

Focus on learning loops, personal operating systems, notes, reflective practice, habits, and long-term knowledge accumulation.

Write pages under `wiki/personal/`.

## Operations

### Ingest

1. Read one source from `raw/`.
2. Compile it into one or more topic pages under `wiki/`.
3. Update `wiki/index.md`.
4. Append to `wiki/log.md`.

### Query

1. Read `wiki/index.md`.
2. Read relevant pages.
3. Answer from wiki content first.
4. Only write a new page when the user chooses to archive the answer.

### Lint

Check for missing index entries, empty pages, broken local links, and orphan topics. Report issues before making large structural changes.
