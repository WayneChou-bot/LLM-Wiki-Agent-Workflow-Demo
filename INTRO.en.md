# LLM Wiki Agent Workflow Demo

I've been studying Karpathy's LLM Wiki idea, so I built a small demo to show that AI Agents aren't just for answering questions - they can help maintain a knowledge base that actually grows and weaves itself together over time.

The core flow:

`Inputs (raw material) -> Agents (AI perspectives) -> Knowledge (compiled pages) -> Concepts (cross-source synthesis) -> Map (relationship graph) -> Ask (query the wiki) -> Maintain (health check)`

## What does this demo do?

A typical chatbot answer lives in your chat history and dissipates after use.

This demo shows a different workflow: feed articles, notes, meeting transcripts, and web pages to different AI Agents, and they compile them into a **durable, queryable, compounding** Markdown knowledge base - and every time you add new material, the cross-references between existing pages update automatically.

## Supported Agent perspectives

- **Programming Agent**: technical architecture, API integration, development patterns
- **UI Design Agent**: interface flow, interaction design, user experience
- **Project Manager Agent**: roadmap, task breakdown, risks and decisions
- **Personal Knowledge Agent**: learning notes, reflection, personal knowledge management

The same source can be read by different Agents from different angles, producing knowledge pages with different purposes.

## Demo features

- **Inputs**: paste plain text, pick existing material, or fetch a webpage directly from a URL
- **Agents**: pick an AI perspective and turn a source into a knowledge page (or run all 4 perspectives in one click)
- **Knowledge**: browse grouped by source - every lens view of the same material sits together, colour-coded by perspective
- **Concepts**: type a concept name (e.g. "ingest", "workflow") and synthesise related fragments from multiple sources into one page
- **Map**: a node graph showing relationships between raw sources, agents, knowledge pages, and concept pages
- **Ask**: query the compiled wiki - supports mixed English / Chinese queries
- **Maintain**: read-only health view + explicit action buttons (rebuild index / record lint), including orphan page detection

The Gemini API is wired in, so Agents can actually read raw sources, write wiki pages, and cross-link to related pages as they go. Everything produced is a plain Markdown file - the whole `wiki/` folder can be opened and edited in Obsidian.

## TL;DR

This demo is about showing that AI Agents aren't just chat tools - they can turn scattered material into a **knowledge system that grows and weaves itself together**.
