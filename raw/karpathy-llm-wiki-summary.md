---
title: Karpathy LLM Wiki Summary
source: demo seed based on public gist
collected: 2026-05-17
published: 2026-04-04
---

# Karpathy LLM Wiki Summary

An LLM Wiki is a pattern for building personal knowledge bases using LLMs.

Instead of retrieving raw chunks at query time, the LLM incrementally builds and maintains a persistent wiki. New sources are read once, extracted, integrated into existing pages, linked to related concepts, and checked for contradictions.

The human chooses sources, asks questions, and guides emphasis. The LLM performs the maintenance work: summarizing, filing, cross-referencing, updating indexes, and preserving a log.

The basic architecture has three layers:

- Raw sources: immutable source materials.
- Wiki: compiled markdown pages maintained by the LLM.
- Schema: instructions that define the structure and workflows.

The basic operations are:

- Ingest: process a new source into the wiki.
- Query: answer from the compiled wiki and cite pages.
- Lint: check health, missing links, stale claims, contradictions, and orphan pages.

The key claim is that knowledge should compound. A good answer or synthesis should not disappear into chat history; it can be saved back into the wiki.
