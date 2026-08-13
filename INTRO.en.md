# LLM Wiki Agent Workflow Demo

I recently saw Andrej Karpathy mention the LLM Wiki idea and thought it was a great pattern to prototype.

This demo isn't trying to be another chatbot, and it isn't just RAG search. It's a different kind of knowledge workflow:
Let AI Agents turn raw material into a Markdown wiki you can maintain, query, and compound over time.

## Core idea

Three layers:

- **`raw/`**: source-of-truth raw material, never rewritten
- **`wiki/`**: Markdown knowledge pages compiled by AI Agents, with automatic cross-references
- **`AGENTS.md`**: the schema that defines how each Agent reads, compiles, and maintains the wiki

Workflow:

1. Drop material into `raw/` (paste text, pick existing, or fetch a URL)
2. Pick an Agent role
3. Let the Agent ingest that material into a structured wiki page
4. Use Concepts to weave the same theme across multiple sources into one page
5. Query the whole wiki
6. Archive useful answers back as synthesis pages


## Supported Agents

I started with 4 common work contexts:

- **Programming Agent**: technical architecture, API integration, development patterns
- **UI Design Agent**: interface flow, interaction design, user experience
- **Project Manager Agent**: roadmap, task breakdown, risks and decisions
- **Personal Knowledge Agent**: learning notes, reflection, personal knowledge management

The same source can be read by different Agents from different angles, **producing wiki pages with different purposes** - this is the "multi-perspective experiment" added on top of Karpathy's original idea.

## Demo interface

Streamlit local web app with 8 tabs, each mapped to a clear action:

- **Showcase**: opening tab that explains what the whole thing does
- **Inputs**: where material lives - paste text / pick existing / fetch URL; **no AI runs here**
- **Agents**: pick source + pick lens, let an AI Agent write a knowledge page
- **Knowledge**: browse grouped by source - lens views of the same material sit together, colour-coded by perspective
- **Concepts**: type a concept name (e.g. "ingest", "workflow"), AI weaves related fragments from multiple sources into one page
- **Map**: node graph showing relationships between raw -> agent -> wiki page -> concept
- **Ask**: query the whole wiki (mixed English / Chinese supported); good answers archive back as synthesis pages
- **Maintain**: read-only health view + explicit action buttons (rebuild index / record lint), including orphan page detection

## Why the Map exists

Following Karpathy's LLM Wiki idea, the point isn't producing one-off summaries - it's **letting knowledge form a network over time**.

The Map shows:

- Which raw sources have been ingested
- Which Agents produced which wiki pages
- How wiki pages link to each other (cross-references update automatically when you ingest a new lens on the same source)
- How concept pages stitch fragments from different sources together
- How synthesis pages fold useful Q&A back into the wiki

In short: **knowledge doesn't just live in chat history - it accumulates into a maintainable, navigable, growing Markdown knowledge system**.


## TL;DR

The AI Agent isn't the headline - **a Markdown knowledge base that grows and weaves its own connections is the headline**. The Agent is the writer. The wiki is the work.
