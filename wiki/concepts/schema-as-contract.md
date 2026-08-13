---
title: "Schema as Contract"
type: concept
updated: "2026-08-13"
sources: "LLM Wiki; LLM App Development Patterns"
---

# Schema as Contract

## Summary

The schema layer — `AGENTS.md` for Codex, `CLAUDE.md` for Claude Code, `SKILL.md` in an Agent Skills setup — is what turns a general-purpose LLM into a disciplined wiki maintainer. It encodes the structure, conventions, and workflows, and the human and the LLM co-evolve it over time.

## Cross-Page Insights

- From `LLM Wiki` (raw): the schema is "the key configuration file" — the difference between a chatbot and a maintainer is written rules, not a better model.
- From `LLM App Development Patterns`: the instruction layer is portable across platforms (`AGENTS.md` / `CLAUDE.md` / `SKILL.md`), while the knowledge layer stays plain markdown either way.
- From the Programming lens: treat `AGENTS.md` as the behavioral contract for future automation — build against the rules, not against the model.
- From the UI Design lens: exposing a small number of stable operations is the schema made visible to the user.
- This demo's own `AGENTS.md` defines four agent roles and three operations — the multi-perspective remix is itself just a schema choice.

## Source Pages

- [LLM Wiki — Programming](../programming/llm-wiki.md)
- [LLM Wiki — UI Design](../ui-design/llm-wiki.md)
- [Raw: LLM Wiki](../../raw/llm-wiki.md)
- [Raw: LLM App Development Patterns](../../raw/llm-app-development-patterns.md)

## Related Concepts

- [Knowledge Compounding](knowledge-compounding.md)
