# LLM Wiki Agent Workflow Demo

A **Karpathy-inspired LLM Wiki workflow**, with a multi-agent twist — available as a local Streamlit app and an interactive static showcase site.

> **Honesty note.** This is **not a 1:1 implementation** of Karpathy's original
> [LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
> Karpathy's pattern organises pages by topic/entity/concept and has a single
> wiki maintainer. This demo keeps the same three-layer architecture
> (`raw/` + `wiki/` + `AGENTS.md` schema) and the three operations
> (Ingest / Query / Lint), but adds a **multi-perspective remix**: four agent
> roles each compile the same source into their own viewpoint page. Use it as
> a teaching aid for the pattern, not a faithful reproduction.

The demo shows how several agent perspectives can compile the same raw sources into a durable markdown wiki:

- Programming Agent
- UI Design Agent
- Project Manager Agent
- Personal Knowledge Agent

It writes real markdown files under `wiki/`, so the folder can also be opened as an Obsidian vault.

## Two ways to experience it

| | Where it runs | What it does |
|---|---|---|
| **`web/` showcase site** | Any browser / [Vercel](https://vercel.com) | Interactive, bilingual (中/EN) static walkthrough: animated architecture, an ingest-workflow simulator, a draggable knowledge graph, a browser for the actual generated wiki pages, and a client-side Ask demo. Zero backend, zero API key. |
| **`app.py` Streamlit app** | Local machine | The full 8-tab workflow (Showcase → Inputs → Agents → Knowledge → Concepts → Map → Ask → Maintain), wired to the Gemini API and writing real markdown files. |

### Showcase site

Open `web/index.html` directly in a browser — no build step, no dependencies.
To publish it on Vercel, see [DEPLOY.md](DEPLOY.md) (≈2 minutes: import the repo,
set the project's Root Directory to `web`, deploy).

### Streamlit app

```powershell
conda env create -f environment.yml
conda activate llm-wiki-demo
streamlit run app.py
```

If the environment already exists:

```powershell
conda activate llm-wiki-demo
pip install -r requirements.txt
streamlit run app.py
```

## Gemini API

The app can use Gemini for real agent work.

Set your key before launching:

```powershell
$env:GEMINI_API_KEY="your-api-key"
streamlit run app.py
```

Or paste the key into the Streamlit sidebar. The app does not write the key to disk.

Default model:

```text
gemini-2.5-flash
```

You can change the model in the sidebar.

## Demo Flow

1. Open the Streamlit app.
2. Enter a Gemini API key in the sidebar, or set `GEMINI_API_KEY`.
3. Pick an agent.
4. Select a raw source (or fetch a new one by URL).
5. Run ingest. Each source produces a new page; ingesting the same source again
   updates the same page; the LLM is asked to cross-link to related pages.
6. Browse the generated wiki pages and watch the knowledge graph grow.
7. Ask a question and optionally save the answer to `wiki/syntheses/`.

## Structure

```text
raw/         Immutable source materials
wiki/        Compiled knowledge pages (LLM-maintained)
templates/   Page templates (article.md, synthesis.md) - used by the app at ingest time
AGENTS.md    Agent maintenance rules / schema
app.py       Streamlit interface
web/         Static interactive showcase site (deployable to Vercel)
DEPLOY.md    Step-by-step Vercel deployment guide
```

Local media folders (screenshots, recordings, reference images) and personal
notes are intentionally git-ignored — the repo only carries the work itself.

## Differences from the original gist

- Pages are per-source x per-agent, not per-entity / per-concept.
- The "schema" file is `AGENTS.md`; the `templates/` folder defines the page shape.
- Ingest uses a fixed shape (`templates/article.md`) so output is stable for demos.
- Cross-references are produced both in deterministic mode (siblings of the same source) and Gemini mode (model is given the full list of existing pages with relative paths).
- Lint is shallow: checks empty pages, missing index entries, broken local links, and orphan pages. No contradiction detection.
