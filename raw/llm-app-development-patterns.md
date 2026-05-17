---
title: LLM App Development Patterns
source: demo seed
collected: 2026-05-17
published: Unknown
---

# LLM App Development Patterns

A practical LLM app often separates the user interface, knowledge layer, agent instructions, and model calls.

The user interface should expose a small number of clear operations. In a wiki demo, these operations are usually Sources, Ingest, Wiki, Ask, and Health.

The knowledge layer can begin as markdown files. Raw materials live in `raw/`, compiled pages live in `wiki/`, and the index/log files help the model navigate and preserve continuity.

The agent instruction layer defines how the system behaves. In Codex this can be `AGENTS.md`; in Claude Code it can be `CLAUDE.md`; in an Agent Skills setup it can be `SKILL.md`.

The model layer can be added later. A deterministic prototype can prove the workflow before connecting an API. After the workflow is clear, the app can call an LLM to perform ingest, answer questions, and lint wiki health.

Streamlit is useful for a local demo because it turns a folder workflow into a browser-based control panel. It is not the knowledge base itself. The markdown files remain the durable artifact.

The recommended first version should avoid vector databases, multi-agent orchestration, and complex automation. It should show the smallest loop that works: raw source in, wiki pages out, question answered, useful answer archived.
